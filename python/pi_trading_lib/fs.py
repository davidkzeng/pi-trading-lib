import os
import os.path
from contextlib import contextmanager


@contextmanager
def safe_open(path, mode, *args, **kwargs):
    if 'w' in mode or 'a' in mode:
        path_dir = os.path.dirname(os.path.realpath(path))
        if not os.path.exists(path_dir):
            os.makedirs(path_dir)
    # TODO: Make atomic
    with open(path, mode, *args, **kwargs) as f:
        yield f
