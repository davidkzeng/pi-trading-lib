extern crate quick_xml;
extern crate ureq;

mod market_data;

fn main() {
    market_data::test();
    println!("Hello, world!");
}
