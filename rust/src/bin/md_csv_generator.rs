use std::env;
use std::fs::File;

use pi_trading_lib::actor::components::CountLogger;
use pi_trading_lib::actor::{self, Listener};
use pi_trading_lib::base::PIDataState;
use pi_trading_lib::market_data::md_cache::RawMarketDataCache;
use pi_trading_lib::market_data::writer::DataPacketWriter;
use pi_trading_lib::market_data::{DataPacket, MarketDataSimJson};

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

    let mut write_counter = CountLogger::new("CSV writer");

    // MarketDataSimJson -> RawMarketDataCache -> Writer
    loop {
        let mut progress = 0;
        progress += actor::drain_to(&mut input_market_data, &mut market_data_cache);

        loop {
            let progress2 = actor::drain_to_fn(&mut market_data_cache, |data: &DataPacket| {
                writer.process(data);
                write_counter.process(data);
                true
            });
            progress += progress2;
            if progress2 == 0 {
                break;
            }
        }

        if progress == 0 {
            break;
        }
    }

    write_counter.report();
    println!("Finished writing");
}
