from pi_trading_lib.model_config import core, fte_election, calibration_model

config = {
    **core.config,
    **fte_election.config,
    **calibration_model.config,
    'calibration-model-enabled': True,
    'election-model-enabled': True,
    'sim-begin-date': '20201028',
    'sim-end-date': '20210401',
}
