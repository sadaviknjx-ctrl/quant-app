import pandas as pd
import numpy as np
from datetime import datetime
import akshare as ak
import time
import os

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA   = os.path.join(ROOT, 'data')
DOCS   = os.path.join(ROOT, 'docs')
os.makedirs(DOCS, exist_ok=True)

STOCKS = {
    '三峡新材': {'code': '600293', 'symbol': 'sh600293', 'hold': 1600, 'cost': 3.748},
    '京东方A':  {'code': '000725', 'symbol': 'sz000725', 'hold': 300,  'cost': 4.892},
    '华远控股': {'code': '600743', 'symbol': 'sh600743', 'hold': 300,  'cost': -2.722},
    '铜陵有色': {'code': '000630', 'symbol': 'sz000630', 'hold': 100,  'cost': 7.19},
}

def update_data():
    print('更新行情数据...')
    for name, cfg in STOCKS.items():
        for attempt in range(3):
            try:
                df = ak.stock_zh_a_daily(
                    symbol=cfg['symbol'],
                    start_date='20240101',
                    end_date=datetime.now().strftime('%Y%m%d'),
                    adjust='qfq'
                )
                df.to_csv(os.path.join(DATA, f"{cfg['code']}.csv"), index=False)
                print(f"  {name}: {df['close'].iloc[-1]} ({df['date'].iloc[-1]})")
                time.sleep(1)
                break
            except Exception as e:
                print(f"  {name} 第{attempt+1}次失败: {e}")
                time.sleep(3)

def calc_signals(cfg):
    df = pd.read_csv(os.path.join(DATA, f"{cfg['code']}.csv"))
    df['date']  = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    close = df['close'].astype(float)
    high  = df['high'].astype(float)
    low   = df['low'].astype(float)
    vol   = df['volume'].astype(float)

    ma5  = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    std20   = close.rolling(20).std()
    boll_up = (ma20 + 2 * std20).iloc[-1]
    boll_dn = (ma20 - 2 * std20).iloc[-1]

    last_date  = df['date'].iloc[-1].strftime('%m-%d')
    last_close = float(close.iloc[-1])
    prev_high  = float(high.iloc[-1])
    prev_low   = float(low.iloc[-1])
    last_vol   = float(vol.iloc[-1])
    avg_vol10  = float(vol.tail(10).mean())
    avg_vol20  = float(vol.tail(20).mean())
    avg_vol5   = float(vol.tail(5).mean())
    vol_ratio  = last_vol / avg_vol10 if avg_vol10 > 0 else 1

    ma5_v  = ma5.iloc[-1]
    ma10_v = ma10.iloc[-1]
    ma20_v = ma20.iloc[-1]

    t_sell   = round(prev_high * 1.01, 2)
    t_buy    = round(prev_low  * 0.99, 2)
    stop     = round(min(last_close * 0.97, t_buy * 0.99), 2)
    t_shares = max(round(cfg['hold'] * 0.2 / 100) * 100, 100)

    cost = cfg['cost']
    if cost <= 0:
        profit_pct   = None
        profit_label = f'+{last_close - cost:.3f}元/股（成本已为负）'
        profit_pos   = True
    else:
        profit_pct   = (last_close - cost) / cost * 100
        profit_label = f'{profit_pct:+.1f}%'
        profit_pos   = profit_pct >= 0

    trend_val = ma5_v - ma10_v
    if last_close > ma5_v > ma10_v:
        trend, trend_cls = '↑ 短期上升', 'up'
    elif last_close < ma5_v < ma10_v:
        trend, trend_cls = '↓ 短期下降', 'down'
    else:
        trend, trend_cls = '→ 横盘震荡', 'flat'

    vol_desc = f'放量 {vol_ratio:.1f}x' if vol_ratio > 1.5 else ('缩量' if vol_ratio < 0.7 else f'正常 {vol_ratio:.1f}x')

    warnings = []
    below_ma20 = int((close.tail(5) < ma20.tail(5)).sum())
    if below_ma20 >= 5:
        warnings.append(('red', '连续5日低于MA20，趋势持续走弱，暂停做T'))
    elif below_ma20 >= 3:
        warnings.append(('orange', f'近5日有{below_ma20}天低于MA20，谨慎操作'))

    if cost > 0 and profit_pct is not None:
        if profit_pct < -10:
            warnings.append(('red', f'浮亏已达{profit_pct:.1f}%，建议考虑止损换股'))
        elif profit_pct < -5:
            warnings.append(('orange', f'浮亏{profit_pct:.1f}%，关注止损线'))

    if avg_vol20 > 0 and avg_vol5 / avg_vol20 < 0.5:
        warnings.append(('orange', '成交量持续萎缩，流动性不足，做T空间有限'))

    if t_sell - t_buy < last_close * 0.02:
        warnings.append(('yellow', '高抛低吸价差不足2%，手续费后盈利空间有限'))

    if last_close < boll_dn:
        advice = ('warning', '超卖区域，优先低吸，暂缓高抛')
    elif last_close > boll_up:
        advice = ('warning', '超买区域，优先高抛，谨慎追涨')
    elif vol_ratio > 1.5 and last_close > ma5_v:
        advice = ('good', '放量上涨，趋势偏强，以高抛为主')
    elif vol_ratio < 0.7:
        advice = ('neutral', '缩量横盘，今日可不操作，等待放量信号')
    else:
        advice = ('neutral', '正常震荡，按挂单价位操作即可')

    return {
        'last_close': last_close, 'last_date': last_date, 'cost': cost,
        'profit_label': profit_label, 'profit_pct': profit_pct, 'profit_pos': profit_pos,
        'trend': trend, 'trend_cls': trend_cls,
        'vol_desc': vol_desc, 'vol_ratio': vol_ratio,
        'ma5': ma5_v, 'ma10': ma10_v, 'ma20': ma20_v,
        'boll_up': boll_up, 'boll_dn': boll_dn,
        't_sell': t_sell, 't_buy': t_buy, 'stop': stop,
        't_shares': t_shares, 'advice': advice,
        'hold': cfg['hold'], 'code': cfg['code'],
        'warnings': warnings,
    }

def stock_card(name, s, today_md):
    profit_cls = 'positive' if s['profit_pos'] else 'negative'
    trend_cls  = s['trend_cls']
    stale      = s['last_date'] != today_md
    date_cls   = 'data-date-stale' if stale else 'data-date-fresh'
    date_label = f"数据 {s['last_date']}" + ('（非最新）' if stale else '（最新）')

    warn_html = ''
    for level, msg in s['warnings']:
        warn_html += f'<div class="warn warn-{level}">{msg}</div>'

    return f"""<div class="card stock-card">
  <div class="card-top">
    <div class="stock-id">
      <span class="stock-name">{name}</span>
      <span class="stock-code">{s['code']}</span>
    </div>
    <div class="price-block">
      <span class="last-price">{s['last_close']:.2f}</span>
      <span class="profit {profit_cls}">{s['profit_label']}</span>
    </div>
  </div>
  <div class="{date_cls}">{date_label}</div>

  {warn_html}

  <div class="meta-row">
    <span class="trend trend-{trend_cls}">{s['trend']}</span>
    <span class="pill">{s['vol_desc']}</span>
    <span class="pill">持仓 {s['hold']}股</span>
  </div>

  <div class="divider"></div>

  <div class="ind-grid">
    <div class="ind"><span class="ind-l">MA5</span><span class="ind-v">{s['ma5']:.2f}</span></div>
    <div class="ind"><span class="ind-l">MA10</span><span class="ind-v">{s['ma10']:.2f}</span></div>
    <div class="ind"><span class="ind-l">MA20</span><span class="ind-v">{s['ma20']:.2f}</span></div>
    <div class="ind"><span class="ind-l">布林上</span><span class="ind-v">{s['boll_up']:.2f}</span></div>
    <div class="ind"><span class="ind-l">布林下</span><span class="ind-v">{s['boll_dn']:.2f}</span></div>
  </div>

  <div class="divider"></div>

  <p class="t-label-row">明日挂单建议 <span class="shares-badge">{s['t_shares']}股</span></p>
  <div class="t-grid">
    <div class="t-cell t-sell">
      <div class="t-cell-label">高抛（卖出）</div>
      <div class="t-cell-price">{s['t_sell']:.2f}</div>
    </div>
    <div class="t-cell t-buy">
      <div class="t-cell-label">低吸（买回）</div>
      <div class="t-cell-price">{s['t_buy']:.2f}</div>
    </div>
    <div class="t-cell t-stop">
      <div class="t-cell-label">止损（减仓）</div>
      <div class="t-cell-price">{s['stop']:.2f}</div>
    </div>
  </div>

  <div class="advice advice-{s['advice'][0]}">{s['advice'][1]}</div>
</div>"""

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#f0f2f5;font-family:-apple-system,'PingFang SC',sans-serif;padding:16px;max-width:500px;margin:0 auto;color:#1a1d23}
h1{font-size:19px;font-weight:600;color:#1a1d23;margin-bottom:2px}
.sub-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;gap:8px}
.sub{font-size:12px;color:#8a8f9b}
.refresh-btn{flex-shrink:0;padding:5px 10px;background:#fff;border:1px solid #e8eaed;border-radius:8px;font-size:11px;color:#5a6072;cursor:pointer;white-space:nowrap}
.refresh-btn:active{background:#f0f2f5}
.refresh-btn:disabled{opacity:.5}

/* ── Cards ── */
.card{background:#fff;border-radius:14px;padding:16px;margin-bottom:14px;border:1px solid #e8eaed}
.section-title{font-size:13px;font-weight:600;color:#5a6072;text-transform:uppercase;letter-spacing:.04em;margin-bottom:12px}

/* ── Stock card top ── */
.card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.stock-name{font-size:16px;font-weight:600;color:#1a1d23}
.stock-code{font-size:11px;color:#b0b5c0;margin-left:5px}
.price-block{text-align:right}
.last-price{display:block;font-size:24px;font-weight:700;color:#1a1d23;letter-spacing:-.5px}
.profit{font-size:12px;font-weight:500}
.profit.positive{color:#00a854}
.profit.negative{color:#f5222d}

/* ── Data date badge ── */
.data-date-fresh{display:inline-block;font-size:11px;color:#00a854;background:#f6ffed;border:1px solid #b7eb8f;border-radius:6px;padding:2px 7px;margin-bottom:10px}
.data-date-stale{display:inline-block;font-size:11px;color:#fa8c16;background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:2px 7px;margin-bottom:10px}

/* ── Warnings ── */
.warn{font-size:12px;padding:7px 10px;border-radius:8px;margin-bottom:8px;font-weight:500}
.warn-red{background:#fff1f0;color:#cf1322;border-left:3px solid #f5222d}
.warn-orange{background:#fff7e6;color:#874d00;border-left:3px solid #fa8c16}
.warn-yellow{background:#feffe6;color:#7c6500;border-left:3px solid #fadb14}

/* ── Meta row ── */
.meta-row{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.trend{font-size:12px;font-weight:600;padding:3px 8px;border-radius:6px}
.trend-up{color:#f5222d;background:#fff1f0}
.trend-down{color:#00a854;background:#f6ffed}
.trend-flat{color:#5a6072;background:#f5f6f8}
.pill{background:#f5f6f8;border:1px solid #e8eaed;border-radius:6px;padding:3px 8px;font-size:11px;color:#6b7280}

/* ── Divider ── */
.divider{height:1px;background:#f0f2f5;margin:12px 0}

/* ── Indicator grid ── */
.ind-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:12px}
.ind{background:#f8f9fb;border-radius:8px;padding:7px 4px;text-align:center}
.ind-l{display:block;font-size:10px;color:#9ca3af;margin-bottom:3px}
.ind-v{font-size:13px;font-weight:600;color:#1a1d23}

/* ── T grid ── */
.t-label-row{font-size:12px;color:#9ca3af;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.shares-badge{background:#e8f4ff;color:#0958d9;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:500}
.t-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px}
.t-cell{border-radius:10px;padding:10px 6px;text-align:center}
.t-sell{background:#fff1f0;border:1px solid #ffa39e}
.t-buy{background:#f6ffed;border:1px solid #b7eb8f}
.t-stop{background:#fffbe6;border:1px solid #ffe58f}
.t-cell-label{font-size:10px;color:#8a8f9b;margin-bottom:5px}
.t-cell-price{font-size:18px;font-weight:700}
.t-sell .t-cell-price{color:#f5222d}
.t-buy .t-cell-price{color:#389e0d}
.t-stop .t-cell-price{color:#d46b08}

/* ── Advice ── */
.advice{font-size:13px;padding:9px 12px;border-radius:8px;border-left:3px solid transparent}
.advice-neutral{background:#f5f6f8;color:#5a6072;border-left-color:#c4c9d4}
.advice-good{background:#f6ffed;color:#389e0d;border-left-color:#52c41a}
.advice-warning{background:#fff7e6;color:#874d00;border-left-color:#fa8c16}

/* ── Flow steps ── */
.step{display:flex;gap:12px;margin-bottom:14px;align-items:flex-start}
.step:last-child{margin-bottom:0}
.step-num{width:24px;height:24px;border-radius:50%;background:#e8f4ff;color:#0958d9;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;flex-shrink:0}
.step-body{}
.step-title{font-size:13px;font-weight:600;color:#1a1d23;margin-bottom:3px}
.step-desc{font-size:12px;color:#8a8f9b;line-height:1.6}
.time-pill{background:#e8f4ff;color:#0958d9;border-radius:4px;padding:1px 6px;font-size:11px;margin-right:4px}

/* ── Checklist ── */
.checklist{list-style:none}
.checklist li{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid #f0f2f5;font-size:13px;color:#5a6072}
.checklist li:last-child{border-bottom:none}
.chk{width:17px;height:17px;border:1.5px solid #d1d5db;border-radius:4px;flex-shrink:0}

/* ── Risk list ── */
.risk-list{display:flex;flex-direction:column;gap:8px}
.risk-item{display:flex;gap:8px;font-size:12px;color:#6b7280;align-items:flex-start;line-height:1.6}
.risk-dot{color:#f5222d;margin-top:2px;flex-shrink:0}

/* ── Trade stats ── */
.stat-summary{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:4px}
.stat-item{background:#f8f9fb;border-radius:10px;padding:10px 6px;text-align:center}
.stat-num{display:block;font-size:20px;font-weight:700;color:#1a1d23;letter-spacing:-.3px}
.stat-label{font-size:11px;color:#9ca3af;margin-top:2px;display:block}
.t-stat-header{display:grid;grid-template-columns:2fr 1fr 1fr 1.5fr;gap:4px;padding:4px 0;font-size:11px;color:#9ca3af;font-weight:500}
.t-stat-row{display:grid;grid-template-columns:2fr 1fr 1fr 1.5fr;gap:4px;padding:7px 0;border-bottom:1px solid #f0f2f5;font-size:12px}
.t-stat-row:last-child{border-bottom:none}
.t-stat-name{color:#1a1d23;font-weight:500}
.t-stat-val{color:#5a6072;text-align:right}
.trade-row{display:flex;gap:8px;align-items:center;padding:7px 0;border-bottom:1px solid #f0f2f5;font-size:12px}
.trade-row:last-child{border-bottom:none}
.trade-date{color:#9ca3af;width:36px;flex-shrink:0}
.trade-stock{color:#1a1d23;font-weight:500;flex:1}
.trade-action{width:36px;font-weight:600;flex-shrink:0}
.trade-sell{color:#f5222d}
.trade-buy{color:#00a854}
.trade-detail{color:#8a8f9b;margin-left:auto}

/* ── Add trade button ── */
.add-trade-btn{width:100%;margin-top:12px;padding:11px;background:#f0f7ff;color:#1677ff;border:1.5px dashed #91caff;border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;letter-spacing:.02em}
.add-trade-btn:active{background:#e6f0ff}

/* ── Modal overlay ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:100;align-items:flex-end;justify-content:center}
.modal-overlay.open{display:flex}
.modal{background:#fff;border-radius:20px 20px 0 0;padding:24px 20px 36px;width:100%;max-width:500px;animation:slideUp .25s ease}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
.modal-title{font-size:16px;font-weight:600;color:#1a1d23;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center}
.modal-close{background:none;border:none;font-size:22px;color:#9ca3af;cursor:pointer;line-height:1}
.form-group{margin-bottom:14px}
.form-label{font-size:12px;color:#8a8f9b;margin-bottom:6px;display:block;font-weight:500}
.seg-group{display:flex;gap:8px}
.seg-btn{flex:1;padding:10px;border:1.5px solid #e8eaed;border-radius:10px;background:#f8f9fb;font-size:13px;font-weight:500;color:#5a6072;cursor:pointer;transition:all .15s}
.seg-btn.active-sell{border-color:#f5222d;background:#fff1f0;color:#f5222d}
.seg-btn.active-buy{border-color:#00a854;background:#f6ffed;color:#00a854}
.seg-btn.active-stock{border-color:#1677ff;background:#e8f4ff;color:#1677ff}
.form-input{width:100%;padding:11px 12px;border:1.5px solid #e8eaed;border-radius:10px;font-size:15px;color:#1a1d23;background:#f8f9fb;outline:none;-webkit-appearance:none}
.form-input:focus{border-color:#1677ff;background:#fff}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.submit-btn{width:100%;padding:14px;background:#1677ff;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:600;cursor:pointer;margin-top:6px}
.submit-btn:disabled{background:#b0c4de;cursor:not-allowed}
.token-hint{font-size:11px;color:#b0b5c0;text-align:center;margin-top:10px;line-height:1.6}
.toast{position:fixed;top:24px;left:50%;transform:translateX(-50%);background:#1a1d23;color:#fff;padding:10px 20px;border-radius:10px;font-size:13px;z-index:200;display:none;white-space:nowrap}

/* ── Screener btn ── */
.screener-btn{display:block;text-align:center;padding:13px;background:#1677ff;color:#fff;border-radius:12px;font-size:14px;font-weight:600;text-decoration:none;margin-bottom:14px;letter-spacing:.02em}

.footer{text-align:center;font-size:11px;color:#b0b5c0;padding-bottom:24px}
"""

TRADES_CSV = os.path.join(DATA, 'trades.csv')

def load_trades():
    if not os.path.exists(TRADES_CSV):
        return pd.DataFrame(columns=['date','stock','action','shares','price','note'])
    df = pd.read_csv(TRADES_CSV)
    df['date'] = pd.to_datetime(df['date'])
    df['shares'] = pd.to_numeric(df['shares'], errors='coerce')
    df['price']  = pd.to_numeric(df['price'],  errors='coerce')
    return df.dropna(subset=['shares','price'])

def calc_trade_stats(trades):
    if trades.empty:
        return None

    # 配对高抛/低吸：按日期+股票匹配，每对算一次T
    stats_by_stock = {}
    for stock, grp in trades.groupby('stock'):
        sells = grp[grp['action'] == '高抛'].sort_values('date').reset_index(drop=True)
        buys  = grp[grp['action'] == '低吸'].sort_values('date').reset_index(drop=True)
        pairs = min(len(sells), len(buys))
        profit = 0.0
        win = 0
        for i in range(pairs):
            sell_p = sells.iloc[i]['price']
            buy_p  = buys.iloc[i]['price']
            sh     = min(sells.iloc[i]['shares'], buys.iloc[i]['shares'])
            p = (sell_p - buy_p) * sh - (sell_p * sh + buy_p * sh) * 0.0003  # 手续费估算
            profit += p
            if p > 0:
                win += 1
        stats_by_stock[stock] = {'pairs': pairs, 'win': win, 'profit': round(profit, 2)}

    total_pairs  = sum(v['pairs']  for v in stats_by_stock.values())
    total_win    = sum(v['win']    for v in stats_by_stock.values())
    total_profit = sum(v['profit'] for v in stats_by_stock.values())
    win_rate = total_win / total_pairs * 100 if total_pairs > 0 else 0

    # 最近7天记录
    recent = trades[trades['date'] >= (pd.Timestamp.now() - pd.Timedelta(days=7))]

    return {
        'by_stock': stats_by_stock,
        'total_pairs': total_pairs,
        'total_win': total_win,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'recent': recent,
        'last_date': trades['date'].max().strftime('%Y-%m-%d'),
    }

def trade_stats_html(stats):
    if stats is None:
        return """<div class="card">
  <p class="section-title">做T战绩</p>
  <div style="text-align:center;padding:20px 0;color:#b0b5c0;font-size:13px;line-height:2">
    暂无交易记录<br>
    <span style="font-size:12px">完成第一笔做T后，点下方按钮录入</span>
  </div>
  <button class="add-trade-btn" onclick="openTradeModal()">＋ 记录一笔交易</button>
</div>"""

    win_color  = '#00a854' if stats['win_rate'] >= 60 else ('#fa8c16' if stats['win_rate'] >= 40 else '#f5222d')
    pnl_color  = '#00a854' if stats['total_profit'] >= 0 else '#f5222d'
    pnl_sign   = '+' if stats['total_profit'] >= 0 else ''

    # 按股票分行
    stock_rows = ''
    for stock, sv in stats['by_stock'].items():
        if sv['pairs'] == 0:
            continue
        wr = sv['win'] / sv['pairs'] * 100
        pc = sv['profit']
        stock_rows += f"""<div class="t-stat-row">
          <span class="t-stat-name">{stock}</span>
          <span class="t-stat-val">{sv['pairs']}次</span>
          <span class="t-stat-val" style="color:{'#00a854' if wr>=60 else '#fa8c16'}">{wr:.0f}%</span>
          <span class="t-stat-val" style="color:{'#00a854' if pc>=0 else '#f5222d'}">{'+' if pc>=0 else ''}{pc:.2f}元</span>
        </div>"""

    # 最近记录
    recent_rows = ''
    for _, row in stats['recent'].sort_values('date', ascending=False).iterrows():
        action_cls = 'sell' if row['action'] == '高抛' else 'buy'
        recent_rows += f"""<div class="trade-row">
          <span class="trade-date">{row['date'].strftime('%m/%d')}</span>
          <span class="trade-stock">{row['stock']}</span>
          <span class="trade-action trade-{action_cls}">{row['action']}</span>
          <span class="trade-detail">{int(row['shares'])}股 @ {row['price']}</span>
        </div>"""

    if not recent_rows:
        recent_rows = '<div style="text-align:center;color:#b0b5c0;font-size:12px;padding:10px">近7日暂无记录</div>'

    return f"""<div class="card">
  <p class="section-title">做T战绩</p>
  <div class="stat-summary">
    <div class="stat-item">
      <span class="stat-num">{stats['total_pairs']}</span>
      <span class="stat-label">总做T次数</span>
    </div>
    <div class="stat-item">
      <span class="stat-num" style="color:{win_color}">{stats['win_rate']:.0f}%</span>
      <span class="stat-label">胜率</span>
    </div>
    <div class="stat-item">
      <span class="stat-num" style="color:{pnl_color}">{pnl_sign}{stats['total_profit']:.2f}</span>
      <span class="stat-label">累计收益(元)</span>
    </div>
  </div>

  <div class="divider"></div>

  <div class="t-stat-header">
    <span class="t-stat-name">股票</span>
    <span class="t-stat-val">次数</span>
    <span class="t-stat-val">胜率</span>
    <span class="t-stat-val">盈亏</span>
  </div>
  {stock_rows if stock_rows else '<div style="text-align:center;color:#b0b5c0;font-size:12px;padding:10px">暂无完成的做T记录</div>'}

  <div class="divider"></div>

  <p class="section-title" style="margin-bottom:8px">近7日记录</p>
  {recent_rows}

  <button class="add-trade-btn" onclick="openTradeModal()">＋ 记录一笔交易</button>
</div>"""

def generate():
    update_data()
    now = datetime.now()
    signals, errors = {}, {}
    for name, cfg in STOCKS.items():
        try:
            signals[name] = calc_signals(cfg)
        except Exception as e:
            errors[name] = str(e)

    trades     = load_trades()
    trade_stat = calc_trade_stats(trades)

    today_md = now.strftime('%m-%d')
    STOCK_BUTTONS_HTML = ''.join(
        '<button class="seg-btn" onclick="selectStock(this,\'' + name + '\')">' + name + '</button>'
        for name in STOCKS
    )
    cards = ''
    for name, cfg in STOCKS.items():
        if name in signals:
            cards += stock_card(name, signals[name], today_md)
        else:
            cards += f'<div class="card"><p style="color:#f5222d">{name} 加载失败: {errors[name]}</p></div>'

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>做T辅助信号 {now.strftime('%m-%d')}</title>
<style>{CSS}</style>
</head>
<body>
<h1>做T辅助信号</h1>
<div class="sub-row">
  <p class="sub">更新于 {now.strftime('%Y-%m-%d %H:%M')} &nbsp;·&nbsp; 工作日 17:30 自动刷新</p>
  <button class="refresh-btn" id="refreshBtn" onclick="manualRefresh()">🔄 立即刷新</button>
</div>

{cards}

<div class="card">
  <p class="section-title">今日操作流程</p>
  <div class="step">
    <div class="step-num">1</div>
    <div class="step-body">
      <p class="step-title"><span class="time-pill">17:30</span>页面自动更新</p>
      <p class="step-desc">每个工作日收盘后自动拉取数据，刷新本页面即可查看当日信号。若卡片显示"非最新"，点右上角刷新按钮手动拉取</p>
    </div>
  </div>
  <div class="step">
    <div class="step-num">2</div>
    <div class="step-body">
      <p class="step-title"><span class="time-pill">09:15</span>设同花顺条件单</p>
      <p class="step-desc">打开同花顺 → 交易 → 条件单 → 新建<br>高抛价触发卖出，低吸价触发买入，各设一单</p>
    </div>
  </div>
  <div class="step">
    <div class="step-num">3</div>
    <div class="step-body">
      <p class="step-title"><span class="time-pill">09:30</span>开盘观察30分钟</p>
      <p class="step-desc">确认方向与信号一致；大盘跌超1.5%时撤低吸条件单</p>
    </div>
  </div>
  <div class="step">
    <div class="step-num">4</div>
    <div class="step-body">
      <p class="step-title"><span class="time-pill">14:55</span>收盘前确认</p>
      <p class="step-desc">确保当日T仓已平，不持有当天买入的仓位过夜</p>
    </div>
  </div>
</div>

<div class="card">
  <p class="section-title">今日操作清单</p>
  <ul class="checklist">
    <li><div class="chk"></div>页面已刷新，数据为最新交易日</li>
    {''.join(f'<li><div class="chk"></div>{name}条件单已挂好</li>' for name in STOCKS)}
    <li><div class="chk"></div>开盘30分钟已观察确认</li>
    <li><div class="chk"></div>收盘前T仓已平</li>
  </ul>
</div>

<div class="card">
  <p class="section-title">风控规则</p>
  <div class="risk-list">
    <div class="risk-item"><span class="risk-dot">▸</span>每只股票做T仓位不超过持仓20%</div>
    <div class="risk-item"><span class="risk-dot">▸</span>触发止损价时减仓，不补仓摊薄</div>
    <div class="risk-item"><span class="risk-dot">▸</span>单日亏损超总资产1%，当天停止操作</div>
    <div class="risk-item"><span class="risk-dot">▸</span>大盘跌幅超1.5%，撤销低吸条件单</div>
    <div class="risk-item"><span class="risk-dot">▸</span>当天买入的T仓必须当天平掉，不过夜</div>
    <div class="risk-item"><span class="risk-dot">▸</span>收到红色预警的股票当日暂停做T</div>
  </div>
</div>

{trade_stats_html(trade_stat)}

<a class="screener-btn" href="screener.html">查看今日选股推荐 →</a>

<p class="footer">仅供参考，不构成投资建议 · 据此操作风险自负</p>

<!-- 交易录入弹窗 -->
<div class="modal-overlay" id="tradeModal" onclick="closeOnBackdrop(event)">
  <div class="modal">
    <div class="modal-title">
      记录一笔交易
      <button class="modal-close" onclick="closeTradeModal()">×</button>
    </div>

    <div class="form-group">
      <label class="form-label">股票</label>
      <div class="seg-group" id="stockSeg">
        {STOCK_BUTTONS_HTML}
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">操作</label>
      <div class="seg-group" id="actionSeg">
        <button class="seg-btn" onclick="selectAction(this,'高抛')">高抛（卖出）</button>
        <button class="seg-btn" onclick="selectAction(this,'低吸')">低吸（买入）</button>
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label class="form-label">数量（股）</label>
        <input class="form-input" id="shares" type="number" placeholder="100" inputmode="numeric">
      </div>
      <div class="form-group">
        <label class="form-label">成交价格（元）</label>
        <input class="form-input" id="price" type="number" placeholder="3.85" inputmode="decimal" step="0.01">
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">备注（选填）</label>
      <input class="form-input" id="note" type="text" placeholder="如：止损单触发">
    </div>

    <button class="submit-btn" id="submitBtn" onclick="submitTrade()">提交记录</button>
    <p class="token-hint" id="tokenHint"></p>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const REPO  = 'sadaviknjx-ctrl/quant-app';
const BRANCH = 'main';
const FILE   = 'data/trades.csv';
const WORKFLOW = 'update.yml';

let selStock  = '';
let selAction = '';

async function manualRefresh() {{
  let token = localStorage.getItem('gh_token');
  if (!token) {{
    token = prompt('请输入 GitHub Personal Access Token（需要 repo 权限，只需输入一次）：');
    if (!token) return;
    localStorage.setItem('gh_token', token.trim());
    token = token.trim();
  }}

  const btn = document.getElementById('refreshBtn');
  btn.disabled = true;
  btn.textContent = '触发中...';

  try {{
    const res = await fetch(`https://api.github.com/repos/${{REPO}}/actions/workflows/${{WORKFLOW}}/dispatches`, {{
      method: 'POST',
      headers: {{ Authorization: `token ${{token}}`, Accept: 'application/vnd.github.v3+json', 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ ref: BRANCH }})
    }});
    if (!res.ok) throw new Error('触发失败，请检查 Token 权限');
    showToast('✓ 已触发更新，约2-3分钟后刷新页面查看', 3500);
  }} catch(err) {{
    showToast('❌ ' + err.message, 4000);
  }} finally {{
    setTimeout(() => {{ btn.disabled = false; btn.textContent = '🔄 立即刷新'; }}, 3000);
  }}
}}

function openTradeModal() {{
  document.getElementById('tradeModal').classList.add('open');
  const tk = localStorage.getItem('gh_token');
  document.getElementById('tokenHint').textContent = tk
    ? '已保存 GitHub Token ✓'
    : '首次使用会提示输入 GitHub Token（只输入一次）';
}}
function closeTradeModal() {{
  document.getElementById('tradeModal').classList.remove('open');
}}
function closeOnBackdrop(e) {{
  if (e.target === document.getElementById('tradeModal')) closeTradeModal();
}}

function selectStock(btn, val) {{
  selStock = val;
  document.querySelectorAll('#stockSeg .seg-btn').forEach(b => b.classList.remove('active-stock'));
  btn.classList.add('active-stock');
}}
function selectAction(btn, val) {{
  selAction = val;
  document.querySelectorAll('#actionSeg .seg-btn').forEach(b => {{
    b.classList.remove('active-sell','active-buy');
  }});
  btn.classList.add(val === '高抛' ? 'active-sell' : 'active-buy');
}}

function showToast(msg, ms=2500) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  setTimeout(() => t.style.display='none', ms);
}}

async function submitTrade() {{
  if (!selStock)  {{ showToast('请选择股票'); return; }}
  if (!selAction) {{ showToast('请选择操作'); return; }}
  const shares = document.getElementById('shares').value.trim();
  const price  = document.getElementById('price').value.trim();
  if (!shares || isNaN(shares) || +shares <= 0) {{ showToast('请输入有效数量'); return; }}
  if (!price  || isNaN(price)  || +price  <= 0) {{ showToast('请输入有效价格'); return; }}
  const note = document.getElementById('note').value.trim();

  let token = localStorage.getItem('gh_token');
  if (!token) {{
    token = prompt('请输入 GitHub Personal Access Token（需要 repo 权限，只需输入一次）：');
    if (!token) return;
    localStorage.setItem('gh_token', token.trim());
    token = token.trim();
  }}

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = '提交中...';

  async function fetchSha() {{
    const getRes = await fetch(`https://api.github.com/repos/${{REPO}}/contents/${{FILE}}?ref=${{BRANCH}}&_=${{Date.now()}}`, {{
      cache: 'no-store',
      headers: {{ Authorization: `token ${{token}}`, Accept: 'application/vnd.github.v3+json' }}
    }});
    if (!getRes.ok) {{
      const body = await getRes.json().catch(() => ({{}}));
      throw new Error(`读取文件失败 (${{getRes.status}}): ${{body.message || '未知错误'}}`);
    }}
    return getRes.json();
  }}

  async function writeTrade() {{
    const fileData = await fetchSha();
    const oldContent = atob(fileData.content.replace(/\\n/g,''));
    const today = new Date().toLocaleDateString('sv-SE'); // YYYY-MM-DD
    const newLine = `${{today}},${{selStock}},${{selAction}},${{shares}},${{price}},${{note}}\\n`;
    const newContent = btoa(unescape(encodeURIComponent(oldContent + newLine)));

    return fetch(`https://api.github.com/repos/${{REPO}}/contents/${{FILE}}`, {{
      method: 'PUT',
      headers: {{ Authorization: `token ${{token}}`, Accept: 'application/vnd.github.v3+json', 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        message: `trade: ${{selStock}} ${{selAction}} ${{shares}}股@${{price}}`,
        content: newContent,
        sha: fileData.sha,
        branch: BRANCH
      }})
    }});
  }}

  try {{
    let putRes = await writeTrade();

    // SHA 冲突（文件刚被其他提交更新）时自动重试一次
    if (putRes.status === 409) {{
      await new Promise(r => setTimeout(r, 800));
      putRes = await writeTrade();
    }}

    if (!putRes.ok) {{
      const body = await putRes.json().catch(() => ({{}}));
      throw new Error(`写入失败 (${{putRes.status}}): ${{body.message || '未知错误'}}`);
    }}

    // 4. 触发 Actions 重新生成报告
    await fetch(`https://api.github.com/repos/${{REPO}}/actions/workflows/${{WORKFLOW}}/dispatches`, {{
      method: 'POST',
      headers: {{ Authorization: `token ${{token}}`, Accept: 'application/vnd.github.v3+json', 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ ref: BRANCH }})
    }});

    showToast('✓ 记录成功！约2分钟后刷新页面查看战绩', 3500);
    closeTradeModal();

    // 清空表单
    selStock = selAction = '';
    document.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('active-stock','active-sell','active-buy'));
    ['shares','price','note'].forEach(id => document.getElementById(id).value = '');

  }} catch(err) {{
    showToast('❌ ' + err.message, 4000);
  }} finally {{
    btn.disabled = false;
    btn.textContent = '提交记录';
  }}
}}
</script>
</body>
</html>"""

    out = os.path.join(DOCS, 'index.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'报告已生成: {out}')

if __name__ == '__main__':
    generate()
