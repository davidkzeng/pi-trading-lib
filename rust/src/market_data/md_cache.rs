use std::collections::{HashSet, HashMap};

use chrono::{DateTime, Utc};

use crate::base::{PIDataState, ContractPrice};
use crate::actor::ActorBuffer;
use crate::market_data::{
    ContractData,
    MarketData,
    PIDataPacket,
    DataPacket,
    PacketPayload,
    MarketDataListener,
    RawMarketDataListener,
    MarketDataProvider,
    RawMarketDataProvider
};

pub struct RawToRawMarketDataCache {
    state: PIDataState,
    output: ActorBuffer<PIDataPacket>
}

impl RawToRawMarketDataCache {
    pub fn new(state: PIDataState) -> Self {
        RawToRawMarketDataCache { state, output: ActorBuffer::new() }
    }

    fn ingest_and_filter(&mut self, data: &PIDataPacket) -> bool {
        let updated_markets: HashSet<u64> = ingest_data(&mut self.state, &data).iter()
            .map(|(k, _v)| *k)
            .collect();

        let filtered_updates: HashMap<u64, MarketData> = data.market_updates.iter()
            .filter(|(k, _v)| updated_markets.contains(k))
            .map(|(k, v)| (*k, v.clone()))
            .collect();

        self.output.push(PIDataPacket { market_updates: filtered_updates });
        true
    }
}

impl RawMarketDataListener for RawToRawMarketDataCache {
    fn process_raw_market_data(&mut self, data: &PIDataPacket) -> bool {
        self.ingest_and_filter(data)
    }
}

impl RawMarketDataProvider for RawToRawMarketDataCache {
    fn fetch_raw_market_data(&mut self) -> Option<&PIDataPacket> {
        self.output.deque_ref()
    }
}

pub struct RawMarketDataCache {
    state: PIDataState,
    output: ActorBuffer<DataPacket>
}

impl RawMarketDataCache {
    pub fn new(state: PIDataState) -> Self {
        RawMarketDataCache { state, output: ActorBuffer::with_capacity(4096) }
    }

    fn ingest_and_transform(&mut self, data: &PIDataPacket) -> usize {
        let updated_market_constracts = ingest_data(&mut self.state, data);
        let mut nout = 0;

        for (&market_id, contract_ids) in updated_market_constracts.iter() {
            let market_state = self.state.get_market(market_id).unwrap();
            for &contract_id in contract_ids.iter() {
                let contract_state = self.state.get_contract(contract_id).unwrap();
                let data_packet = DataPacket {
                    timestamp:  contract_state.data_ts,
                    payload: PacketPayload::PIQuote {
                        id: contract_state.id,
                        market_id: contract_state.market_id,
                        name: contract_state.name.clone(), // TODO: This is inefficient
                        market_name: market_state.name.clone(),
                        status: contract_state.status,
                        trade_price: contract_state.prices.trade_price,
                        ask_price: contract_state.prices.ask_price,
                        bid_price: contract_state.prices.bid_price,
                    }
                };
                self.output.push(data_packet);
                nout += 1
            }
        }

        nout
    }
}

impl RawMarketDataListener for RawMarketDataCache {
    fn process_raw_market_data(&mut self, data: &PIDataPacket) -> bool {
        self.ingest_and_transform(data);
        true
    }
}

impl MarketDataProvider for RawMarketDataCache {
    fn fetch_market_data(&mut self) -> Option<&DataPacket> {
        self.output.deque_ref()
    }
}

pub struct MarketDataCache {
    state: PIDataState,
    output: ActorBuffer<DataPacket>
}

impl MarketDataCache {
    pub fn new(state: PIDataState) -> Self {
        MarketDataCache { state, output: ActorBuffer::new() }
    }
}

impl MarketDataListener for MarketDataCache {
    fn process_market_data(&mut self, data: &DataPacket) -> bool {
        let mut update = false;

        match data.payload {
            PacketPayload::PIQuote { id, market_id, status, trade_price, bid_price, ask_price, .. } => {
                if !self.state.has_market(market_id) {
                    self.state.add_market(market_id, "");
                }

                if !self.state.has_contract(id) {
                    self.state.add_contract(id, market_id, "")
                }

                let contract = self.state.get_contract_mut(id).unwrap();

                if contract.data_ts > data.timestamp {
                    println!("Warning: Timestamp for contract {} went backwards from {} to {}", contract.id,
                            contract.data_ts, data.timestamp);
                } else {
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
        
        if update {
            self.output.push(data.clone()); // Should we clone??
        }
        update
    }
}

fn ingest_data(state: &mut PIDataState, data: &PIDataPacket) -> HashMap<u64, Vec<u64>> {
    let mut updated_markets = HashMap::new();
    for (&market_id, market_data) in data.market_updates.iter() {
        let market_updates = ingest_one_market_data(state,market_data);
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

fn ingest_one_contract_data(state: &mut PIDataState, market_id: u64, contract_data: &ContractData, ts: DateTime<Utc>) -> bool {
    let mut update = false;

    if !state.has_contract(contract_data.id) {
        state.add_contract(contract_data.id, market_id, &contract_data.name);
        update = true;
    }

    let contract = state.get_contract_mut(contract_data.id).unwrap();
    assert!(contract.market_id == market_id);

    if contract.data_ts > ts {
        println!("Warning: Timestamp for contract {} went backwards from {} to {}", contract.id,
                contract.data_ts, ts);
        return false;
    }

    if contract.status != contract_data.status {
        contract.status = contract_data.status;
        update = true;
    }

    let new_prices = ContractPrice::new(contract_data.trade_price,
        contract_data.ask_price, contract_data.bid_price);
    if contract.prices != new_prices {
        contract.prices = new_prices;
        update = true;
    }

    update
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_true() {
        assert_eq!("lol", "lol");
    }
}
