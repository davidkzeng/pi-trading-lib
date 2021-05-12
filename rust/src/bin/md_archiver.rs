use std::time::{SystemTime, UNIX_EPOCH};
use std::fs::File;
use std::{env, thread, time};
use std::convert::TryInto;

use pi_trading_lib::market_data::{MarketDataLive, MarketDataSource, RawMarketDataListener, RawMarketDataProvider};
use pi_trading_lib::market_data::writer::PIDataPacketWriter;
use pi_trading_lib::market_data::md_stream::RawToRawMarketDataCache;
use pi_trading_lib::base::PIDataState;

const API_RETRY_LIMIT: u64 = 5;
const POLL_INTERVAL_SECS: u64 = 60; // PredictIt API update rate

fn current_time_millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went before unix epoch")
        .as_millis()
        .try_into().unwrap()
}

fn main() {
    let args: Vec<String> = env::args().collect();
    assert_eq!(args.len(), 3);

    println!("args: {:?}", args);

    let output_file_name = &args[1];
    let die_time_millis = args[2].parse::<u64>().expect("Unable to parse die time");

    let data_state = PIDataState::new();
    let mut market_data_cache = RawToRawMarketDataCache::new(data_state);

    let output_file = File::create(output_file_name).expect("Unable to create output file");
    let mut output_writer = PIDataPacketWriter::new(output_file);

    let mut loop_counter = 0;
    let mut api_market_data = MarketDataLive::new_with_retry(API_RETRY_LIMIT);

    println!("Starting market data reading");
    let end_time = loop {
        let loop_start_time = current_time_millis();
        let next_loop_time = current_time_millis() + POLL_INTERVAL_SECS * 1000;

        if loop_start_time > die_time_millis {
            println!("Exiting loop at time {}", current_time_millis());
            break loop_start_time;
        }
        println!("Fetch market data at time {}", current_time_millis());

        match api_market_data.fetch_market_data() {
            Ok(Some(market_data)) => {
                market_data_cache.process_raw_market_data(&market_data);
                if let Some(updated_market_data) = market_data_cache.fetch_raw_market_data() {
                    output_writer.process_raw_market_data(updated_market_data);
                }
            },
            Ok(None) => panic!("Current live md implementation should always return market data"),
            Err(err) => {
                println!("Unable to fetch market data: {:?}", err);
            }
        }

        if loop_counter % 60 == 0 {
            output_writer.flush();
        }

        let mut sleep_time: i64 = TryInto::<i64>::try_into(next_loop_time).unwrap() -
            TryInto::<i64>::try_into(current_time_millis()).unwrap();
        if sleep_time < 0 {
            println!("Warning: falling behind market data updates");
            sleep_time = 0;
        }
        thread::sleep(time::Duration::from_millis(sleep_time.try_into().unwrap()));
        loop_counter += 1;
    };

    println!("Finished market data archiving at time {}", end_time);
}

