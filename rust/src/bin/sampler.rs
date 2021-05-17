use std::env;
use std::fs::File;

use csv;

use pi_trading_lib::learning::sampler;
use pi_trading_lib::market_data::MarketDataSimCsv;

fn main() {
    let args: Vec<String> = env::args().collect();
    assert_eq!(args.len(), 3);

    let input_file_name = &args[1];
    let output_file_name = &args[2];

    let mut input_market_data = MarketDataSimCsv::new(input_file_name);

    let output_file = File::create(output_file_name).expect("Unable to create output file");
    let mut csv_writer = csv::Writer::from_writer(output_file);
    let samples = sampler::sample(&mut input_market_data, 10 * 60 * 1000);

    println!("Creating {} samples", samples.len());
    csv_writer.write_record(&["id", "timestamp", "back", "tick", "forward"]).unwrap();
    for sample in samples.into_iter() {
        csv_writer
            .write_record(&[
                sample.id.to_string(),
                sample.timestamp.to_string(),
                sample.back_price.to_string(),
                sample.tick_price.to_string(),
                sample.forward_price.to_string(),
            ])
            .unwrap();
    }
}
