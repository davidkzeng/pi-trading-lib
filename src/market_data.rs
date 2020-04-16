use ureq;
use serde_json::Value;
use chrono::{DateTime, Utc};

use std::collections::HashMap;

use crate::base::{Status, PIDataState};
use self::md_stream::PIDataIngester;

mod md_stream;

type JsonMap = serde_json::map::Map<String, Value>;

#[derive(Debug)]
pub struct MarketDataError {
    kind: MarketDataErrorKind,
}

impl MarketDataError {
    pub fn new(kind: MarketDataErrorKind) -> MarketDataError {
        MarketDataError { kind: kind }
    }

    pub fn new_field_format_error(field: &str) -> MarketDataError {
        MarketDataError::new(MarketDataErrorKind::FieldFormatError(field.to_owned()))
    }
}

#[derive(Debug)]
pub enum MarketDataErrorKind {
    FieldUnavailable(String),
    FieldFormatError(String),
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
    let api_address = format!("https://www.predictit.org/api/marketdata/markets/{}", id);
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

pub fn fetch_all_market_data() -> Result<PIDataPacket, MarketDataError> {
    let api_address = "https://www.predictit.org/api/marketdata/all/";
    let resp = ureq::get(&api_address).call();

    let mut all_market_data_map = HashMap::new();

    if resp.ok() {
        let data_string = resp.into_string().unwrap();
        let all_market_data = serde_json::from_str::<Value>(&data_string)
            .map_err(|_err| MarketDataError::new(MarketDataErrorKind::JsonParseError))?;
        let all_market_data_obj = all_market_data.as_object()
            .ok_or(MarketDataError::new(MarketDataErrorKind::JsonParseError))?;
        for market_data in get_array(all_market_data_obj, "markets")? {
            let market_map = market_data.as_object()
                .ok_or(MarketDataError::new_field_format_error("markets[] entry"))?;
            let market = get_market(market_map)?;
            all_market_data_map.insert(market.id, market);
        }
        // TODO: Get ts from markets, assert that the timestamp is always the same.
        Ok(PIDataPacket { market_updates: all_market_data_map, timestamp: Utc::now() })
    } else {
        Err(MarketDataError::new(MarketDataErrorKind::APIUnavailable))
    }
}

pub fn fetch_and_update_state(state: &mut PIDataState) {
    let new_data = fetch_all_market_data().unwrap();
    let mut ingester = PIDataIngester::new(state);
    ingester.ingest_data(&new_data);
}
