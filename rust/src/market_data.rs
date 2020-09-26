use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::{thread, time};

use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc};

use crate::base::Status;

pub mod md_stream;
pub mod api_parser;

#[derive(Debug)]
pub struct MarketDataError(MarketDataErrorKind);

impl MarketDataError {
    pub fn new_field_format_error(field: &str) -> Self {
        MarketDataError(MarketDataErrorKind::FieldFormatError(field.to_owned()))
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
    status: Status,
    timestamp: DateTime<Utc>
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PIDataPacket {
    pub market_updates: HashMap<u64, MarketData>,
}

pub type MarketDataResult = Result<PIDataPacket, MarketDataError>;
pub trait MarketDataSource {
    fn fetch_market_data(&mut self) -> MarketDataResult;
}
pub struct MarketDataLive {
    retry_limit: u64
}

impl MarketDataLive {
    pub fn new() -> Self {
        MarketDataLive { retry_limit: 1 }
    }

    pub fn new_with_retry(retry_limit: u64) -> Self {
        MarketDataLive { retry_limit }
    }
}

impl MarketDataSource for MarketDataLive {
    fn fetch_market_data(&mut self) -> MarketDataResult {
        let mut attempts = 0;
        loop {
            match api_parser::fetch_api_market_data() {
                Ok(market_data) => {
                    break Ok(market_data);
                },
                Err(err) => {
                    attempts += 1;
                    if attempts >= self.retry_limit {
                        break Err(err);
                    }
                    println!("Encountered market data error {:?}", err);
                    println!("Sleeping for 1 second");
                    thread::sleep(time::Duration::from_millis(1000));
                }
            }
        }
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
