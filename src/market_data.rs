use serde_json::{Value};
use ureq;

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
        ask_price: get_f64(contract, "bestBuyYesCost")?,
        bid_price: get_f64(contract, "bestSellYesCost")?
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

pub fn fetch_market_data(id: u64) -> Result<Market, MarketDataError> {
    let api_address = format!("https://www.predictit.org/api/marketdata/markets/{}", id);
    let resp = ureq::get(&api_address)
        .call();

    if resp.ok() {
        // TODO: Wrap library errors into MarketDataError
        let data_string = resp.into_string().unwrap();
        let market_data_value = serde_json::from_str::<Value>(&data_string)
            .map_err(|_err| MarketDataError::new(MarketDataErrorKind::JsonParseError))?;
        let market_data_map = market_data_value.as_object()
            .ok_or(MarketDataError::new(MarketDataErrorKind::JsonParseError))?;

        let market = Market { 
            id: get_u64(market_data_map, "id")?,
            name: get_string(market_data_map, "shortName")?,
            contracts: get_contracts(get_array(market_data_map, "contracts")?)?,
            status: get_status(get_str(market_data_map, "status")?)?
        };
        Ok(market)
    } else {
        Err(MarketDataError::new(MarketDataErrorKind::APIUnavailable))
    }
}

pub fn test() {
    println!("{:?}", fetch_market_data(2721).unwrap());
}

