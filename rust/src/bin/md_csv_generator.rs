use std::fs::File;
use std::io::BufWriter;
use std::env;

use pi_trading_lib::market_data::{
    MarketDataSimJson,
    MarketDataSource,
    md_stream,
    DataPacket
};
use pi_trading_lib::base::PIDataState;

fn main() {
    let args: Vec<String> = env::args().collect();
    assert_eq!(args.len(), 3);

    let input_file_name = &args[1];
    let output_file_name = &args[2];

    let mut data_state = PIDataState::new();
    let output_file = File::create(output_file_name).expect("Unable to create output file");
    let mut output_writer = BufWriter::new(output_file);

    let mut input_market_data = MarketDataSimJson::new(input_file_name);
    
    let mut write_counter = 0;

    DataPacket::write_header(&mut output_writer);

    while let Ok(Some(market_data)) = input_market_data.fetch_market_data() {
        let data_packets = md_stream::ingest_and_transform(&mut data_state, &market_data);
        for packet in &data_packets {
            packet.csv_serialize(&mut output_writer);
            write_counter += 1;
            if write_counter % 1000 == 0 {
                println!("Wrote {} packets", write_counter);
            }
        }
    }

    println!("Wrote {} packets", write_counter);
    println!("Finished writing");
}
