use crate::actor::{self, Listener, Provider};
use crate::base::PIDataState;
use crate::market_data::md_cache::{DelayedMarketDataCache, MarketDataCache};
use crate::market_data::{DataPacket, PacketPayload};

pub struct SampleData {
    pub id: u64,
    pub back_price: f64,
    pub tick_price: f64,
    pub forward_price: f64,
}

pub fn sample<T: Provider<DataPacket>>(input_market_data: &mut T, window: u64) -> Vec<SampleData> {
    let mut market_data_cache = MarketDataCache::new(PIDataState::new());
    let mut delayed_market_data_cache = DelayedMarketDataCache::new(PIDataState::new(), window, 4096);

    let mut forward_sample_queue: Vec<(i64, SampleData)> = Vec::new(); // (sample_time, contract id)
    let mut samples: Vec<SampleData> = Vec::new();
    while let Some(data) = input_market_data.fetch() {
        while data.timestamp > forward_sample_queue.last().map(|(ts, _)| *ts).unwrap_or(i64::MAX) {
            let (_, mut sample) = forward_sample_queue.pop().unwrap();
            if let Some(forward_price) = market_data_cache.state.contract_mid_price(sample.id) {
                sample.forward_price = forward_price;
                samples.push(sample);
            }
        }

        market_data_cache.process(data);
        delayed_market_data_cache.process(data);

        match data.payload {
            PacketPayload::PIQuote { id, .. } => {
                if let Some(back_price) = delayed_market_data_cache.state.contract_mid_price(id) {
                    if let Some(tick_price) = market_data_cache.state.contract_mid_price(id) {
                        forward_sample_queue.push((
                            data.timestamp + (window as i64),
                            SampleData {
                                id,
                                back_price,
                                tick_price,
                                forward_price: 0.0,
                            },
                        ));
                    }
                }
            }
        }

        actor::drain(&mut market_data_cache);
        actor::drain(&mut delayed_market_data_cache);
    }

    samples
}
