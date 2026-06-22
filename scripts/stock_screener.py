import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
os.makedirs(DOCS, exist_ok=True)

# 筛选条件
MIN_PRICE    = 3.0    # 最低股价（元）
MAX_PRICE    = 20.0   # 最高股价（1.1万能买500股以上）
MIN_VOL_DAYS = 3      # 近N日波动率计算窗口
VOLATILITY_MIN = 2.0  # 近20日日均波幅最低（%，太低没空间做T）
VOLATILITY_MAX = 8.0  # 近20日日均波幅最高（%，太高风险大）
TOP_N = 15            # 最终推荐数量

def screen():
    print('正在拉取全市场行情数据...')
    try:
        spot = ak.stock_zh_a_spot()  # 新浪接口，东方财富接口在 GitHub Actions 上常连接失败
    except Exception as e:
        print(f'行情数据拉取失败: {e}')
        return []

    spot = spot.rename(columns={
        '代码': 'symbol_raw', '名称': 'name', '最新价': 'price', '成交额': 'amount',
    })

    # 仅保留沪深主板（排除北交所 bj 开头）
    df = spot[spot['symbol_raw'].str.startswith(('sh', 'sz'), na=False)].copy()
    df['code']   = df['symbol_raw'].str[2:]
    df['price']  = pd.to_numeric(df['price'],  errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    # 基础过滤（新浪接口无换手率字段，改用成交额衡量流动性）
    df = df[
        df['price'].notna() & (df['price'] > 0) &
        (df['price'] >= MIN_PRICE) &
        (df['price'] <= MAX_PRICE) &
        (~df['name'].str.contains('ST|退', na=False)) &
        (df['amount'] >= 5e7)   # 成交额5000万以上
    ].copy()

    print(f'基础过滤后剩余: {len(df)} 只，开始计算波动率...')

    results = []
    end_date   = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=40)).strftime('%Y%m%d')

    for i, row in df.iterrows():
        code   = row['code']
        name   = row['name']
        price  = row['price']
        amount = row['amount']
        symbol = row['symbol_raw']

        try:
            hist = ak.stock_zh_a_daily(symbol=symbol, start_date=start_date,
                                        end_date=end_date, adjust='qfq')
            if len(hist) < 15:
                continue

            hist['close'] = hist['close'].astype(float)
            hist['high']  = hist['high'].astype(float)
            hist['low']   = hist['low'].astype(float)
            hist['vol']   = hist['volume'].astype(float)

            # 日均波幅 = (high-low)/close 的均值
            hist['range_pct'] = (hist['high'] - hist['low']) / hist['close'] * 100
            avg_range = hist['range_pct'].tail(20).mean()

            if avg_range < VOLATILITY_MIN or avg_range > VOLATILITY_MAX:
                continue

            # 均线趋势：MA5 > MA10（短期向上）
            ma5  = hist['close'].rolling(5).mean().iloc[-1]
            ma10 = hist['close'].rolling(10).mean().iloc[-1]
            ma20 = hist['close'].rolling(20).mean().iloc[-1]

            # 量能稳定：近5日均量 / 近20日均量
            vol5  = hist['vol'].tail(5).mean()
            vol20 = hist['vol'].tail(20).mean()
            vol_ratio = vol5 / vol20 if vol20 > 0 else 0

            # 评分：波幅适中 + 量能稳定 + 价格站上MA5
            score = 0
            if ma5 > ma10:        score += 30
            if price > ma5:       score += 20
            if 3 < avg_range < 6: score += 30  # 波幅最佳区间
            if 0.8 < vol_ratio < 2.0: score += 20

            results.append({
                'code': code, 'name': name, 'price': price,
                'amount_wan': round(amount / 1e4), 'avg_range': round(avg_range, 2),
                'ma5': round(ma5, 2), 'ma10': round(ma10, 2), 'ma20': round(ma20, 2),
                'vol_ratio': round(vol_ratio, 2), 'score': score,
                'trend': '↑' if ma5 > ma10 else ('↓' if ma5 < ma10 else '→'),
            })
            time.sleep(0.3)

        except Exception:
            continue

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:TOP_N]

def build_html(results):
    now = datetime.now()

    if not results:
        rows = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#64748b">暂无符合条件的股票</td></tr>'
    else:
        rows = ''
        for r in results:
            trend_color = '#ef4444' if r['trend'] == '↑' else ('#22c55e' if r['trend'] == '↓' else '#94a3b8')
            score_color = '#22c55e' if r['score'] >= 70 else ('#f59e0b' if r['score'] >= 50 else '#94a3b8')
            rows += f"""<tr>
              <td><span class="sname">{r['name']}</span><br><span class="scode">{r['code']}</span></td>
              <td style="font-weight:700">{r['price']}</td>
              <td style="color:{trend_color}">{r['trend']} {r['ma5']}</td>
              <td>{r['amount_wan']}万</td>
              <td>{r['avg_range']}%</td>
              <td>{r['vol_ratio']}x</td>
              <td style="color:{score_color};font-weight:700">{r['score']}</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>选股推荐 {now.strftime('%m-%d')}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--color-background-tertiary,#f5f5f3);color:var(--color-text-primary);font-family:-apple-system,sans-serif;padding:16px;max-width:540px;margin:0 auto}}
  h1{{font-size:18px;font-weight:500;color:var(--color-text-primary);margin-bottom:4px}}
  .subtitle{{font-size:12px;color:var(--color-text-tertiary);margin-bottom:16px}}
  .card{{background:var(--color-background-primary);border:0.5px solid var(--color-border-tertiary);border-radius:12px;padding:16px;margin-bottom:12px;overflow-x:auto}}
  table{{width:100%;border-collapse:collapse;font-size:12px;min-width:420px;table-layout:fixed}}
  th{{color:var(--color-text-tertiary);font-weight:500;padding:6px 4px;border-bottom:0.5px solid var(--color-border-tertiary);text-align:left}}
  td{{padding:8px 4px;border-bottom:0.5px solid var(--color-border-tertiary);vertical-align:middle;color:var(--color-text-secondary)}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:var(--color-background-secondary)}}
  .sname{{font-size:13px;font-weight:500;color:var(--color-text-primary)}}
  .scode{{font-size:10px;color:var(--color-text-tertiary)}}
  .criteria{{background:var(--color-background-primary);border:0.5px solid var(--color-border-tertiary);border-radius:12px;padding:16px;margin-bottom:12px}}
  .criteria-title{{font-size:13px;font-weight:500;color:var(--color-text-primary);margin-bottom:8px}}
  .crit-item{{font-size:12px;color:var(--color-text-secondary);margin-bottom:5px;padding-left:10px;line-height:1.6}}
  .back-btn{{display:block;width:100%;padding:12px;background:var(--color-background-secondary);color:var(--color-text-secondary);border:0.5px solid var(--color-border-secondary);border-radius:10px;font-size:14px;font-weight:500;cursor:pointer;margin-bottom:12px;text-align:center;text-decoration:none}}
  .footer{{text-align:center;font-size:11px;color:var(--color-text-tertiary);padding-bottom:20px}}
</style>
</head>
<body>

<h1>🔍 选股推荐</h1>
<div class="subtitle">生成时间：{now.strftime('%Y-%m-%d %H:%M')} · 共筛出 {len(results)} 只</div>

<div class="criteria">
  <div class="criteria-title">筛选标准</div>
  <div class="crit-item">▸ 股价 {MIN_PRICE}–{MAX_PRICE} 元（1.1万可买足量）</div>
  <div class="crit-item">▸ 成交额 ≥ 5000万（避免小票，流动性充足）</div>
  <div class="crit-item">▸ 近20日日均波幅 {VOLATILITY_MIN}%–{VOLATILITY_MAX}%（做T空间合适）</div>
  <div class="crit-item">▸ 非ST / 非退市股</div>
</div>

<div class="card">
  <table>
    <thead>
      <tr>
        <th>股票</th><th>现价</th><th>趋势/MA5</th><th>成交额</th><th>日均波幅</th><th>量比</th><th>评分</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>

<div class="criteria">
  <div class="criteria-title">评分说明</div>
  <div class="crit-item">▸ MA5 &gt; MA10（短期上升趋势）：+30分</div>
  <div class="crit-item">▸ 现价 &gt; MA5（站上短期均线）：+20分</div>
  <div class="crit-item">▸ 日均波幅在3%–6%（最佳做T区间）：+30分</div>
  <div class="crit-item">▸ 量比在0.8x–2.0x（量能稳定）：+20分</div>
  <div class="crit-item" style="color:#f59e0b">▸ 评分≥70为优先关注，仅供参考</div>
</div>

<a class="back-btn" href="report.html">← 返回持仓信号</a>

<div class="footer">仅供参考，不构成投资建议 · 据此操作风险自负</div>
</body>
</html>"""

    out = os.path.join(DOCS, 'screener.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'选股报告已生成: {out}')
    print(f'选股报告已生成: {out}')

if __name__ == '__main__':
    print('开始选股筛选，预计需要5–10分钟（逐只拉取历史数据）...')
    results = screen()
    print(f'\n筛选完成，共 {len(results)} 只股票入选')
    build_html(results)
