import importlib
import typing as t


ParamValue = t.Union[str, float, bool]


class Config:
    def __init__(self, params: t.Dict[str, ParamValue]):
        self.params = params

    def __getitem__(self, key):
        return self.params[key]

    def __eq__(self, other: t.Any):
        if isinstance(other, Config):
            return self.params == other.params
        return False

    def __hash__(self):
        return hash(frozenset(self.params.items()))

    def override(self, override_vals: t.Dict[str, ParamValue]) -> 'Config':
        assert set(override_vals).issubset(set(self.params))
        new_params = {
            **self.params,
            **override_vals,
        }
        return Config(new_params)

    def diff(self, other: 'Config') -> t.Dict[str, t.Tuple[ParamValue, ParamValue]]:
        assert set(self.params) == set(other.params)
        return {
            k: (self.params[k], other.params[k])
            for k in self.params if self.params[k] != other.params[k]
        }

    def component_params(self, component: str) -> 'Config':
        component_params = {
            param: val for param, val in self.params.items() if param.startswith(component)
        }
        return Config(component_params)


def guess_param_type(val: str, param: str) -> ParamValue:
    if 'date' in param:
        return val

    if val in ['true', 'True']:
        return True
    elif val in ['false', 'False']:
        return False

    try:
        return float(val)
    except ValueError:
        pass

    return val


def override_config(config: Config, override_str: str) -> Config:
    overrides = override_str.split(':')
    override_vals: t.Dict[str, ParamValue] = {}
    for override in overrides:
        tokens = override.split('=', 1)
        override_vals[tokens[0]] = guess_param_type(tokens[1], tokens[0])
    return config.override(override_vals)


def get_config(name) -> Config:
    config_module = importlib.import_module('pi_trading_lib.model_config.' + name)
    assert hasattr(config_module, 'config')
    return Config(config_module.config)  # type: ignore
