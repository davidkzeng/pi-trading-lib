import typing as t

from pi_trading_lib.model_config import Config
from pi_trading_lib.score import SimResult
import pi_trading_lib.model_config


def grid_search(config: Config, overrides: t.List[t.Dict], sim_fn: t.Callable[[Config], SimResult]):
    search: t.List[t.Dict] = [{}] + overrides

    best_val = None
    best_override = None

    results = []

    for override in search:
        new_config = config.override(override)
        if new_config == config and override != {}:
            continue

        sim_result = sim_fn(new_config)

        if best_val is None or best_val < sim_result.score:
            best_val = sim_result.score
            best_override = new_config

        results.append((new_config, sim_result))

    results = sorted(results, key=lambda res: res[1], reverse=True)
    print('RESULTS')
    for result in results:
        override_config, sim_result = result
        diff = config.diff(override_config)
        print(f'[{sim_result.score:.2f}]      ({diff})')
        print(sim_result.book_summary)

    assert best_override is not None
    print()
    print('Best score: ', best_val)
    print('Best override: ', config.diff(best_override))


def parse_search(search_str: str) -> t.List[t.Dict]:
    tokens = search_str.split('=', 1)
    param = tokens[0]
    val_tokens = tokens[1].split(',')
    vals = [pi_trading_lib.model_config.guess_param_type(val, param) for val in val_tokens]

    search = []
    for val in vals:
        search.append({param: val})
    return search
