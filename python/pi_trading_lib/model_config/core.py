# Core configs shared across models

config = {
    'sim-version': 1, # use for forcing sim after code updates

    'capital': 10000.0,
    'use-final-res': False,

    'optimizer-position-size-mult': 10,

    'optimizer-std-penalty': 0.01 * 0.005, # increase required edge with position size, addition 0.01 edge per 200 shares
    'optimizer-take-edge': 0.015,

    # risk limits
    'optimizer-max-add-order-size': 200,
}
