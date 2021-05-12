pub struct ActorBuffer<T> {
    buf: Vec<T>,
    capacity: usize,
    readptr: usize,
    writeptr: usize
}

pub const DEFAULT_BUFFER_SIZE: usize = 1024;

impl<T> ActorBuffer<T> {
    pub fn new() -> Self {
        ActorBuffer::with_capacity(DEFAULT_BUFFER_SIZE)
    }

    pub fn with_capacity(capacity: usize) -> Self {
        let mut buf: Vec<T> = Vec::new();
        buf.reserve(capacity);
        ActorBuffer { buf, capacity, readptr: 0, writeptr: 0 }
    }

    pub fn is_empty(&self) -> bool {
        self.readptr == self.writeptr
    }

    pub fn is_full(&self) -> bool {
        self.readptr == self.writeptr - self.capacity
    }

    pub fn push(&mut self, val: T) {
        if self.is_full() { panic!() }
        if self.writeptr < self.capacity {
            self.buf.push(val)
        } else {
            self.buf[self.writeptr % self.capacity] = val;
        }
        self.writeptr += 1;
    }

    pub fn deque_ref(&mut self) -> Option<&T> {
        if self.is_empty() {
            None
        } else {
            let res = &self.buf[self.readptr % self.capacity];
            self.readptr += 1;
            Some(res)
        }
    }
}
