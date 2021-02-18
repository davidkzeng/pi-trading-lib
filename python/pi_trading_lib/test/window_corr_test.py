import unittest

import pandas as pd

from pi_trading_lib.constants import NANOS_IN_MIN

from pi_trading_lib.learning.window_corr import sample_md


class WindowCorrTest(unittest.TestCase):
    def setUp(self):
        cid = 1
        self.universe = [cid]
        mid_values = [0.5, 0.5, 0.6, 0.6, 0.5]
        self.sample_data = pd.DataFrame(
            [[(idx + 1) * NANOS_IN_MIN, cid, mid_price] for idx, mid_price in enumerate(mid_values)],
            columns=['timestamp', 'contract_id', 'mid_price'],
        )
        self.sample_data['timestamp'] = self.sample_data['timestamp'].astype('datetime64[ns]')
        self.sample_data = self.sample_data.set_index(['timestamp', 'contract_id'])

    def test_sample(self):
        corr_sample = sample_md(self.sample_data, 2, 1, self.universe, ema_alpha=0)
        self.assertEqual(2, len(corr_sample))
        self.assertAlmostEqual(0, corr_sample[0][0])
        self.assertAlmostEqual(0, corr_sample[0][1])
        self.assertAlmostEqual(0.1, corr_sample[1][0])
        self.assertAlmostEqual(-0.1, corr_sample[1][1])

    def test_ema_sample(self):
        corr_sample = sample_md(self.sample_data, 2, 1, self.universe, ema_alpha=0.75)
        self.assertEqual(2, len(corr_sample))
        self.assertAlmostEqual(0, corr_sample[0][0])
        self.assertAlmostEqual(0, corr_sample[0][1])
        self.assertAlmostEqual(0.04375, corr_sample[1][0])
        self.assertAlmostEqual(-0.1, corr_sample[1][1])
