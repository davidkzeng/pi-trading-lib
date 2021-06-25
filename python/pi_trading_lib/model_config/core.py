# Core configs shared across models

config = {
    'sim-version': 1, # use for forcing sim after code updates

    'capital': 10000.0,
    'use-final-res': False,

    'optimizer-position-size-mult': 10,
    'optimizer-std-penalty': 0.01 * 0.01, # increase required edge with position size
    'optimizer-take-edge': 0.02,
    'optimizer-max-add-order-size': 200,
}
