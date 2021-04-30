use std::collections::{HashSet, HashMap};

use crate::base::{PIDataState, Contract, Market, ContractPrice};
use crate::market_data::{
    ContractData,
    MarketData,
    PIDataPacket,
    DataPacket,
    PacketPayload
};


fn ingest_one_contract_data(state: &mut PIDataState, market_id: u64, contract_data: &ContractData) -> bool {
    let mut update = false;

    if let Some(contract) = state.get_contract_mut(contract_data.id) {
        assert!(contract.market_id == market_id);

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
    } else {
        let new_contract = Contract {
            id: contract_data.id,
            name: contract_data.name.clone(),
            market_id,
            status: contract_data.status,
            prices: ContractPrice::new(contract_data.trade_price,
                contract_data.ask_price, contract_data.bid_price)
        };
        state.add_contract(new_contract);
        update = true;
    }

    update
}

fn ingest_one_market_data(state: &mut PIDataState, market_data: &MarketData) -> Vec<u64> {
    let mut updated_contracts = Vec::new();
    let market_id = market_data.id;
    if let Some(market) = state.get_market_mut(market_id) {
        if market_data.timestamp >= market.data_ts {
            for contract_data in &market_data.contracts {
                let contract_update = ingest_one_contract_data(state,market_id, contract_data);
                if contract_update {
                    updated_contracts.push(contract_data.id);
                }
            }
        } else {
            println!("Warning: Timestamp for market {} went backwards from {} to {}", market.id,
                market.data_ts, market_data.timestamp);
        }
    } else {
        let new_market = Market {
            id: market_id,
            name: market_data.name.clone(),
            status: market_data.status,
            contracts: Vec::new(),
            data_ts: market_data.timestamp
        };
        state.add_market(new_market);
        for contract_data in &market_data.contracts {
            assert!(state.get_contract(contract_data.id).is_none());
            let contract_update = ingest_one_contract_data(state,market_id, contract_data);
            assert!(contract_update);
            updated_contracts.push(contract_data.id);
        }
    }
    updated_contracts
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

pub fn ingest_and_filter(state: &mut PIDataState, data: PIDataPacket) -> PIDataPacket {
    let updated_markets: HashSet<u64> = ingest_data(state, &data).iter()
        .map(|(k, _v)| *k)
        .collect();

    let filtered_updates: HashMap<u64, MarketData> = data.market_updates.into_iter()
        .filter(|(k, _v)| updated_markets.contains(k))
        .collect();

    PIDataPacket { market_updates: filtered_updates }
}

pub fn ingest_and_transform(state: &mut PIDataState, data: &PIDataPacket) -> Vec<DataPacket> {
    let updated_market_constracts = ingest_data(state, data);
    let mut output_data_packets = Vec::new();

    for (&market_id, contract_ids) in updated_market_constracts.iter() {
        let market_state = state.get_market(market_id).unwrap();
        for &contract_id in contract_ids.iter() {
            let contract_state = state.get_contract(contract_id).unwrap();
            let data_packet = DataPacket {
                timestamp:  market_state.data_ts,
                payload: PacketPayload::PIContractQuote {
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
            output_data_packets.push(data_packet)
        }
    }
    output_data_packets
}
