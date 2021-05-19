use std::collections::{HashMap, HashSet};

use chrono::{DateTime, Utc};

use crate::actor::{ActorBuffer, Listener, Provider};
use crate::base::{ContractPrice, PIDataState};
use crate::market_data::{ContractData, DataPacket, MarketData, PIDataPacket, PacketPayload};

pub struct RawToRawMarketDataCache {
    state: PIDataState,
    output: ActorBuffer<PIDataPacket>,
}

impl RawToRawMarketDataCache {
    pub fn new(state: PIDataState) -> Self {
        RawToRawMarketDataCache {
            state,
            output: ActorBuffer::new(),
        }
    }

    fn ingest_and_filter(&mut self, data: &PIDataPacket) -> bool {
        let updated_markets: HashSet<u64> = ingest_data(&mut self.state, &data).iter().map(|(k, _v)| *k).collect();

        let filtered_updates: HashMap<u64, MarketData> = data
            .market_updates
            .iter()
            .filter(|(k, _v)| updated_markets.contains(k))
            .map(|(k, v)| (*k, v.clone()))
            .collect();

        self.output.push(PIDataPacket {
            market_updates: filtered_updates,
        });
        true
    }
}

impl Listener<PIDataPacket> for RawToRawMarketDataCache {
    fn process(&mut self, data: &PIDataPacket) -> bool {
        self.ingest_and_filter(data)
    }
}

impl Provider<PIDataPacket> for RawToRawMarketDataCache {
    fn output_buffer(&mut self) -> &mut ActorBuffer<PIDataPacket> {
        &mut self.output
    }
}

pub struct RawMarketDataCache {
    state: PIDataState,
    output: ActorBuffer<DataPacket>,
}

impl RawMarketDataCache {
    pub fn new(state: PIDataState) -> Self {
        RawMarketDataCache {
            state,
            output: ActorBuffer::with_capacity(4096),
        }
    }

    fn ingest_and_transform(&mut self, data: &PIDataPacket) -> usize {
        let updated_market_constracts = ingest_data(&mut self.state, data);
        let mut nout = 0;

        for (&market_id, contract_ids) in updated_market_constracts.iter() {
            for &contract_id in contract_ids.iter() {
                let contract_state = self.state.get_contract(contract_id).unwrap();
                let data_packet = DataPacket {
                    timestamp: contract_state.data_ts,
                    payload: PacketPayload::PIQuote {
                        id: contract_state.id,
                        market_id,
                        status: contract_state.status,
                        trade_price: contract_state.prices.trade_price,
                        ask_price: contract_state.prices.ask_price,
                        bid_price: contract_state.prices.bid_price,
                    },
                };
                self.output.push(data_packet);
                nout += 1
            }
        }

        nout
    }
}

impl Listener<PIDataPacket> for RawMarketDataCache {
    fn process(&mut self, data: &PIDataPacket) -> bool {
        self.ingest_and_transform(data) > 0
    }
}

impl Provider<DataPacket> for RawMarketDataCache {
    fn output_buffer(&mut self) -> &mut ActorBuffer<DataPacket> {
        &mut self.output
    }
}

pub struct MarketDataCache {
    pub state: PIDataState,
    output: ActorBuffer<DataPacket>,
}

impl MarketDataCache {
    pub fn new(state: PIDataState) -> Self {
        MarketDataCache {
            state,
            output: ActorBuffer::new(),
        }
    }
}

impl Listener<DataPacket> for MarketDataCache {
    fn process(&mut self, data: &DataPacket) -> bool {
        let update = ingest_data_packet(&mut self.state, data);
        if update {
            self.output.push(data.clone());
        }
        update
    }
}

/// Outputs DataPackets that resulted in a market data update
impl Provider<DataPacket> for MarketDataCache {
    fn output_buffer(&mut self) -> &mut ActorBuffer<DataPacket> {
        &mut self.output
    }
}

// TODO: Delayed vs standard should be more transport. Maybe just a param?
/// Naive, memory-hungry implementation of a market data cache with delayed message processing
///
/// This implementation is useful for when data packet arrival rate is less than the
/// desired sample rate (if using a sampling based method)
pub struct DelayedMarketDataCache {
    pub state: PIDataState,
    delay_time: u64,
    delay_buffer: ActorBuffer<DataPacket>,
    output: ActorBuffer<DataPacket>,
}

impl DelayedMarketDataCache {
    pub fn new(state: PIDataState, delay_time: u64, capacity: usize) -> Self {
        assert!(delay_time > 0);
        DelayedMarketDataCache {
            state,
            delay_time,
            delay_buffer: ActorBuffer::with_capacity(capacity),
            output: ActorBuffer::with_capacity(capacity),
        }
    }
}

impl Listener<DataPacket> for DelayedMarketDataCache {
    fn process(&mut self, data: &DataPacket) -> bool {
        let delay_ts = data.timestamp - (self.delay_time as i64);
        while let Some(buf_data) = self.delay_buffer.peek() {
            if buf_data.timestamp <= delay_ts {
                let update = ingest_data_packet(&mut self.state, data);
                if update {
                    self.output.push(buf_data.clone());
                }
                self.delay_buffer.deque_ref();
            } else {
                break;
            }
        }
        self.delay_buffer.push(data.clone());

        true
    }
}

impl Provider<DataPacket> for DelayedMarketDataCache {
    fn output_buffer(&mut self) -> &mut ActorBuffer<DataPacket> {
        &mut self.output
    }
}

fn ingest_data_packet(state: &mut PIDataState, data: &DataPacket) -> bool {
    let mut update = false;

    match data.payload {
        PacketPayload::PIQuote {
            id,
            market_id,
            status,
            trade_price,
            bid_price,
            ask_price,
            ..
        } => {
            if !state.has_market(market_id) {
                state.add_market(market_id, "");
            }

            if !state.has_contract(id) {
                state.add_contract(id, market_id, "")
            }

            let contract = state.get_contract_mut(id).unwrap();

            if contract.data_ts > data.timestamp {
                println!(
                    "Warning: Timestamp for contract {} went backwards from {} to {}",
                    contract.id, contract.data_ts, data.timestamp
                );
            } else {
                contract.data_ts = data.timestamp;

                if contract.status != status {
                    contract.status = status;
                    update = true;
                }

                let new_prices = ContractPrice::new(trade_price, ask_price, bid_price);
                if contract.prices != new_prices {
                    contract.prices = new_prices;
                    update = true;
                }
            }
        }
    }

    update
}

fn ingest_data(state: &mut PIDataState, data: &PIDataPacket) -> HashMap<u64, Vec<u64>> {
    let mut updated_markets = HashMap::new();
    for (&market_id, market_data) in data.market_updates.iter() {
        let market_updates = ingest_one_market_data(state, market_data);
        if market_updates.len() > 0 {
            updated_markets.insert(market_id, market_updates);
        }
    }
    updated_markets
}

fn ingest_one_market_data(state: &mut PIDataState, market_data: &MarketData) -> Vec<u64> {
    let mut updated_contracts = Vec::new();
    let market_id = market_data.id;

    if !state.has_market(market_id) {
        state.add_market(market_id, &market_data.name);
        for contract_data in &market_data.contracts {
            assert!(state.get_contract(contract_data.id).is_none());
        }
    }

    for contract_data in &market_data.contracts {
        let contract_update = ingest_one_contract_data(state, market_id, contract_data, market_data.timestamp);
        if contract_update {
            updated_contracts.push(contract_data.id);
        }
    }
    updated_contracts
}

fn ingest_one_contract_data(
    state: &mut PIDataState,
    market_id: u64,
    contract_data: &ContractData,
    ts: DateTime<Utc>,
) -> bool {
    let mut update = false;

    if !state.has_contract(contract_data.id) {
        state.add_contract(contract_data.id, market_id, &contract_data.name);
        update = true;
    }

    let contract = state.get_contract_mut(contract_data.id).unwrap();
    assert!(contract.market_id == market_id);

    if contract.data_ts > ts.timestamp_millis() {
        println!(
            "Warning: Timestamp for contract {} went backwards from {} to {}",
            contract.id, contract.data_ts, ts
        );
        return false;
    }

    contract.data_ts = ts.timestamp_millis();

    if contract.status != contract_data.status {
        contract.status = contract_data.status;
        update = true;
    }

    let new_prices = ContractPrice::new(
        contract_data.trade_price,
        contract_data.ask_price,
        contract_data.bid_price,
    );
    if contract.prices != new_prices {
        contract.prices = new_prices;
        update = true;
    }

    update
}

#[cfg(test)]
mod test {
    use super::*;

    use crate::base::Status;

    #[test]
    fn test_market_data_cache() {
        let mut market_data_cache = MarketDataCache::new(PIDataState::new());

        let packet1 = DataPacket::new(1, PacketPayload::new_piquote(0, 0, Status::Open, 0.2, 0.3, 0.2));
        let packet2 = DataPacket::new(2, PacketPayload::new_piquote(0, 0, Status::Open, 0.2, 0.3, 0.2));
        let packet3 = DataPacket::new(3, PacketPayload::new_piquote(0, 0, Status::Open, 0.3, 0.3, 0.2));
        let packet4 = DataPacket::new(2, PacketPayload::new_piquote(0, 0, Status::Open, 0.2, 0.3, 0.2));

        // New contract in cache
        market_data_cache.process(&packet1);
        assert!(market_data_cache.state.has_contract(0));
        assert!(market_data_cache.state.has_market(0));
        let output1 = market_data_cache.fetch();
        match output1 {
            Some(out) => {
                assert_eq!(&packet1, out);
            }
            None => {
                assert!(false);
            }
        }

        // No cache update
        market_data_cache.process(&packet1);
        market_data_cache.process(&packet2);
        assert!(market_data_cache.fetch().is_none());

        // Update cache
        market_data_cache.process(&packet3);
        assert_eq!(market_data_cache.state.get_contract(0).unwrap().prices.trade_price, 0.3);
        let output3 = market_data_cache.fetch();
        match output3 {
            Some(out) => {
                assert_eq!(&packet3, out);
            }
            None => {
                assert!(false);
            }
        }

        // Ignore backwards time jump
        market_data_cache.process(&packet4);
        assert_eq!(market_data_cache.state.get_contract(0).unwrap().prices.trade_price, 0.3);
        assert!(market_data_cache.fetch().is_none());
    }
}
