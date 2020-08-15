import logging

def init_logging():
    FORMAT = '[%(asctime)s] [%(levelname)-8s] %(message)s (%(filename)s:%(lineno)s) '
    logging.basicConfig(level=logging.INFO, format=FORMAT)
