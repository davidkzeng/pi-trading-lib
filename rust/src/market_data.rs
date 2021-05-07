use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
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

// TODO: Maybe we want this Sized restriction?
fn write_column<W: Write, T: ToString + ?Sized>(writer: &mut W, val: Option<&T>) {
    if let Some(v) = val {
        writer.write(v.to_string().as_bytes()).unwrap();
    }
    writer.write(",".as_bytes()).unwrap();
}

pub enum PacketPayload {
    PIQuote {
        id: u64,
        market_id: u64,
        name: String,
        market_name: String,
        status: Status,
        trade_price: f64,
        bid_price: f64,
        ask_price: f64,
    }
}

impl PacketPayload {
    const TYPE: &'static str = "type";
    const ID: &'static str = "id";
    const MARKET_ID: &'static str = "market_id";
    const STATUS: &'static str = "status";
    const TRADE_PRICE: &'static str = "trade_price";
    const BID_PRICE: &'static str = "bid_price";
    const ASK_PRICE: &'static str = "ask_price";

    pub fn csv_serialize<T: Write>(&self, write_buf: &mut T) {
        match self {
            PacketPayload::PIQuote { id, market_id, status, trade_price, ask_price, bid_price, .. } => {
                write_column(write_buf, Some("piquote"));
                write_column(write_buf, Some(id));
                write_column(write_buf, Some(market_id));
                write_column(write_buf, Some(status));
                write_column(write_buf, Some(trade_price));
                write_column(write_buf, Some(bid_price));
                write_column(write_buf, Some(ask_price));
            }
        }
    }

    pub fn write_header<T: Write>(write_buf: &mut T) {
        write_column(write_buf, Some(Self::TYPE));
        write_column(write_buf, Some(Self::ID));
        write_column(write_buf, Some(Self::MARKET_ID));
        write_column(write_buf, Some(Self::STATUS));
        write_column(write_buf, Some(Self::TRADE_PRICE));
        write_column(write_buf, Some(Self::BID_PRICE));
        write_column(write_buf, Some(Self::ASK_PRICE));
    }
}

// V2 of PIDataPacket, going for more generic, event oriented, easy to csv serialize
pub struct DataPacket {
    pub timestamp: DateTime<Utc>,
    pub payload: PacketPayload
}

impl DataPacket {
    const TIMESTAMP: &'static str = "timestamp";

    pub fn csv_serialize<T: Write>(&self, writer: &mut T) {
        // Performance question? Is using a byte array faster?
        let mut bytes: Vec<u8> = Vec::with_capacity(128);
        write_column(&mut bytes, Some(&self.timestamp.timestamp_millis()));
        self.payload.csv_serialize(&mut bytes);
        writeln!(&mut bytes).unwrap();
        writer.write_all(&bytes).unwrap();
    }

    pub fn write_header<T: Write>(writer: &mut T) {
        write_column(writer, Some(Self::TIMESTAMP));
        PacketPayload::write_header(writer);
        writeln!(writer).unwrap();
    }
}

pub type MarketDataResult = Result<Option<PIDataPacket>, MarketDataError>;
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

// Delete once we remove Json from the pipeline
pub struct MarketDataSimJson {
    data_reader: BufReader<File>,
    line_buffer: String
}

impl MarketDataSimJson {
    pub fn new(filename: &str) -> Self {
        let data_file = File::open(filename).unwrap();
        MarketDataSimJson {
            data_reader: BufReader::new(data_file),
            line_buffer: String::new()
        }
    }
}

impl MarketDataSource for MarketDataSimJson {
    fn fetch_market_data(&mut self) -> MarketDataResult {
        let bytes_read = self.data_reader.read_line(&mut self.line_buffer).unwrap();
        if bytes_read == 0 {
            return Ok(None);
        }
        let market_data: PIDataPacket = serde_json::from_str(&mut self.line_buffer).unwrap();
        self.line_buffer.clear();
        Ok(Some(market_data))
    }
}

pub struct MarketDataSimCsv {
    data_reader: BufReader<File>,
    line_buffer: String
}

impl MarketDataSimCsv {
    pub fn new(filename: &str) -> Self {
        let data_file = File::open(filename).unwrap();
        MarketDataSimCsv {
            data_reader: BufReader::new(data_file),
            line_buffer: String::new()
        }
    }
}

impl MarketDataSource for MarketDataSimCsv {
    fn fetch_market_data(&mut self) -> MarketDataResult {
        let bytes_read = self.data_reader.read_line(&mut self.line_buffer).unwrap();
        if bytes_read == 0 {
            return Ok(None);
        }
        let market_data: PIDataPacket = serde_json::from_str(&mut self.line_buffer).unwrap();
        self.line_buffer.clear();
        Ok(Some(market_data))
    }
}
