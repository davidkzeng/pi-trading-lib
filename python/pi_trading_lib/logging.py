import logging


def init_logging(level=logging.INFO):
    FORMAT = '[%(asctime)s] [%(levelname)-8s] %(message)s (%(filename)s:%(lineno)s) '
    logging.basicConfig(level=level, format=FORMAT)
