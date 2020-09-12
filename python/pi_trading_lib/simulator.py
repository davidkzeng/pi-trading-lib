from pi_trading_lib.model import BaseModel, OptimizeResult


def daily_sim(model: BaseModel, start_date: str, end_date: str) -> OptimizeResult:
    # Keep track of daily positions, solve for min capital and adjust positions.
    pass
