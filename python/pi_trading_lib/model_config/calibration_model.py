import typing as t

config: t.Dict = {
    'calibration-model-fit-begin-date': '20200817',
    'calibration-model-fit-active-date': '20210101',
    'calibration-model-fit-window-size': 0.10,
    'calibration-model-fit-sample-weight-alpha': 1.0,
    'calibration-model-fit-market-normalize': 'local', # 'local', 'global', or None
    'calibration-model-fit-symmetric-binary': True,
    'calibration-model-fit-market-resample-seed': None, # used for research purposes
    'calibration-model-fit-sample-method': 'sod', # 'sod' or 'change'
    'calibration-model-fit-sample-no-correct': False,

    'calibration-model-enable-binary': True,
    'calibration-model-enable-non-binary': True,
    'calibration-model-enabled': False,
}
