from pi_trading_lib.model_config import core, fte_election, calibration_model

config = {
    **core.config,
    **fte_election.config,
    **calibration_model.config,
    'calibration-model-enabled': True,
    'election-model-enabled': True,
    'return-weight-calibration-model': 2.0,
    'return-weight-election-model': 3.0,
    'sim-begin-date': '20201028',
    'sim-end-date': '20210401',
}
