use std::env;
use std::fs::File;

use pi_trading_lib::actor::{self, Listener, Provider};
use pi_trading_lib::base::PIDataState;
use pi_trading_lib::market_data::md_cache::RawMarketDataCache;
use pi_trading_lib::market_data::writer::DataPacketWriter;
use pi_trading_lib::market_data::MarketDataSimJson;

fn main() {
    let args: Vec<String> = env::args().collect();
    assert_eq!(args.len(), 3);

    let input_file_name = &args[1];
    let output_file_name = &args[2];

    let mut input_market_data = MarketDataSimJson::new(input_file_name);

    let output_file = File::create(output_file_name).expect("Unable to create output file");
    let mut writer = DataPacketWriter::new(output_file);

    let data_state = PIDataState::new();
    let mut market_data_cache = RawMarketDataCache::new(data_state);

    let mut write_counter = 0;

    // MarketDataSimJson -> RawMarketDataCache -> Writer
    loop {
        let market_data = match input_market_data.fetch() {
            Some(market_data) => market_data,
            None => {
                break;
            }
        };

        market_data_cache.process(market_data);
        let packets_written = actor::drain_to(&mut market_data_cache, &mut writer);
        if (write_counter + packets_written) / 1024 > write_counter / 1024 {
            println!("Wrote {} packets", (write_counter / 1024 + 1) * 1024);
        }
        write_counter += packets_written;
    }

    println!("Wrote {} packets", write_counter);
    println!("Finished writing");
}
