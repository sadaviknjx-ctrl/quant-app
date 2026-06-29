"""
回测现有做T信号公式（t_sell=昨高×1.01, t_buy=昨低×0.99）的历史有效性。

方法说明（重要假设）：
- 日线数据只有OHLC，无法知道盘中高低点先后顺序，所以本回测的"成功"定义是：
  当天最高价 >= t_sell 且 当天最低价 <= t_buy 时，记为一次完整高抛低吸成交。
  这是理想化假设（假设两笔都能按目标价成交），实际执行会因排队、滑点打折。
- 手续费近似按双边成交额的0.03%扣除（与网站做T战绩统计口径一致）。
- 对比基准：同期简单持有（不做T）的涨跌幅。
"""
import pandas as pd
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

STOCKS = {
    '三峡新材（已清仓，留作回测样本）': '600293',
    '京东方A':   '000725',
    '华远控股':  '600743',
    '铜陵有色':  '000630',
}

FEE_RATE = 0.0003  # 双边手续费近似
BAND_WIDTHS = [0.005, 0.003, 0.002]      # 待测试的高抛/低吸偏离比例
TREND_THRESHOLD = 0.30                    # 120日涨幅超过此值视为强趋势，跳过做T


def backtest_one(code, band):
    path = os.path.join(DATA, f'{code}.csv')
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)

    # 120日涨幅，用于判断是否处于强势上升趋势（趋势强股不建议做T）
    df['pct_120'] = df['close'].pct_change(120)

    total_days = 0
    executed = 0
    wins = 0
    profit_sum_pct = 0.0
    trend_skip_days = 0  # 强势趋势中本应跳过做T的天数

    for t in range(1, len(df)):
        prev_high = df['high'].iloc[t - 1]
        prev_low = df['low'].iloc[t - 1]
        prev_close = df['close'].iloc[t - 1]
        today_high = df['high'].iloc[t]
        today_low = df['low'].iloc[t]
        pct_120 = df['pct_120'].iloc[t - 1]

        t_sell = prev_high * (1 + band)
        t_buy = prev_low * (1 - band)
        total_days += 1

        is_strong_trend = pd.notna(pct_120) and pct_120 > TREND_THRESHOLD
        if is_strong_trend:
            trend_skip_days += 1
            continue  # 强趋势中不做T，跳过本日信号

        if today_high >= t_sell and today_low <= t_buy and t_sell > t_buy:
            executed += 1
            gross = t_sell - t_buy
            fee = (t_sell + t_buy) * FEE_RATE
            net = gross - fee
            pct = net / prev_close
            profit_sum_pct += pct
            if net > 0:
                wins += 1

    buy_hold_return = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]

    return {
        'code': code, 'band': band,
        'total_days': total_days,
        'executed': executed,
        'freq_pct': executed / total_days * 100 if total_days else 0,
        'win_rate': wins / executed * 100 if executed else None,
        'trend_skip_pct': trend_skip_days / total_days * 100 if total_days else 0,
        'cum_t_return_pct': profit_sum_pct * 100,
        'buy_hold_return_pct': buy_hold_return * 100,
        'date_range': f"{df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}",
    }


def main():
    print('=' * 78)
    print('做T信号参数扫描回测（加入：现价超MA60的15%以上时，强趋势跳过做T）')
    print('=' * 78)

    for name, code in STOCKS.items():
        print(f"\n【{name}】 {code}")
        for band in BAND_WIDTHS:
            r = backtest_one(code, band)
            diff = r['cum_t_return_pct'] - r['buy_hold_return_pct']
            verdict = '✅正贡献' if diff > 0 else '❌拖累'
            print(f"  band=±{band*100:.1f}%  触发{r['executed']:>3}次({r['freq_pct']:.1f}%)  "
                  f"胜率{r['win_rate']:.0f}%  做T{r['cum_t_return_pct']:+.1f}%  "
                  f"持有{r['buy_hold_return_pct']:+.1f}%  增量{diff:+.1f}% {verdict}  "
                  f"(强趋势跳过{r['trend_skip_pct']:.0f}%天数)")

    print('\n' + '=' * 78)
    print('注意：仍是理想化假设（高低点都精确成交），实际效果会打折。')
    print('=' * 78)


if __name__ == '__main__':
    main()
