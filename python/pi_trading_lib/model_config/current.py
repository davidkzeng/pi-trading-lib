from pi_trading_lib.model_config import core, fte_election

config = {
    **core.config,
    **fte_election.config,
    'weight_fte_election': 1.0,
}
