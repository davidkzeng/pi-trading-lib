use std::collections::VecDeque;

use crate::actor::{self, ActorBuffer, Listener, ListenerWithContext, Provider};
use crate::base::PIDataState;
use crate::market_data::md_cache::{DelayedMarketDataCache, MarketDataCache};
use crate::market_data::{DataPacket, PacketPayload};

#[derive(Clone)]
pub struct SampleData {
    pub id: u64,
    pub timestamp: i64,
    pub back_price: f64,
    pub tick_price: f64,
    pub forward_price: f64,
}

struct Sampler {
    window: u64,
    forward_sample_queue: VecDeque<(i64, SampleData)>,
    output: ActorBuffer<SampleData>,
}

struct SamplerContext<'a> {
    market_data_cache: &'a MarketDataCache,
    delayed_market_data_cache: &'a DelayedMarketDataCache,
}

impl<'a> SamplerContext<'a> {
    pub fn new(market_data_cache: &'a MarketDataCache, delayed_market_data_cache: &'a DelayedMarketDataCache) -> Self {
        SamplerContext {
            market_data_cache,
            delayed_market_data_cache,
        }
    }
}

impl<'a> ListenerWithContext<DataPacket, SamplerContext<'a>, 1> for Sampler {
    fn process_with_context(&mut self, data: &DataPacket, context: &SamplerContext<'a>) -> bool {
        let SamplerContext { market_data_cache, .. } = *context;
        while data.timestamp > self.forward_sample_queue.back().map(|(ts, _)| *ts).unwrap_or(i64::MAX) {
            let (_, mut sample) = self.forward_sample_queue.pop_back().unwrap();
            if let Some(forward_price) = market_data_cache.state.contract_mid_price(sample.id) {
                sample.forward_price = forward_price;
                self.output.push(sample);
            }
        }

        true
    }
}

impl<'a> ListenerWithContext<DataPacket, SamplerContext<'a>, 2> for Sampler {
    fn process_with_context(&mut self, data: &DataPacket, context: &SamplerContext<'a>) -> bool {
        let SamplerContext {
            market_data_cache,
            delayed_market_data_cache,
        } = *context;
        match data.payload {
            PacketPayload::PIQuote { id, .. } => {
                if let Some(back_price) = delayed_market_data_cache.state.contract_mid_price(id) {
                    if let Some(tick_price) = market_data_cache.state.contract_mid_price(id) {
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

impl Sampler {
    fn new(window: u64) -> Self {
        Sampler {
            window,
            forward_sample_queue: VecDeque::new(),
            output: ActorBuffer::with_capacity(100000),
        }
    }

    fn fetch(&mut self) -> Option<&SampleData> {
        self.output.deque_ref()
    }
}

pub fn sample<T: Provider<DataPacket>>(input_market_data: &mut T, window: u64) -> Vec<SampleData> {
    let mut market_data_cache = MarketDataCache::new(PIDataState::new());
    let mut delayed_market_data_cache = DelayedMarketDataCache::new(PIDataState::new(), window, 4096);

    let mut samples: Vec<SampleData> = Vec::new();
    let mut sampler = Sampler::new(window);

    while let Some(data) = input_market_data.fetch() {
        let sampler_context = SamplerContext::new(&market_data_cache, &delayed_market_data_cache);
        ListenerWithContext::<_, _, 1>::process_with_context(&mut sampler, data, &sampler_context);
        market_data_cache.process(data);
        delayed_market_data_cache.process(data);
        let sampler_context = SamplerContext::new(&market_data_cache, &delayed_market_data_cache);
        ListenerWithContext::<_, _, 2>::process_with_context(&mut sampler, data, &sampler_context);

        while let Some(sample_data) = sampler.fetch() {
            samples.push(sample_data.clone());
        }

        actor::drain(&mut market_data_cache);
        actor::drain(&mut delayed_market_data_cache);
    }

    samples
}
