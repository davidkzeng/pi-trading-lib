pub mod components;

pub trait Provider<O> {
    fn output_buffer(&mut self) -> &mut ActorBuffer<O>;

    fn fetch(&mut self) -> Option<&O> {
        self.output_buffer().deque_ref()
    }
}

/// Processes input messages
///
/// A listener can implement multiple variants, V, of ways to process a message
#[rustfmt::skip]
pub trait Listener<I, const V: usize = 1> {
    fn process(&mut self, input: &I) -> bool;
}

pub struct ActorBuffer<T> {
    buf: Vec<T>,
    capacity: usize,
    readptr: usize,
    writeptr: usize,
}

pub const DEFAULT_BUFFER_SIZE: usize = 1024;

/// Simple ring buffer
impl<T> ActorBuffer<T> {
    pub fn new() -> Self {
        ActorBuffer::with_capacity(DEFAULT_BUFFER_SIZE)
    }

    pub fn with_capacity(capacity: usize) -> Self {
        let mut buf: Vec<T> = Vec::new();
        buf.reserve(capacity);
        ActorBuffer {
            buf,
            capacity,
            readptr: 0,
            writeptr: 0,
        }
    }

    pub fn size(&self) -> usize {
        self.writeptr - self.readptr
    }

    pub fn is_empty(&self) -> bool {
        self.readptr >= self.writeptr
    }

    pub fn is_full(&self) -> bool {
        self.readptr + self.capacity <= self.writeptr
    }

    pub fn push(&mut self, val: T) {
        // TODO: Allow this to alloc but warn
        if self.is_full() {
            panic!()
        }
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

    pub fn peek(&self) -> Option<&T> {
        if self.is_empty() {
            None
        } else {
            Some(&self.buf[self.readptr % self.capacity])
        }
    }
}

/// Drains Provider until no more outputs remain
pub fn drain_sink<O, P: Provider<O>>(provider: &mut P) -> usize {
    let mut counter = 0;
    while let Some(_) = provider.fetch() {
        counter += 1;
    }
    counter
}

/// Drains data from Provider to Listener until no more outputs remain
pub fn drain_to<T, P, L>(provider: &mut P, listener: &mut L) -> usize
where
    P: Provider<T>,
    L: Listener<T>,
{
    drain_to_fn(provider, |t| listener.process(t))
}

const MAX_DRAIN: usize = 64;

pub fn drain_to_fn<T, P, L>(provider: &mut P, mut listener: L) -> usize
where
    P: Provider<T>,
    L: FnMut(&T) -> bool,
{
    let mut counter = 0;
    while let Some(t) = provider.fetch() {
        listener(t);
        counter += 1;
        if counter >= MAX_DRAIN {
            break;
        }
    }
    counter
}
