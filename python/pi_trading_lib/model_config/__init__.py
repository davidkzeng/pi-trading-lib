import importlib
import typing as t


class Config:
    def __init__(self, params: t.Dict[str, t.Any]):
        self.params = params

    def __getitem__(self, key):
        return self.params[key]

    def __eq__(self, other: t.Any):
        if isinstance(other, Config):
            return self.params == other.params
        return False

    def __hash__(self):
        return hash(frozenset(self.params))

    def override(self, override_vals: t.Dict[str, t.Any]) -> 'Config':
        assert set(override_vals).issubset(set(self.params))
        new_params = {
            **self.params,
            **override_vals,
        }
        return Config(new_params)

    def diff(self, other: 'Config') -> t.Dict[str, t.Tuple[t.Any, t.Any]]:
        assert set(self.params) == set(other.params)
        return {
            k: (self.params[k], other.params[k])
            for k in self.params if self.params[k] != other.params[k]
        }


def get_config(name) -> Config:
    config_module = importlib.import_module('pi_trading_lib.model_config.' + name)
    assert hasattr(config_module, 'config')
    return Config(config_module.config)  # type: ignore
