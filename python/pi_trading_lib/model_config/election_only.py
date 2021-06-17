import typing as t

from pi_trading_lib.model_config import core, fte_election

config: t.Dict[str, t.Any] = {
    **core.config,
    **fte_election.config,
    'weight_fte_election': 1.0,
    'begin_date': '20201001',
    'end_date': '20201030',
}
