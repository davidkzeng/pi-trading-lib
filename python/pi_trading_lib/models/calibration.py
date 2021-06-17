"""
import functools
import datetime

import pandas as pd
import numpy as np

import pi_trading_lib.data.contracts
import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.resolution as resolution
import pi_trading_lib.model_config as model_config
import pi_trading_lib.timers as timers
from pi_trading_lib.data.resolution_data import NO_CORRECT_CONTRACT_MARKETS
from pi_trading_lib.model import ReturnModel


def sample_date(date: datetime.date, config: model_config.Config):
    global bucket_counts, bucket_yes, bucket_sum

    snapshot = market_data.get_snapshot(date).data
    contracts = snapshot.index.get_level_values(0).tolist()
    binary_contract_map = pi_trading_lib.data.contracts.is_binary_contract(contracts)
    binary_contracts = [cid for cid, val in binary_contract_map.items() if val]
    resolutions = resolution.get_contract_resolution(contracts)
    resolutions = pd.Series(resolutions, name='resolution')
    resampled = resampled.join(resolutions)
    resampled = resampled.dropna()
    resampled = resampled[~resampled.index.get_level_values(0).isin(binary_contracts)]
    for idx, row in resampled.iterrows():
        samples.append((idx, row['market_id'], row['trade_price'], row['resolution']))
    resampled['bucket'] = (resampled['trade_price'] * buckets).astype(int)
    date_counts = resampled.groupby('bucket').count()['resolution'] #???
    yes_counts = resampled[resampled['resolution'] >= 1].groupby('bucket').count()['resolution'] #???
    bucket_counts = bucket_counts + date_counts.reindex(bucket_counts.index).fillna(0.0)
    bucket_yes = bucket_yes + yes_counts.reindex(bucket_counts.index).fillna(0).astype(int)
    bucket_sum = bucket_sum + resampled.groupby('bucket')['trade_price'].sum().reindex(bucket_counts.index).fillna(0.0)
    unique_ids = resampled.reset_index().groupby('bucket')['contract_id'].agg(['unique'])['unique'].tolist()
    for idx, bu in enumerate(unique_ids):
        bucket_ids[idx] = bucket_ids[idx] | set(bu.tolist())

    pass


def sample(begin_date: datetime.date, end_date: datetime.date, config: model_config.Config):
    for date in date_util.date_range(begin_date, end_date):
        sample_date(date, config)


def generate_parameters(date: datetime.date, config: model_config.Config) -> str:
    alpha = 25.0
    sample_df_copy = sample_df
    sample_df_copy['weight'] = np.round(np.exp(-1.0 * alpha * (sample_df['trade_price'] - px).abs()), decimals=3)
    sample_df_copy['weighted_res'] = sample_df_copy['weight'] * sample_df_copy['resolution']
    sample_df_copy['weighted_trade'] = sample_df_copy['weight'] * sample_df_copy['trade_price']
    result = sample_df_copy['weighted_res'].sum() / sample_df_copy['weight'].sum()
    result_trade = np.round(sample_df_copy['weighted_trade'].sum() / sample_df_copy['weight'].sum(), decimals=2)
    return result, result_trade

def compute(px, sample_df):

def run():
    market_id = np.random.choice(sample_df_a['market_id'].unique(), size=len(sample_df_a['market_id'].unique() // 2))
    sample_df_copy = sample_df_a.set_index('market_id').loc[market_id].reset_index()
    resampled = sample_df_copy.groupby('market_id').sample(n=600, replace=True)
    print(resampled.shape)
    for px in range(1, 100, 1):
        real_px = px / 100
        a, b = compute(real_px, resampled)
        res.append(a)
        idxs.append(b)


class CalibrationModel(Model):
    pass
"""
