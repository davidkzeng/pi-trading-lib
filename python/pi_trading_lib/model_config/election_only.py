import typing as t

from pi_trading_lib.model_config import core, fte_election

config: t.Dict[str, t.Any] = {
    **core.config,
    **fte_election.config,
    'weight-fte-election': 1.0,
    'sim-begin-date': '20201001',
    'sim-end-date': '20201030',
}
