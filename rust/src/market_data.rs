use std::collections::HashMap;
use std::io::Write;

use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc};

use crate::base::Status;

pub mod md_cache;
pub mod api_parser;
pub mod reader;
pub mod writer;

pub use api_parser::MarketDataResult;
pub use reader::{MarketDataLive, MarketDataSimJson};

/// Raw format for PI market data updates, matching source JSON format
#[derive(Debug, Serialize, Deserialize)]
pub struct PIDataPacket {
    pub market_updates: HashMap<u64, MarketData>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MarketData {
    id: u64,
    name: String,
    contracts: Vec<ContractData>,
    status: Status,
    timestamp: DateTime<Utc>
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ContractData {
    id: u64,
    name: String,
    status: Status,
    trade_price: f64,
    ask_price: f64,
    bid_price: f64
}

/// Format for PI market data updates, organized around contract updates
pub struct DataPacket {
    pub timestamp: DateTime<Utc>,
    pub payload: PacketPayload
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

pub trait MarketDataListener {
    fn process_market_data(&mut self, data: &DataPacket) -> bool;
}

pub trait RawMarketDataListener {
    fn process_raw_market_data(&mut self, data: &PIDataPacket) -> bool;
}

pub trait MarketDataProvider {
    fn fetch_market_data(&mut self) -> Option<&DataPacket>;
}

pub trait RawMarketDataProvider {
    fn fetch_raw_market_data(&mut self) -> Option<&PIDataPacket>;
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

impl DataPacket {
    const TIMESTAMP: &'static str = "timestamp";

    pub fn csv_serialize<T: Write>(&self, writer: &mut T) {
        // Performance question? Is using a byte array faster?
        write_column(writer, Some(&self.timestamp.timestamp_millis()));
        self.payload.csv_serialize(writer);
        writeln!(writer).unwrap();
    }

    pub fn write_header<T: Write>(writer: &mut T) {
        write_column(writer, Some(Self::TIMESTAMP));
        PacketPayload::write_header(writer);
        writeln!(writer).unwrap();
    }
}

fn write_column<W: Write, T: ToString + ?Sized>(writer: &mut W, val: Option<&T>) {
    if let Some(v) = val {
        writer.write_all(v.to_string().as_bytes()).unwrap();
    }
    writer.write_all(",".as_bytes()).unwrap();
}
