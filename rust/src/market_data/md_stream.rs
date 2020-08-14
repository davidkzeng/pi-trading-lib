use std::collections::{HashSet, HashMap};

use crate::base::{PIDataState, Contract, Market, ContractPrice};
use crate::market_data::{
    ContractData,
    MarketData,
    PIDataPacket,
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
    }
    
    update
}

fn ingest_one_market_data(state: &mut PIDataState, market_data: &MarketData) -> bool {
    let mut updated = false;
    let market_id = market_data.id;
    if let Some(market) = state.get_market_mut(market_id) {
        if market.status != market_data.status {
            market.status = market_data.status;
            updated = true;
        }
        for contract_data in &market_data.contracts {
            let contract_update = ingest_one_contract_data(state,market_id, contract_data);
            updated |= contract_update;
        }
    } else {
        let new_market = Market {
            id: market_id,
            name: market_data.name.clone(),
            status: market_data.status,
            contracts: Vec::new()
        };
        state.add_market(new_market);
        for contract_data in &market_data.contracts {
            let contract_update = ingest_one_contract_data(state,market_id, contract_data);
            updated |= contract_update;
        }
        updated = true;
    }
    updated
}

pub fn ingest_data(state: &mut PIDataState, data: &PIDataPacket) -> Vec<u64> {
    let mut updated_markets = Vec::new();
    for (&market_id, market_data) in data.market_updates.iter() {
        let market_update = ingest_one_market_data(state,market_data);
        if market_update {
            updated_markets.push(market_id);
        }
    }
    state.update_pi_data_ts(&data.timestamp);
    updated_markets
}

pub fn ingest_data_and_get_filtered(state: &mut PIDataState, data: PIDataPacket) -> PIDataPacket {
    let updated_markets = ingest_data(state, &data);
    let updated_markets_set: HashSet<u64> = updated_markets
        .iter().cloned().collect();

    let timestamp = data.timestamp.clone();
    let filtered_updates: HashMap<u64, MarketData> = data.market_updates.into_iter()
        .filter(|(k, _v)| updated_markets_set.contains(k))
        .collect();

    PIDataPacket { market_updates: filtered_updates, timestamp }
}
