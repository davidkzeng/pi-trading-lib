use quick_xml::Reader;

pub fn fetch_data(market_id: u32) {
    let api_address = format!("https://www.predictit.org/api/marketdata/markets/{}", market_id);
    let resp = ureq::get(&api_address)
        .call();

    if resp.ok() {
        let text = resp.into_string().unwrap();
        let mut reader = Reader::from_str(&text);
        reader.trim_text(true);
    }
}

pub fn test() {
    fetch_data(2721);
    println!("Market_data");
}
