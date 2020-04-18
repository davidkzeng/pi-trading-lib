use pi_trading_lib::market_data::{self, PIDataPacket, MarketDataError, MarketData};
use pi_trading_lib::market_data::md_stream;
use pi_trading_lib::base::{PIDataState};

use std::collections::{HashSet, HashMap};

fn fetch_data_and_get_update(state: &mut PIDataState) -> Result<PIDataPacket, MarketDataError> {
    let data_packet = market_data::fetch_all_market_data()?;
    let updated_markets = md_stream::ingest_data(state, &data_packet);
    let updated_markets_set : HashSet<u64> = updated_markets
        .iter().cloned().collect();

    let timestamp = data_packet.timestamp.clone();
    let filtered_updates : HashMap<u64, MarketData> = data_packet.market_updates.into_iter()
        .filter(|(k, _v)| updated_markets_set.contains(k))
        .collect();

    Ok(PIDataPacket { market_updates: filtered_updates, timestamp: timestamp })
}

fn main() {
    let mut initial_state = PIDataState::new();
    let mut err_counter = 0;
    match fetch_data_and_get_update(&mut initial_state) {
        Ok(_data) => {
            if err_counter != 0 {
                err_counter = 0;
            }
        },
        Err(err) => {
            err_counter += 1;
            if err_counter >= 5 {
                // TODO (implement display)
                println!("Data is bad, most recent error {:?}", err);
            }
        }
    }
    println!("{:?}", initial_state);
}

