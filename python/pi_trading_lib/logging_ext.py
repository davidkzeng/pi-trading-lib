import logging


_LOGGING_SET = False


def _init_logging(level):
    FORMAT = '[%(asctime)s] [%(levelname)-8s] %(message)s (%(filename)s:%(lineno)s) '
    logging.basicConfig(level=level, format=FORMAT)


def init_logging(level=logging.INFO):
    global _LOGGING_SET

    if not _LOGGING_SET:
        _init_logging(level)
    else:
        logging.warn('Setting logging level again... ignoring')

    _LOGGING_SET = True


_init_logging(logging.INFO)
