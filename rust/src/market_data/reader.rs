use std::fs::File;
use std::{thread, time};
use std::io::{BufRead, BufReader};

use crate::actor::ActorBuffer;
use crate::market_data::api_parser;
use crate::market_data::{PIDataPacket, DataPacket, RawMarketDataProvider, MarketDataResult, MarketDataProvider};

pub struct MarketDataLive {
    retry_limit: u64,
}

impl MarketDataLive {
    pub fn new() -> Self {
        MarketDataLive::new_with_retry(1)
    }

    pub fn new_with_retry(retry_limit: u64) -> Self {
        MarketDataLive { retry_limit }
    }

    pub fn fetch_market_data(&mut self) -> MarketDataResult {
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

pub struct MarketDataSimJson {
    data_reader: BufReader<File>,
    line_buffer: String,
    buffer: ActorBuffer<PIDataPacket>
}

impl MarketDataSimJson {
    pub fn new(filename: &str) -> Self {
        let data_file = File::open(filename).unwrap();
        MarketDataSimJson {
            data_reader: BufReader::new(data_file),
            line_buffer: String::new(),
            buffer: ActorBuffer::new(),
        }
    }
}

impl RawMarketDataProvider for MarketDataSimJson {
    fn fetch_raw_market_data(&mut self) -> Option<&PIDataPacket> {
        let bytes_read = self.data_reader.read_line(&mut self.line_buffer).unwrap();
        if bytes_read == 0 {
            return None;
        }
        self.buffer.push(serde_json::from_str(&mut self.line_buffer).unwrap());
        self.line_buffer.clear();
        self.buffer.deque_ref()
    }
}

pub struct MarketDataSimCsv {
    data_reader: BufReader<File>,
    read_buffer: Vec<u8>,
    buffer: ActorBuffer<DataPacket>
}

impl MarketDataSimCsv {
    pub fn new(filename: &str) -> Self {
        let data_file = File::open(filename).unwrap();
        let mut data_reader = BufReader::new(data_file);
        assert!(DataPacket::check_header(&mut data_reader));

        MarketDataSimCsv {
            data_reader,
            read_buffer: Vec::with_capacity(DataPacket::MAX_SER_SIZE),
            buffer: ActorBuffer::new(),
        }
    }
}

impl MarketDataProvider for MarketDataSimCsv {
    fn fetch_market_data(&mut self) -> Option<&DataPacket> {
        match DataPacket::csv_deserialize(&mut self.data_reader, &mut self.read_buffer) {
            Ok(data_packet) => {
                self.buffer.push(data_packet);
                self.buffer.deque_ref()
            },
            Err(_) => None, // ???
        }
    }
}
