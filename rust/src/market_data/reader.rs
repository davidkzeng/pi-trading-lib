use std::fs::File;
use std::io::{BufRead, BufReader};
use std::{thread, time};

use crate::actor::{ActorBuffer, Provider};
use crate::market_data::api_parser;
use crate::market_data::{DataPacket, MarketDataResult, PIDataPacket};

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
                }
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
    output: ActorBuffer<PIDataPacket>,
}

impl MarketDataSimJson {
    const BATCH_SIZE: usize = 64;

    pub fn new(filename: &str) -> Self {
        let data_file = File::open(filename).unwrap();
        MarketDataSimJson {
            data_reader: BufReader::new(data_file),
            line_buffer: String::new(),
            output: ActorBuffer::new(),
        }
    }
}

impl Provider<PIDataPacket> for MarketDataSimJson {
    fn output_buffer(&mut self) -> &mut ActorBuffer<PIDataPacket> {
        while self.output.size() < MarketDataSimJson::BATCH_SIZE {
            let bytes_read = self.data_reader.read_line(&mut self.line_buffer).unwrap();
            if bytes_read == 0 {
                break;
            }
            self.output.push(serde_json::from_str(&self.line_buffer).unwrap());
            self.line_buffer.clear();
        }
        &mut self.output
    }
}

pub struct MarketDataSimCsv {
    data_reader: BufReader<File>,
    read_buffer: Vec<u8>,
    output: ActorBuffer<DataPacket>,
}

impl MarketDataSimCsv {
    const BATCH_SIZE: usize = 64;

    pub fn new(filename: &str) -> Self {
        let data_file = File::open(filename).unwrap();
        let mut data_reader = BufReader::new(data_file);
        assert!(DataPacket::check_header(&mut data_reader));

        MarketDataSimCsv {
            data_reader,
            read_buffer: Vec::with_capacity(DataPacket::MAX_SER_SIZE),
            output: ActorBuffer::new(),
        }
    }
}

impl Provider<DataPacket> for MarketDataSimCsv {
    fn output_buffer(&mut self) -> &mut ActorBuffer<DataPacket> {
        while self.output.size() < MarketDataSimCsv::BATCH_SIZE {
            match DataPacket::csv_deserialize(&mut self.data_reader, &mut self.read_buffer) {
                Ok(data_packet) => {
                    self.output.push(data_packet);
                }
                Err(_) => {
                    break;
                } // ???
            }
        }
        &mut self.output
    }
}
