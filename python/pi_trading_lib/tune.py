import typing as t

from pi_trading_lib.model_config import Config
from pi_trading_lib.score import SimResult
import pi_trading_lib.model_config


def grid_search(config: Config, search: t.List[t.Dict], override: str, sim_fn: t.Callable[[Config], SimResult]) -> t.Tuple[Config, SimResult]:
    search: t.List[t.Dict] = [{}] + search

    base_config = config
    config = pi_trading_lib.model_config.override_config(config, override)

    best_result = None
    best_override = None

    results = []

    for override in search:
        new_config = config.override(override)
        if new_config == config and override != {}:
            continue

        sim_result = sim_fn(new_config)

        if best_result is None or best_result.score < sim_result.score:
            best_result = sim_result
            best_override = new_config

        results.append((new_config, sim_result))

    results = sorted(results, key=lambda res: res[1].score, reverse=True)
    print('RESULTS')
    for result in results:
        override_config, sim_result = result
        diff = base_config.diff(override_config)
        print(f'[{sim_result.score:.2f}]      ({diff})     {sim_result.path}')
        print(sim_result.book_summary)

    assert best_override is not None and best_result is not None
    print()
    print('Best score: ', best_result.score)
    print('Best override: ', base_config.diff(best_override))
    print('Best path: ', best_result.path)
    return best_override, best_result


def parse_search(search_str: str) -> t.List[t.Dict]:
    tokens = search_str.split('=', 1)
    param = tokens[0]
    val_tokens = tokens[1].split(',')
    vals = [pi_trading_lib.model_config.guess_param_type(val, param) for val in val_tokens]

    search = []
    for val in vals:
        search.append({param: val})
    return search
