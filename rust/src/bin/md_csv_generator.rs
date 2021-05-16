use std::env;
use std::fs::File;

use pi_trading_lib::actor::{Provider, Listener};
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

        while let Some(packet) = market_data_cache.fetch() {
            writer.process(packet);
            write_counter += 1;
            if write_counter % 1000 == 0 {
                println!("Wrote {} packets", write_counter);
            }
        }
    }

    println!("Wrote {} packets", write_counter);
    println!("Finished writing");
}
