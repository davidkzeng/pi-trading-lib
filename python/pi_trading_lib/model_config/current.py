from pi_trading_lib.model_config import core, fte_election, calibration_model

config = {
    **core.config,
    **fte_election.config,
    **calibration_model.config,
    'calibration-model-enabled': True,
    'sim-begin-date': '20201001',
    'sim-end-date': '20210401',
}
