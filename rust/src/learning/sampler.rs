use crate::actor::{self, Listener, Provider};
use crate::base::PIDataState;
use crate::market_data::md_cache::MarketDataCache;
use crate::market_data::MarketDataSimCsv;

#[allow(dead_code)]
pub struct AutoSampler {
    window: u64,
    front_sample: MarketDataCache,
    back_sample: MarketDataCache
}

pub fn sample(input_file_name: &str) {
    let mut input_market_data = MarketDataSimCsv::new(input_file_name);
    let mut market_data_cache = MarketDataCache::new(PIDataState::new());

    loop {
        let market_data = match input_market_data.fetch() {
            Some(market_data) => market_data,
            None => {
                break;
            }
        };

        market_data_cache.process(market_data);
        actor::drain(&mut market_data_cache);
    }
}
