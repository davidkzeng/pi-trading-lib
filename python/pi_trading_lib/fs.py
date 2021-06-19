import os
import os.path
import tempfile
import shutil
from contextlib import contextmanager


@contextmanager
def safe_open(path, mode, *args, **kwargs):
    if 'w' in mode or 'a' in mode:
        path_dir = os.path.dirname(os.path.realpath(path))
        if not os.path.exists(path_dir):
            os.makedirs(path_dir)
    with open(path, mode, *args, **kwargs) as f:
        yield f


@contextmanager
def atomic_output(path):
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
        shutil.move(tmpdir, path)
