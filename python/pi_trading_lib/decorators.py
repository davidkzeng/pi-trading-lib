import typing as t


def copy(func):
    def decorated_func(*args, **kwargs):
        result = func(*args, **kwargs)
        return result.copy()
    return decorated_func


S = t.TypeVar('S')
T = t.TypeVar('T')


def memoize_mapping(keys_only=True):
    """Parameterized memoize_mapping decorator

    args:
        keys_only: decorator only returns keys requested
    """

    def memoize_mapping_decorator(func: t.Callable[[t.List[S]], t.Dict[S, T]]):
        _map: t.Dict[S, T] = {}

        def decorated_func(query: t.List[S]) -> t.Dict[S, T]:
            query_set = set(query)
            missing = query_set - set(_map)
            if len(missing) > 0:
                missing_vals = func(list(missing))
                _map.update(missing_vals)
            if keys_only:
                return {k: v for k, v in _map.items() if k in query_set}
            else:
                return _map
        return decorated_func
    return memoize_mapping_decorator


def _hashable(val):
    if isinstance(val, list) or isinstance(val, dict):
        return frozenset(val)
    return val


# TODO: auto-treat config as a special arg, filter out
def memoize(config_prefix: t.Optional[str] = None):
    def memoize_decorator(func):
        _memo_map = {}

        def decorated_func(*args):
            key = frozenset(_hashable(arg) for arg in args)
            if key in _memo_map:
                return _memo_map[key]
            res = func(*args)
            _memo_map[key] = res
            return res

        return decorated_func
    return memoize_decorator


def impure(func):
    """No-op. Tagging important impure functions in the sim path so that we don't try to cache these"""
    return func
