use std::collections::HashMap;
use std::io::{BufRead, Write};
use std::str::{self, FromStr};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::base::Status;

mod api_parser;
pub mod md_cache;
pub mod reader;
pub mod writer;

pub use self::api_parser::MarketDataResult;
#[doc(inline)]
pub use self::reader::{MarketDataLive, MarketDataSimJson, MarketDataSimCsv};

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
    status: Status, // In practice, this is always true
    timestamp: DateTime<Utc>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ContractData {
    id: u64,
    name: String,
    status: Status, // In practice, this is always true
    trade_price: f64,
    ask_price: f64,
    bid_price: f64,
}

/// Format for PI market data updates, organized around contract updates
#[derive(Clone, Debug, PartialEq)]
pub struct DataPacket {
    // TODO: Replace this with just normal millis timestamp
    pub timestamp: i64,
    pub payload: PacketPayload,
}

#[derive(Clone, Debug, PartialEq)]
pub enum PacketPayload {
    PIQuote {
        id: u64,
        market_id: u64,
        status: Status,
        trade_price: f64,
        bid_price: f64,
        ask_price: f64,
    },
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
            PacketPayload::PIQuote {
                id,
                market_id,
                status,
                trade_price,
                ask_price,
                bid_price,
                ..
            } => {
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

    pub fn csv_deserialize<T: BufRead>(reader: &mut T, buffer: &mut Vec<u8>) -> Result<Self, ()> {
        let payload_type: &str = read_column_str(reader, buffer)?;
        if payload_type == "piquote" {
            Ok(PacketPayload::PIQuote {
                id: read_column(reader, buffer)?,
                market_id: read_column(reader, buffer)?,
                status: read_column(reader, buffer)?,
                trade_price: read_column(reader, buffer)?,
                bid_price: read_column(reader, buffer)?,
                ask_price: read_column(reader, buffer)?,
            })
        } else {
            Err(())
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
    #[allow(dead_code)]
    const MAX_SIZE: usize = std::mem::size_of::<Self>();
    const MAX_SER_SIZE: usize = 10 * Self::MAX_SIZE; // Estimate

    pub fn csv_serialize<T: Write>(&self, writer: &mut T) {
        // Performance question? Is using a byte array faster?
        write_column(writer, Some(&self.timestamp));
        self.payload.csv_serialize(writer);
        writeln!(writer).unwrap();
    }

    pub fn write_header<T: Write>(writer: &mut T) {
        write_column(writer, Some(Self::TIMESTAMP));
        PacketPayload::write_header(writer);
        writeln!(writer).unwrap();
    }

    pub fn csv_deserialize<T: BufRead>(reader: &mut T, buffer: &mut Vec<u8>) -> Result<Self, ()> {
        let timestamp = read_column(reader, buffer)?;
        let payload = PacketPayload::csv_deserialize(reader, buffer)?;
        Ok(DataPacket { timestamp, payload })
    }

    pub fn check_header<T: BufRead>(reader: &mut T) -> bool {
        let mut reference_header: Vec<u8> = Vec::new();
        Self::write_header(&mut reference_header);
        let mut file_header: Vec<u8> = Vec::new();
        reader.read_until(b'\n', &mut file_header).unwrap();
        file_header.pop();
        reference_header == file_header
    }
}

fn write_column<W: Write, T: ToString + ?Sized>(writer: &mut W, val: Option<&T>) {
    if let Some(v) = val {
        writer.write_all(v.to_string().as_bytes()).unwrap();
    }
    writer.write_all(",".as_bytes()).unwrap();
}

fn read_column<R: BufRead, T: FromStr>(reader: &mut R, buffer: &mut Vec<u8>) -> Result<T, ()> {
    buffer.clear();
    reader.read_until(b',', buffer).map_err(|_err| ())?;
    if buffer.is_empty() {
        Err(())
    } else {
        str::from_utf8(&buffer[..buffer.len() - 1])
            .unwrap()
            .parse()
            .map_err(|_err| ())
    }
}

fn read_column_str<'a, R: BufRead>(reader: &mut R, buffer: &'a mut Vec<u8>) -> Result<&'a str, ()> {
    buffer.clear();
    reader.read_until(b',', buffer).map_err(|_err| ())?;
    if buffer.is_empty() {
        Err(())
    } else {
        Ok(str::from_utf8(&buffer[..buffer.len() - 1]).unwrap())
    }
}

#[cfg(test)]
mod test {
    use super::*;

    use std::io::BufReader;

    #[test]
    fn test_print_data_packet_size() {
        println!("{}", DataPacket::MAX_SIZE);
    }

    #[test]
    fn test_ser_de_packet() {
        let data_packet = DataPacket {
            timestamp: 1609462800000,
            payload: PacketPayload::PIQuote {
                id: 1,
                market_id: 2,
                status: Status::Open,
                trade_price: 0.1,
                bid_price: 0.2,
                ask_price: 0.3,
            },
        };

        let mut write_buf = Vec::with_capacity(DataPacket::MAX_SER_SIZE);
        data_packet.csv_serialize(&mut write_buf);
        assert_eq!(
            str::from_utf8(&write_buf[..]).unwrap(),
            "1609462800000,piquote,1,2,OPEN,0.1,0.2,0.3,\n"
        );

        let mut write_buf_reader = BufReader::new(&write_buf[..]);
        let mut read_buf = Vec::with_capacity(DataPacket::MAX_SER_SIZE);
        let deser_data_packet = DataPacket::csv_deserialize(&mut write_buf_reader, &mut read_buf).unwrap();
        assert_eq!(deser_data_packet, data_packet);
    }
}
