import typing as t

from pi_trading_lib.model import OptimizeResult


def sharpe(result: OptimizeResult) -> float:
    PI_RISK_FREE_RATE = 0.02
    _, model_return = result
    exp_return, std_return = model_return

    return (exp_return - PI_RISK_FREE_RATE) / std_return


def one_stdev_return(result: OptimizeResult) -> float:
    _, model_return = result
    exp_return, std_return = model_return

    return exp_return - 1 * std_return


def meta_optimize(optimize_fn: t.Callable[[t.Dict[str, t.Any]], OptimizeResult],
                  param_search: t.List[t.Dict[str, t.Any]] = [{}],
                  score_func: t.Callable[[OptimizeResult], float] = one_stdev_return) -> OptimizeResult:
    best_result: t.Optional[OptimizeResult] = None
    best_score = None

    for param_option in param_search:
        result = optimize_fn(param_option)
        score = score_func(result)

        if best_score is None or score > best_score:
            best_result = result
            best_score = score

    assert best_result is not None
    return best_result
