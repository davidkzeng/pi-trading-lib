import time
import typing as t


class FunctionTimer:
    """Not thread-safe function timer"""
    def __init__(self):
        self.sum = 0.0
        self.count = 0
        self.start_time_stack: t.List[float] = []

    def start(self):
        self.start_time_stack.append(time.time())

    def stop(self):
        assert len(self.start_time_stack) > 0
        self.sample(time.time() - self.start_time_stack.pop())

    def sample(self, val):
        self.sum += val
        self.count += 1

    def report(self):
        if self.count == 0:
            return None
        return format(self.sum, '.6f'), format(self.sum / self.count, '.6f'), self.count

    def reset(self):
        self.sum = 0.0
        self.count = 0


_function_timers: t.Dict[str, FunctionTimer] = {}


def timer(func):
    if func.__name__ not in _function_timers:
        _function_timers[func.__name__] = FunctionTimer()
    func_timer = _function_timers[func.__name__]

    def decorated_func(*args, **kwargs):
        func_timer.start()
        return_val = func(*args, **kwargs)
        func_timer.stop()
        return return_val
    decorated_func.__name__ = func.__name__
    return decorated_func


def report_timers():
    def print_format(name, sum_, avg, count):
        print(f'{name:50.50} {sum_:10} {avg:10} {count:<6}')
    print('\nTIMERS')
    print_format('func_name', 'sum', 'avg', 'count')
    print()
    for func_name, timer in _function_timers.items():
        timer_report = timer.report()
        if timer_report is not None:
            sum_, avg, count = timer_report
            print_format(func_name, sum_, avg, count)


def reset_timers():
    for timer in _function_timers.values():
        timer.reset()
