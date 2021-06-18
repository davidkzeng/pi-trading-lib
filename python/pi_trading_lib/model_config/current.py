from pi_trading_lib.model_config import core, fte_election, calibration_model

config = {
    **core.config,
    **fte_election.config,
    **calibration_model.config,
    'weight_fte_election': 1.0,
    'begin_date': '20201001',
    'end_date': '20201030',
}
