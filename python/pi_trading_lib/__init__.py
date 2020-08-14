import os.path


def parent_dir(path, levels=1):
    cur_path = path
    for _ in range(levels):
        cur_path = os.path.dirname(cur_path)
    return cur_path


def get_package_dir():
    return parent_dir(os.path.realpath(__file__), 3)
