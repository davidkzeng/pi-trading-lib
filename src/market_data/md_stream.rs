use crate::base::{PIDataState, Contract, Market, ContractPrice};
use crate::market_data::{ContractData, MarketData, PIDataPacket};

pub struct PIDataIngester<'a> {
    state: &'a mut PIDataState
}

impl<'a> PIDataIngester<'a> {
    pub fn new(state: &'a mut PIDataState) -> PIDataIngester<'a> {
        PIDataIngester { state: state }
    }

    fn ingest_one_contract_data(&mut self, market_id: u64, contract_data: &ContractData) -> bool {
        let mut update = false;
        
        if let Some(contract) = self.state.get_contract_mut(contract_data.id) {
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
                market_id: market_id,
                status: contract_data.status,
                prices: ContractPrice::new(contract_data.trade_price,
                    contract_data.ask_price, contract_data.bid_price)
            };
            self.state.add_contract(new_contract);
        }
        
        update
    }

    fn ingest_one_market_data(&mut self, market_data: &MarketData) -> bool {
        let mut updated = false;
        let market_id = market_data.id;
        if let Some(market) = self.state.get_market_mut(market_id) {
            if market.status != market_data.status {
                market.status = market_data.status;
                updated = true;
            }
            for contract_data in &market_data.contracts {
                let contract_update = self.ingest_one_contract_data(market_id, contract_data);
                updated |= contract_update;
            }
        } else {
            let new_market = Market {
                id: market_id,
                name: market_data.name.clone(),
                status: market_data.status,
                contracts: Vec::new()
            };
            self.state.add_market(new_market);
            for contract_data in &market_data.contracts {
                let contract_update = self.ingest_one_contract_data(market_id, contract_data);
                updated |= contract_update;
            }
            updated = true;
        }
        updated
    }

    pub fn ingest_data(&mut self, data: &PIDataPacket) -> Vec<u64> {
        let mut updated_markets = Vec::new();
        for (&market_id, market_data) in data.market_updates.iter() {
            let market_update = self.ingest_one_market_data(market_data);
            if market_update {
                updated_markets.push(market_id);
            }
        }
        updated_markets
    }
}
