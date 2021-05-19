use crate::actor::Listener;

pub struct CountLogger {
    name: &'static str,
    counter: u64,
    report_count: u64,
}

impl CountLogger {
    pub fn new(name: &'static str) -> Self {
        CountLogger {
            name,
            counter: 0,
            report_count: 1,
        }
    }

    pub fn report(&self) {
        println!("{} saw {} packets", self.name, self.counter);
    }
}

impl<I> Listener<I> for CountLogger {
    fn process(&mut self, _input: &I) -> bool {
        self.counter += 1;
        if self.counter >= self.report_count {
            self.report_count *= 2;
            self.report();
        }
        true
    }
}
