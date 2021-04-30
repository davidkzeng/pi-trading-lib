use std::fs::File;
use std::env;

use pi_trading_lib::market_data::{
    MarketDataSimJson,
    MarketDataSource,
    md_stream
};
use pi_trading_lib::base::PIDataState;

fn main() {
    let args: Vec<String> = env::args().collect();
    assert_eq!(args.len(), 3);

    let input_file_name = &args[1];
    let output_file_name = &args[2];

    let mut data_state = PIDataState::new();
    let _output_file = File::create(output_file_name).expect("Unable to create output file");

    let mut input_market_data = MarketDataSimJson::new(input_file_name);

    while let Ok(Some(market_data)) = input_market_data.fetch_market_data() {
        md_stream::ingest_and_transform(&mut data_state, &market_data);
    }
}
