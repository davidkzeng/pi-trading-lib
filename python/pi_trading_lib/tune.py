import typing as t

import pandas as pd

from pi_trading_lib.model_config import Config


def grid_search(config: Config, overrides: t.List[t.Dict], sim_fn: t.Callable[[Config], t.Tuple[float, pd.Series]]):
    search: t.List[t.Dict] = [{}] + overrides

    best_val = None
    best_override = None

    results = []

    for override in search:
        new_config = config.override(override)
        if new_config == config and override != {}:
            continue

        res, summary = sim_fn(new_config)

        if best_val is None or best_val < res:
            best_val = res
            best_override = new_config

        results.append((new_config, res, summary))

    results = sorted(results, key=lambda res: res[1], reverse=True)
    for result in results:
        override_config, res, summary = result
        diff = config.diff(override_config)
        print(f'{res:.2f}:      ({diff})')
        print(summary.to_frame().T)

    assert best_override is not None
    print(best_val)
    print(config.diff(best_override))


def guess_type(val: str) -> t.Union[str, float]:
    try:
        return float(val)
    except ValueError:
        pass

    return val


def parse_search(search_str: str) -> t.List[t.Dict]:
    tokens = search_str.split('=', 1)
    param = tokens[0]
    val_tokens = tokens[1].split(',')
    vals = [guess_type(val) for val in val_tokens]

    search = []
    for val in vals:
        search.append({param: val})
    return search
