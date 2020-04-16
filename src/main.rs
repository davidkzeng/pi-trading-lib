mod base;
mod market_data;

fn main() {
    let mut initial_state = base::PIDataState::new();
    market_data::fetch_and_update_state(&mut initial_state);
}
