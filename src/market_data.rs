use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};

use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc};

use crate::base::Status;

pub mod md_stream;
pub mod api_parser;

#[derive(Debug)]
pub struct MarketDataError {
    kind: MarketDataErrorKind,
}

impl MarketDataError {
    pub fn new(kind: MarketDataErrorKind) -> Self {
        MarketDataError { kind }
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

#[derive(Debug, Serialize, Deserialize)]
pub struct ContractData {
    id: u64,
    name: String,
    status: Status,
    trade_price: f64,
    ask_price: f64,
    bid_price: f64
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MarketData {
    id: u64,
    name: String,
    contracts: Vec<ContractData>,
    status: Status
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PIDataPacket {
    pub market_updates: HashMap<u64, MarketData>,
    pub timestamp: DateTime<Utc>
}

pub type MarketDataResult = Result<PIDataPacket, MarketDataError>;
pub trait MarketDataSource {
    fn fetch_market_data(&mut self) -> MarketDataResult;
}
pub struct MarketDataLive;

impl MarketDataSource for MarketDataLive {
    fn fetch_market_data(&mut self) -> MarketDataResult {
        api_parser::fetch_api_market_data()
    }
}

pub struct MarketDataSim {
    data_reader: BufReader<File>,
    line_buffer: String
}

impl MarketDataSim {
    pub fn new(filename: &str) -> Self {
        let data_file = File::open(filename).unwrap();
        MarketDataSim { 
            data_reader: BufReader::new(data_file), 
            line_buffer: String::new()
        }
    }
}

impl MarketDataSource for MarketDataSim {
    fn fetch_market_data(&mut self) -> MarketDataResult {
        self.data_reader.read_line(&mut self.line_buffer).unwrap();
        let market_data: PIDataPacket = serde_json::from_str(&mut self.line_buffer).unwrap();
        self.line_buffer.clear();
        Ok(market_data)
    }
}
