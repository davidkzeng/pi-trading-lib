use std::env;
use std::fs::File;

use pi_trading_lib::learning::sampler;
use pi_trading_lib::market_data::MarketDataSimCsv;
use pi_trading_lib::parser::{Arg, Parser};

fn main() {
    let parser = Parser::new()
        .arg(Arg::with_name("input").takes_value().required())
        .arg(Arg::with_name("output").takes_value().required())
        .create()
        .unwrap();
    let env_args: Vec<String> = env::args().collect();
    let args = parser.parse_args(env_args.iter()).unwrap();

    let input_file_name = args.get_str_arg("input").unwrap();
    let output_file_name = args.get_str_arg("output").unwrap();

    let mut input_market_data = MarketDataSimCsv::new(input_file_name);

    let output_file = File::create(output_file_name).expect("Unable to create output file");
    sampler::sample(&mut input_market_data, output_file, &args);
}
