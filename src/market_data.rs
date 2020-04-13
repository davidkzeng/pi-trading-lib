use serde_json::{Value};
use ureq;
use std::collections::HashMap;

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
pub enum ContractStatus {
    Open,
    Closed
}

#[derive(Debug)]
pub struct Contract {
    id: u64,
    name: String,
    status: ContractStatus,
    trade_price: f64,
    ask_price: f64,
    bid_price: f64
}

#[derive(Debug)]
pub struct Market {
    id: u64,
    name: String,
    contracts: Vec<Contract>,
    status: ContractStatus
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

fn get_status(status: &str) -> Result<ContractStatus, MarketDataError> {
    match status {
        "Open" => Ok(ContractStatus::Open),
        "Closed" => Ok(ContractStatus::Closed),
        _ => Err(MarketDataError::new_field_format_error(&format!("status. Unknown status {}", status)))
    }
}

fn get_contract(contract: &JsonMap) -> Result<Contract, MarketDataError> {
    Ok(Contract {
        id: get_u64(contract, "id")?,
        name: get_string(contract, "shortName")?,
        status: get_status(get_str(contract, "status")?)?,
        trade_price: get_f64(contract, "lastTradePrice")?,
        ask_price: get_f64_or_null_val(contract, "bestBuyYesCost", 1.0)?,
        bid_price: get_f64_or_null_val(contract, "bestSellYesCost", 0.0)?
    })
}

fn get_contracts(contracts: &Vec<Value>) -> Result<Vec<Contract>, MarketDataError> {
    let mut parsed_contracts = Vec::new();
    for contract in contracts {
        let contract_map = contract.as_object()
            .ok_or(MarketDataError::new_field_format_error("contracts[] entry"));
        parsed_contracts.push(get_contract(contract_map?)?);
    }
    Ok(parsed_contracts)
}

fn get_market(market_map: &JsonMap) -> Result<Market, MarketDataError> {
    Ok(Market { 
        id: get_u64(market_map, "id")?,
        name: get_string(market_map, "shortName")?,
        contracts: get_contracts(get_array(market_map, "contracts")?)?,
        status: get_status(get_str(market_map, "status")?)?
    })
}

pub fn fetch_market_data(id: u64) -> Result<Market, MarketDataError> {
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

pub fn fetch_all_market_data() -> Result<HashMap<u64, Market>, MarketDataError> {
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
        Ok(all_market_data_map)
    } else {
        Err(MarketDataError::new(MarketDataErrorKind::APIUnavailable))
    }
}

pub fn test() {
    let all_market_data = fetch_all_market_data().unwrap();
    println!("{}", all_market_data.len());
    // println!("{:?}", fetch_all_market_data().unwrap());
    // println!("{:?}", fetch_market_data(3633).unwrap());
}

