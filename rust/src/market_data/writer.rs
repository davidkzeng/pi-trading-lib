use std::io::{BufWriter, Write};

use crate::actor::Listener;
use crate::market_data::{DataPacket, PIDataPacket};

pub struct DataPacketWriter<W: Write> {
    output_writer: BufWriter<W>,
}

impl<W: Write> DataPacketWriter<W> {
    pub fn new(w: W) -> Self {
        let mut output_writer = BufWriter::new(w);
        DataPacket::write_header(&mut output_writer);
        DataPacketWriter { output_writer }
    }
}

impl<W: Write> Listener<DataPacket> for DataPacketWriter<W> {
    fn process(&mut self, data: &DataPacket) -> bool {
        data.csv_serialize(&mut self.output_writer);
        true
    }
}

pub struct PIDataPacketWriter<W: Write> {
    output_writer: BufWriter<W>,
}

impl<W: Write> PIDataPacketWriter<W> {
    pub fn new(w: W) -> Self {
        let output_writer = BufWriter::new(w);
        PIDataPacketWriter { output_writer }
    }

    pub fn flush(&mut self) {
        self.output_writer.flush().unwrap();
    }
}

impl<W: Write> Listener<PIDataPacket> for PIDataPacketWriter<W> {
    fn process(&mut self, data: &PIDataPacket) -> bool {
        let update_data_json = serde_json::to_string(data).unwrap();
        self.output_writer
            .write_all(update_data_json.as_bytes())
            .expect("Unable to write data");
        self.output_writer
            .write_all("\n".as_bytes())
            .expect("Unable to write new line");
        true
    }
}
