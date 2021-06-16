import typing as t

from pi_trading_lib.model_config import core, fte_election

config: t.Dict[str, t.Any] = {
    **core.config,
    **fte_election.config,
    'begin_date': '20201001',
    'end_date': '20201030',
}
