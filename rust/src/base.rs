use std::collections::HashMap;
use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum Status {
    Open,
    Closed,
}

impl fmt::Display for Status {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match *self {
            Status::Open => write!(f, "OPEN"),
            Status::Closed => write!(f, "CLOSED"),
        }
    }
}

impl FromStr for Status {
    type Err = ();

    fn from_str(input: &str) -> Result<Status, Self::Err> {
        match input {
            "OPEN" => Ok(Status::Open),
            "CLOSED" => Ok(Status::Closed),
            _ => Err(()),
        }
    }
}

#[derive(Debug)]
pub struct Market {
    pub id: u64,
    pub name: String,
    pub contracts: Vec<u64>,
}

// TODO: Refactor out status into separate from contract
#[derive(Debug)]
pub struct Contract {
    pub id: u64,
    pub market_id: u64,
    pub name: String,
    pub status: Status,
    pub prices: ContractPrice,
    pub data_ts: i64,
}

impl Contract {
    pub fn new(id: u64, market_id: u64, name: String) -> Self {
        Contract {
            id,
            market_id,
            name,
            status: Status::Closed,
            prices: ContractPrice::new(0.0, 0.0, 0.0),
            data_ts: 0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ContractPrice {
    pub trade_price: f64,
    pub ask_price: f64,
    pub bid_price: f64,
}

impl ContractPrice {
    pub fn new(trade_price: f64, ask_price: f64, bid_price: f64) -> Self {
        ContractPrice {
            trade_price,
            ask_price,
            bid_price,
        }
    }
}

#[derive(Debug)]
pub struct PIDataState {
    markets: HashMap<u64, Market>,
    contracts: HashMap<u64, Contract>,
}

impl PIDataState {
    pub fn new() -> Self {
        PIDataState {
            markets: HashMap::new(),
            contracts: HashMap::new(),
        }
    }

    pub fn get_market(&self, id: u64) -> Option<&Market> {
        self.markets.get(&id)
    }

    pub fn get_contract(&self, id: u64) -> Option<&Contract> {
        self.contracts.get(&id)
    }

    pub fn get_market_mut(&mut self, id: u64) -> Option<&mut Market> {
        self.markets.get_mut(&id)
    }

    pub fn get_contract_mut(&mut self, id: u64) -> Option<&mut Contract> {
        self.contracts.get_mut(&id)
    }

    pub fn add_contract(&mut self, id: u64, market_id: u64, name: &str) {
        assert!(!self.has_contract(id));

        let market = self.markets.get_mut(&market_id).unwrap();
        market.contracts.push(id);
        self.contracts
            .insert(id, Contract::new(id, market_id, name.to_string()));
    }

    pub fn add_market(&mut self, id: u64, name: &str) {
        assert!(!self.has_market(id));
        self.markets.insert(
            id,
            Market {
                id,
                name: name.to_string(),
                contracts: Vec::new(),
            },
        );
    }

    pub fn has_market(&self, id: u64) -> bool {
        self.get_market(id).is_some()
    }

    pub fn has_contract(&self, id: u64) -> bool {
        self.get_contract(id).is_some()
    }

    pub fn contract_mid_price(&self, id: u64) -> Option<f64> {
        self.get_contract(id)
            .map(|contract| (contract.prices.bid_price + contract.prices.ask_price) * 0.5)
    }
}
