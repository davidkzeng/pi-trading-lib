import logging


_LOGGING_SET = False

FORMAT = '[%(asctime)s] [%(levelname)s] (%(filename)s:%(lineno)s) %(message)s'


def init_logging(level=logging.INFO):
    global _LOGGING_SET

    if not _LOGGING_SET:
        logging.basicConfig(level=level, format=FORMAT)
    else:
        logging.warn('Setting logging level again...')
        logging.basicConfig(level=level, format=FORMAT)

    _LOGGING_SET = True
