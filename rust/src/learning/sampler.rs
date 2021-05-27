use std::collections::VecDeque;
use std::io::Write;

use csv;

use crate::actor::{self, ActorBuffer, Listener, Provider};
use crate::base::PIDataState;
use crate::market_data::md_cache::{DelayedMarketDataCache, MarketDataCache};
use crate::market_data::{DataPacket, PacketPayload};
use crate::parser::*;

#[derive(Clone)]
pub struct SampleData {
    pub id: u64,
    pub timestamp: i64,
    pub back_price: f64,
    pub tick_price: f64,
    pub forward_price: f64,
}

pub struct SamplerWriter<W: Write> {
    csv_writer: csv::Writer<W>,
}

impl<W: Write> SamplerWriter<W> {
    pub fn new(writer: W) -> Self {
        let mut csv_writer = csv::Writer::from_writer(writer);
        csv_writer
            .write_record(&["id", "timestamp", "back", "tick", "forward"])
            .unwrap();
        SamplerWriter { csv_writer }
    }
}

impl<W: Write> Listener<SampleData> for SamplerWriter<W> {
    fn process(&mut self, sample: &SampleData) -> bool {
        self.csv_writer
            .write_record(&[
                sample.id.to_string(),
                sample.timestamp.to_string(),
                sample.back_price.to_string(),
                sample.tick_price.to_string(),
                sample.forward_price.to_string(),
            ])
            .unwrap();
        true
    }
}

pub struct Sampler {
    window: u64,
    forward_sample_queue: VecDeque<(i64, SampleData)>,
    output: ActorBuffer<SampleData>,
}

impl Sampler {
    fn new(window: u64) -> Self {
        Sampler {
            window,
            forward_sample_queue: VecDeque::new(),
            output: ActorBuffer::new(),
        }
    }

    pub fn post_process(&mut self, data: &DataPacket, market_data_cache: &MarketDataCache) -> bool {
        while data.timestamp > self.forward_sample_queue.back().map(|(ts, _)| *ts).unwrap_or(i64::MAX) {
            let (_, mut sample) = self.forward_sample_queue.pop_back().unwrap();
            if let Some(forward_price) = market_data_cache.state.contract_mid_price(sample.id) {
                let contract_spread = market_data_cache.state.contract_spread(sample.id).unwrap();
                if contract_spread > 0.04 {
                    continue;
                }
                sample.forward_price = forward_price;
                self.output.push(sample);
            }
        }

        true
    }

    pub fn pre_process(
        &mut self,
        data: &DataPacket,
        market_data_cache: &MarketDataCache,
        delayed_market_data_cache: &DelayedMarketDataCache,
    ) -> bool {
        match data.payload {
            PacketPayload::PIQuote { id, .. } => {
                if let Some(back_price) = delayed_market_data_cache.state.contract_mid_price(id) {
                    if let Some(tick_price) = market_data_cache.state.contract_mid_price(id) {
                        let back_contract_spread = market_data_cache.state.contract_spread(id).unwrap();
                        let contract_spread = delayed_market_data_cache.state.contract_spread(id).unwrap();
                        if contract_spread > 0.04 || back_contract_spread > 0.04 {
                            return true;
                        }
                        self.forward_sample_queue.push_front((
                            data.timestamp + (self.window as i64),
                            SampleData {
                                id,
                                timestamp: data.timestamp,
                                back_price,
                                tick_price,
                                forward_price: 0.0,
                            },
                        ));
                    }
                }
            }
        }

        true
    }
}

impl Provider<SampleData> for Sampler {
    fn output_buffer(&mut self) -> &mut ActorBuffer<SampleData> {
        &mut self.output
    }
}

pub fn register_args(parser: Parser) -> Parser {
    parser.arg(Arg::with_name("sampler-window").takes_value().required())
}

pub fn get_args(parser: &Parser) -> u64 {
    parser.get_str_arg("sampler-window").unwrap().parse::<u64>().unwrap()
}

pub fn sample<W: Write, T: Provider<DataPacket>>(input_market_data: &mut T, writer: W, args: &Parser) {
    let window = get_args(args);
    let mut market_data_cache = MarketDataCache::new(PIDataState::new());
    let mut delayed_market_data_cache = DelayedMarketDataCache::new(PIDataState::new(), window, 4096);

    let mut sampler = Sampler::new(window);

    let mut sampler_writer = SamplerWriter::new(writer);

    loop {
        let mut progress = 0;
        progress += actor::drain_to_fn(input_market_data, |data| {
            sampler.pre_process(data, &market_data_cache, &delayed_market_data_cache);
            market_data_cache.process(data);
            delayed_market_data_cache.process(data);
            sampler.post_process(data, &market_data_cache);

            true
        });

        progress += actor::drain_to(&mut sampler, &mut sampler_writer);
        actor::drain_sink(&mut market_data_cache);
        actor::drain_sink(&mut delayed_market_data_cache);

        if progress == 0 {
            break;
        }
    }
}
