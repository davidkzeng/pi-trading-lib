import typing as t

from pi_trading_lib.model_config import current

config: t.Dict[str, t.Any] = {
    **current.config,
    'sim-end-date': '20201201',
}
