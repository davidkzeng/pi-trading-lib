use std::time::{SystemTime, UNIX_EPOCH};
use std::fs::File;
use std::io::Write;
use std::collections::{HashSet, HashMap};
use std::{env, thread, time};
use std::convert::TryInto;

use pi_trading_lib::market_data::{self, PIDataPacket, MarketDataError, MarketData};
use pi_trading_lib::market_data::md_stream;
use pi_trading_lib::base::{PIDataState};

const RETRY_LIMIT: u64 = 5;

fn fetch_data_and_get_update(state: &mut PIDataState) -> Result<PIDataPacket, MarketDataError> {
    let data_packet = market_data::fetch_all_market_data()?;
    let updated_markets = md_stream::ingest_data(state, &data_packet);
    let updated_markets_set: HashSet<u64> = updated_markets
        .iter().cloned().collect();

    let timestamp = data_packet.timestamp.clone();
    let filtered_updates: HashMap<u64, MarketData> = data_packet.market_updates.into_iter()
        .filter(|(k, _v)| updated_markets_set.contains(k))
        .collect();

    Ok(PIDataPacket { market_updates: filtered_updates, timestamp: timestamp })
}

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

    let mut initial_state = PIDataState::new();
    let mut output_file = File::create(output_file_name).expect("Unable to create output file");

    println!("Starting market data reading");
    let end_time = loop {
        let loop_start_time = current_time_millis();
        let next_loop_time = current_time_millis() + 5 * 1000;

        if loop_start_time > die_time_millis {
            break loop_start_time;
        }
        println!("Fetch market data at time {}", current_time_millis());

        let mut valid_data = false;
        for _err_counter in 0..RETRY_LIMIT {
            match fetch_data_and_get_update(&mut initial_state) {
                Ok(update_data) => {
                    let update_data_str = format!("{:?}", update_data);
                    println!("{}", update_data_str);
                    output_file.write_all(update_data_str.as_bytes()).expect("Unable to write data");
                    valid_data = true;
                    break;
                },
                Err(err) => {
                    println!("Encountered market data error {:?}", err);
                }
            }
        }
        if !valid_data {
            println!("Too many market data errors");
            break loop_start_time;
        }

        let mut sleep_time: i64 = TryInto::<i64>::try_into(next_loop_time).unwrap() -
            TryInto::<i64>::try_into(current_time_millis()).unwrap();
        if sleep_time < 0 {
            println!("Falling behind market data update");
            sleep_time = 0;
        }
        thread::sleep(time::Duration::from_millis(sleep_time.try_into().unwrap()));
    };

    println!("Finished market data archiving at time {}", end_time);
}

