def copy(func):
    def decorated_func(*args, **kwargs):
        result = func(*args, **kwargs)
        return result.copy()
    return decorated_func
