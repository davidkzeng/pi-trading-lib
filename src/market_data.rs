use std::collections::HashMap;

use ureq;
use serde_json::Value;
use chrono::{DateTime, NaiveDateTime, Utc, LocalResult, Duration, TimeZone};
use chrono_tz::US::Eastern;

use crate::base::Status;

pub mod md_stream;

type JsonMap = serde_json::map::Map<String, Value>;

const TIMESTAMP_TOLERANCE_SECS : i64 = 5 * 60;
const API_ADDRESS: &'static str = "https://www.predictit.org/api/marketdata/all/";
const MARKET_API_ADDRESS: &'static str = "https://www.predictit.org/api/marketdata/markets/{}";

#[derive(Debug)]
pub struct MarketDataError {
    kind: MarketDataErrorKind,
}

impl MarketDataError {
    pub fn new(kind: MarketDataErrorKind) -> Self {
        MarketDataError { kind: kind }
    }

    pub fn new_field_format_error(field: &str) -> Self {
        MarketDataError::new(MarketDataErrorKind::FieldFormatError(field.to_owned()))
    }
}

#[derive(Debug)]
pub enum MarketDataErrorKind {
    FieldUnavailable(String),
    FieldFormatError(String),
    TimestampError(String),
    JsonParseError,
    APIUnavailable,
}

#[derive(Debug)]
pub struct ContractData {
    id: u64,
    name: String,
    status: Status,
    trade_price: f64,
    ask_price: f64,
    bid_price: f64
}

#[derive(Debug)]
pub struct MarketData {
    id: u64,
    name: String,
    contracts: Vec<ContractData>,
    status: Status
}

#[derive(Debug)]
pub struct PIDataPacket {
    pub market_updates: HashMap<u64, MarketData>,
    pub timestamp: DateTime<Utc>
}

fn get_field<'a>(map: &'a JsonMap, field: &str) -> Result<&'a Value, MarketDataError> {
    map.get(field).ok_or(MarketDataError::new(MarketDataErrorKind::FieldUnavailable(field.to_owned())))
}

fn get_u64(map: &JsonMap, field: &str) -> Result<u64, MarketDataError> {
    get_field(map, field)?.as_u64()
        .ok_or(MarketDataError::new_field_format_error(field))
}

fn get_f64(map: &JsonMap, field: &str) -> Result<f64, MarketDataError> {
    get_field(map, field)?.as_f64()
        .ok_or(MarketDataError::new_field_format_error(field))
}

fn get_f64_or_null_val(map: &JsonMap, field: &str, val: f64) -> Result<f64, MarketDataError> {
    get_f64(map, field)
        .or_else(|_err| {
            get_field(map, field)?.as_null().ok_or(MarketDataError::new_field_format_error(field))
                .map(|_null_val| val)
        })
}

fn get_str<'a>(map: &'a JsonMap, field: &str) -> Result<&'a str, MarketDataError> {
    get_field(map, field)?.as_str()
        .ok_or(MarketDataError::new_field_format_error(field))
}

fn get_string(map: &JsonMap, field: &str) -> Result<String, MarketDataError> {
    Ok(get_str(map, field)?.to_owned())
}

fn get_array<'a>(map: &'a JsonMap, field: &str) -> Result<&'a Vec<Value>, MarketDataError> {
    get_field(map, field)?.as_array()
        .ok_or(MarketDataError::new_field_format_error(field))
}

fn get_status(status: &str) -> Result<Status, MarketDataError> {
    match status {
        "Open" => Ok(Status::Open),
        "Closed" => Ok(Status::Closed),
        _ => Err(MarketDataError::new_field_format_error(&format!("status. Unknown status {}", status)))
    }
}

fn get_contract(contract: &JsonMap) -> Result<ContractData, MarketDataError> {
    Ok(ContractData {
        id: get_u64(contract, "id")?,
        name: get_string(contract, "shortName")?,
        status: get_status(get_str(contract, "status")?)?,
        trade_price: get_f64(contract, "lastTradePrice")?,
        ask_price: get_f64_or_null_val(contract, "bestBuyYesCost", 1.0)?,
        bid_price: get_f64_or_null_val(contract, "bestSellYesCost", 0.0)?
    })
}

fn get_contracts(contracts: &Vec<Value>) -> Result<Vec<ContractData>, MarketDataError> {
    let mut parsed_contracts = Vec::new();
    for contract in contracts {
        let contract_map = contract.as_object()
            .ok_or(MarketDataError::new_field_format_error("contracts[] entry"));
        parsed_contracts.push(get_contract(contract_map?)?);
    }
    Ok(parsed_contracts)
}

fn get_market(market_map: &JsonMap) -> Result<MarketData, MarketDataError> {
    Ok(MarketData { 
        id: get_u64(market_map, "id")?,
        name: get_string(market_map, "shortName")?,
        contracts: get_contracts(get_array(market_map, "contracts")?)?,
        status: get_status(get_str(market_map, "status")?)?
    })
}

pub fn fetch_market_data(id: u64) -> Result<MarketData, MarketDataError> {
    let api_address = format!("{} {}", MARKET_API_ADDRESS, id);
    let resp = ureq::get(&api_address).call();

    if resp.ok() {
        // TODO: Wrap library errors into MarketDataError
        let data_string = resp.into_string().unwrap();
        println!("{}", data_string);
        let market_data_value = serde_json::from_str::<Value>(&data_string)
            .map_err(|_err| MarketDataError::new(MarketDataErrorKind::JsonParseError))?;
        let market_map = market_data_value.as_object()
            .ok_or(MarketDataError::new(MarketDataErrorKind::JsonParseError))?;
        get_market(market_map)
    } else {
        Err(MarketDataError::new(MarketDataErrorKind::APIUnavailable))
    }
}

fn abs_duration(duration: Duration) -> Duration {
    if duration < Duration::zero() {
        -duration
    } else {
        duration
    }
}

fn get_confirmed_timestamp_utc<Tz: TimeZone>(parse_result: &LocalResult<DateTime<Tz>>, timestamp_str: &str,
    tolerance: &Duration)
    -> Result<DateTime<Utc>, MarketDataError> {
    // TODO: Extract out tolerance to be a parameter
    let current_time = Utc::now().with_timezone(&Utc);
    match parse_result {
        LocalResult::None => {
            let err_string = format!("Invalid timezone timestamp: {}", timestamp_str);
            Err(MarketDataError::new(MarketDataErrorKind::TimestampError(err_string)))
        },
        LocalResult::Single(res) => {
            let res_utc = res.with_timezone(&Utc);
            if &abs_duration(res_utc - current_time) <= tolerance {
                Ok(res_utc)
            } else {
                let err_string = format!("Timestamp {} too far from current time {}", res_utc, current_time);
                Err(MarketDataError::new(MarketDataErrorKind::TimestampError(err_string)))
            }
        },
        LocalResult::Ambiguous(res1, res2) => {
            let res1_utc = res1.with_timezone(&Utc);
            let res2_utc = res2.with_timezone(&Utc);
            let diff_min = abs_duration(res1_utc - current_time);
            let diff_max = abs_duration(res2_utc - current_time);
            if diff_min < diff_max && &diff_min <= tolerance {
                Ok(res1.with_timezone(&Utc))
            } else if diff_max <= diff_min && &diff_max <= tolerance {
                Ok(res2.with_timezone(&Utc))
            } else {
                let err_string = format!("Both timestamps ({}, {}) too far from current time {}",
                    res1_utc, res2_utc, current_time);
                Err(MarketDataError::new(MarketDataErrorKind::TimestampError(err_string)))
            }
        }
    }

}

pub fn fetch_all_market_data() -> Result<PIDataPacket, MarketDataError> {
    let api_address = API_ADDRESS;
    let resp = ureq::get(&api_address).call();

    let mut all_market_data_map = HashMap::new();

    if resp.ok() {
        let data_string = resp.into_string().unwrap();
        let all_market_data = serde_json::from_str::<Value>(&data_string)
            .map_err(|_err| MarketDataError::new(MarketDataErrorKind::JsonParseError))?;
        let all_market_data_obj = all_market_data.as_object()
            .ok_or(MarketDataError::new(MarketDataErrorKind::JsonParseError))?;
        let mut timestamp = None;
        for market_data in get_array(all_market_data_obj, "markets")? {
            let market_map = market_data.as_object()
                .ok_or(MarketDataError::new_field_format_error("markets[] entry"))?;
            let market = get_market(market_map)?;
            all_market_data_map.insert(market.id, market);
            if timestamp.is_none() {
                let timestamp_str = get_str(market_map, "timeStamp")?;
                let timestamp_et = 
                    NaiveDateTime::parse_from_str(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
                        .map_err(|_err| MarketDataError::new_field_format_error("timestamp"))?;
                let timestamp_utc = get_confirmed_timestamp_utc(&Eastern.from_local_datetime(&timestamp_et),
                    timestamp_str, &Duration::seconds(TIMESTAMP_TOLERANCE_SECS))?;
                timestamp = Some(timestamp_utc);
            }
        }
        // TODO: Get ts from markets, assert that the timestamp is always the same.
        Ok(PIDataPacket { market_updates: all_market_data_map, timestamp: timestamp.unwrap() })
    } else {
        Err(MarketDataError::new(MarketDataErrorKind::APIUnavailable))
    }
}


