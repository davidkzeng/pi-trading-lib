use std::env;
use std::fs::File;

use pi_trading_lib::learning::sampler;
use pi_trading_lib::market_data::MarketDataSimCsv;

fn main() {
    let args: Vec<String> = env::args().collect();
    assert_eq!(args.len(), 3);

    let input_file_name = &args[1];
    let output_file_name = &args[2];

    let mut input_market_data = MarketDataSimCsv::new(input_file_name);

    let output_file = File::create(output_file_name).expect("Unable to create output file");
    sampler::sample(&mut input_market_data, output_file, 10 * 60 * 1000);
}
