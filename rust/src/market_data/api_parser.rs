use std::collections::HashMap;

use ureq;
use serde_json::Value;
use chrono::{DateTime, NaiveDateTime, Utc, LocalResult, Duration, TimeZone};
use chrono_tz::US::Eastern;

use crate::base::Status;
use crate::market_data::{
    ContractData,
    MarketData,
    PIDataPacket,
};

type JsonMap = serde_json::map::Map<String, Value>;

const TIMESTAMP_TOLERANCE_SECS : i64 = 5 * 60;
const API_ADDRESS: &'static str = "https://www.predictit.org/api/marketdata/all/";
const MARKET_API_ADDRESS: &'static str = "https://www.predictit.org/api/marketdata/markets/{}";

#[derive(Debug)]
pub struct MarketDataError(MarketDataErrorKind);

impl MarketDataError {
    pub fn new_field_format_error(field: &str) -> Self {
        MarketDataError(MarketDataErrorKind::FieldFormatError(field.to_owned()))
    }
}

#[derive(Clone, Debug)]
pub enum MarketDataErrorKind {
    FieldUnavailable(String),
    FieldFormatError(String),
    TimestampError(String),
    JsonParseError,
    APIUnavailable,
}

pub type MarketDataResult = Result<Option<PIDataPacket>, MarketDataError>;


fn get_field<'a>(map: &'a JsonMap, field: &str) -> Result<&'a Value, MarketDataError> {
    map.get(field).ok_or(MarketDataError(MarketDataErrorKind::FieldUnavailable(field.to_owned())))
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
        status: get_status(get_str(market_map, "status")?)?,
        timestamp: get_utc_timestamp(get_str(market_map, "timeStamp")?)?
    })
}

#[allow(dead_code)]
pub fn fetch_market_data(id: u64) -> Result<MarketData, MarketDataError> {
    let api_address = format!("{} {}", MARKET_API_ADDRESS, id);
    let resp = ureq::get(&api_address)
        .timeout_connect(15_000)  // fairly generous connect and read timeouts
        .timeout_read(15_000)
        .call();

    if resp.ok() {
        // TODO: Wrap library errors into MarketDataError
        let data_string = resp.into_string().unwrap();
        println!("{}", data_string);
        let market_data_value = serde_json::from_str::<Value>(&data_string)
            .map_err(|_err| MarketDataError(MarketDataErrorKind::JsonParseError))?;
        let market_map = market_data_value.as_object()
            .ok_or(MarketDataError(MarketDataErrorKind::JsonParseError))?;
        get_market(market_map)
    } else {
        Err(MarketDataError(MarketDataErrorKind::APIUnavailable))
    }
}

fn abs_duration(duration: Duration) -> Duration {
    if duration < Duration::zero() {
        -duration
    } else {
        duration
    }
}

fn get_utc_timestamp(timestamp_str: &str) -> Result<DateTime<Utc>, MarketDataError> {
    let current_time = Utc::now().with_timezone(&Utc);
    let tolerance = Duration::seconds(TIMESTAMP_TOLERANCE_SECS);

    let local_datetime = NaiveDateTime::parse_from_str(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
            .map_err(|_err| MarketDataError::new_field_format_error("timestamp"))?;
    match Eastern.from_local_datetime(&local_datetime) {
        LocalResult::None => {
            let err_string = format!("Invalid timezone timestamp: {}", timestamp_str);
            Err(MarketDataError(MarketDataErrorKind::TimestampError(err_string)))
        },
        LocalResult::Single(res) => {
            let res_utc = res.with_timezone(&Utc);
            if abs_duration(res_utc - current_time) <= tolerance {
                Ok(res_utc)
            } else {
                let err_string = format!("Timestamp {} too far from current time {}", res_utc, current_time);
                Err(MarketDataError(MarketDataErrorKind::TimestampError(err_string)))
            }
        },
        LocalResult::Ambiguous(res1, res2) => {
            let res1_utc = res1.with_timezone(&Utc);
            let res2_utc = res2.with_timezone(&Utc);
            let diff_min = abs_duration(res1_utc - current_time);
            let diff_max = abs_duration(res2_utc - current_time);
            if diff_min < diff_max && diff_min <= tolerance {
                Ok(res1.with_timezone(&Utc))
            } else if diff_max <= diff_min && diff_max <= tolerance {
                Ok(res2.with_timezone(&Utc))
            } else {
                let err_string = format!("Both timestamps ({}, {}) too far from current time {}",
                    res1_utc, res2_utc, current_time);
                Err(MarketDataError(MarketDataErrorKind::TimestampError(err_string)))
            }
        }
    }

}

pub fn fetch_api_market_data() -> MarketDataResult {
    let api_address = API_ADDRESS;
    let resp = ureq::get(&api_address)
        .timeout_connect(5000) // wait up to 5 seconds
        .call();

    let mut all_market_data_map = HashMap::new();

    if resp.ok() {
        let data_string = resp.into_string().unwrap();
        let all_market_data = serde_json::from_str::<Value>(&data_string)
            .map_err(|_err| MarketDataError(MarketDataErrorKind::JsonParseError))?;
        let all_market_data_obj = all_market_data.as_object()
            .ok_or(MarketDataError(MarketDataErrorKind::JsonParseError))?;

        for market_data in get_array(all_market_data_obj, "markets")? {
            let market_map = market_data.as_object()
                .ok_or(MarketDataError::new_field_format_error("markets[] entry"))?;
            let market = get_market(market_map)?;
            all_market_data_map.insert(market.id, market);
        }

        Ok(Some(PIDataPacket { market_updates: all_market_data_map }))
    } else {
        println!("{:?}", resp);
        Err(MarketDataError(MarketDataErrorKind::APIUnavailable))
    }
}
