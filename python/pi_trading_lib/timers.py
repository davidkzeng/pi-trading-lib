import time
import typing as t


_owned_time_stack: t.List[float] = []
_last_event: float = time.time()


class FunctionTimer:
    """Not thread-safe function timer"""

    def __init__(self):
        self.sum_ = 0.0
        self.owned_sum = 0.0
        self.count = 0
        self.owned_time_stack: t.List[float] = []
        self.last_event: float = time.time()

    def start(self):
        global _last_event

        start_time = time.time()
        if len(_owned_time_stack):
            _owned_time_stack[-1] += start_time - _last_event
        if len(self.owned_time_stack):
            self.owned_time_stack[-1] += start_time - self.last_event

        _owned_time_stack.append(0.0)
        self.owned_time_stack.append(0.0)
        _last_event = start_time
        self.last_event = start_time

    def stop(self):
        global _last_event
        assert len(self.owned_time_stack) > 0
        assert len(_owned_time_stack) > 0

        end_time = time.time()
        _owned_time_stack[-1] += end_time - _last_event
        self.owned_time_stack[-1] += end_time - self.last_event

        overall_owned_time = _owned_time_stack.pop()
        func_owned_time = self.owned_time_stack.pop()

        self.sample(func_owned_time, overall_owned_time)

        _last_event = end_time
        self.last_event = end_time

    def sample(self, val, owned_val):
        self.sum_ += val
        self.owned_sum += owned_val
        self.count += 1

    def report(self):
        if self.count == 0:
            return None
        return (format(self.sum_, '.6f'), format(self.sum_ / self.count, '.6f'),
                format(self.owned_sum, '.6f'), self.count)

    def reset(self):
        self.sum_ = 0.0
        self.owned_sum = 0.0
        self.count = 0


_function_timers: t.Dict[str, FunctionTimer] = {}


def timer(func):
    name = func.__module__.split('.', 1)[-1] + '.' + func.__name__
    if name not in _function_timers:
        _function_timers[name] = FunctionTimer()
    func_timer = _function_timers[name]

    def decorated_func(*args, **kwargs):
        func_timer.start()
        return_val = func(*args, **kwargs)
        func_timer.stop()
        return return_val
    decorated_func.__name__ = func.__name__
    return decorated_func


def report_timers():
    def print_format(name, sum_, avg, owned_sum, count):
        print(f'{name:50.50} {sum_:10} {avg:10} {owned_sum:10} {count:<6}')
    print('\nTIMERS')
    print_format('func_name', 'sum', 'avg', 'owned_sum', 'count')
    print()
    for func_name, timer in _function_timers.items():
        timer_report = timer.report()
        if timer_report is not None:
            print_format(func_name, *timer_report)


def reset_timers():
    for timer in _function_timers.values():
        timer.reset()
