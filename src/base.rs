use chrono::{DateTime, Utc};

use std::collections::HashMap;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Status {
    Open,
    Closed
}

#[derive(Debug)]
pub struct Market {
    pub id: u64,
    pub name: String,
    pub contracts: Vec<u64>,
    pub status: Status,
}

#[derive(Debug)]
pub struct Contract {
    pub id: u64,
    pub name: String,
    pub market_id: u64,
    pub status: Status,
    pub prices: ContractPrice
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ContractPrice {
    trade_price: f64,
    ask_price: f64,
    bid_price: f64
}

impl ContractPrice {
    pub fn new(trade_price: f64, ask_price: f64, bid_price: f64) -> Self {
        ContractPrice { trade_price: trade_price, ask_price: ask_price, bid_price: bid_price }
    }
}

// TODO: Define invariants
#[derive(Debug)]
pub struct PIDataState {
    markets: HashMap<u64, Market>,
    contracts: HashMap<u64, Contract>,
    pi_data_ts: Option<DateTime<Utc>>
}

impl PIDataState {
    pub fn new() -> Self {
        PIDataState { markets: HashMap::new(), contracts: HashMap::new(), pi_data_ts: None }
    }

    pub fn get_market_mut(&mut self, id: u64) -> Option<&mut Market> {
        self.markets.get_mut(&id)
    }

    pub fn get_contract_mut(&mut self, id: u64) -> Option<&mut Contract> {
        self.contracts.get_mut(&id)
    }

    pub fn add_contract(&mut self, contract: Contract) {
        let market_id = contract.market_id;
        // TODO: Replace with error, check invariants
        let market = self.markets.get_mut(&market_id).unwrap();
        market.contracts.push(contract.id);
        self.contracts.insert(contract.id, contract);
    }

    pub fn add_market(&mut self, market: Market) {
        self.markets.insert(market.id, market);
    }

    pub fn update_pi_data_ts(&mut self, ts: &DateTime<Utc>) {
        match &self.pi_data_ts {
            None => self.pi_data_ts = Some(*ts),
            Some(old_ts) => {
                assert!(ts >= old_ts);
                self.pi_data_ts = Some(*ts)
            }
        }
    }
}
