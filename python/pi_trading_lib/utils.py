import os.path


def parent_dir(path, levels=1):
    cur_path = path
    for _ in range(levels):
        cur_path = os.path.dirname(cur_path)
    return cur_path


def get_package_dir():
    """Return directory of python package"""
    return parent_dir(os.path.realpath(__file__), 1)


def get_rust_bin_dir():
    return os.path.join(get_package_dir(), 'rust_bin')


def copy(func):
    def decorated_func(*args, **kwargs):
        result = func(*args, **kwargs)
        return result.copy()
    return decorated_func
