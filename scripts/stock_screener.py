import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

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
CANDIDATE_CAP = 400   # 按成交额取前N只做精细分析，控制运行时长
MAX_WORKERS  = 12     # 并发拉取历史数据的线程数
RPS_PERIOD   = 120    # RPS相对强度计算周期（参考欧奈尔CANSLIM体系）
RPS_THRESHOLD = 85    # 候选池内RPS百分位阈值（候选池已是流动性较好子集，阈值略低于全市场90）

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

    # 按成交额取前N只，避免逐只拉取历史数据耗时过长
    df = df.sort_values('amount', ascending=False).head(CANDIDATE_CAP)
    print(f'基础过滤后剩余: {len(df)} 只，取成交额前{CANDIDATE_CAP}只精细分析...')

    end_date   = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=RPS_PERIOD + 100)).strftime('%Y%m%d')  # 多留缓冲覆盖RPS所需周期（含节假日）

    def analyze_one(row):
        code   = row['code']
        name   = row['name']
        price  = row['price']
        amount = row['amount']
        symbol = row['symbol_raw']

        try:
            hist = ak.stock_zh_a_daily(symbol=symbol, start_date=start_date,
                                        end_date=end_date, adjust='qfq')
            if len(hist) < 25:
                return None

            hist['open']  = hist['open'].astype(float)
            hist['close'] = hist['close'].astype(float)
            hist['high']  = hist['high'].astype(float)
            hist['low']   = hist['low'].astype(float)
            hist['vol']   = hist['volume'].astype(float)
            hist['amt']   = hist['amount'].astype(float)

            # 日均波幅 = (high-low)/close 的均值
            hist['range_pct'] = (hist['high'] - hist['low']) / hist['close'] * 100
            avg_range = hist['range_pct'].tail(20).mean()

            if avg_range < VOLATILITY_MIN or avg_range > VOLATILITY_MAX:
                return None

            # 均线趋势：MA5 > MA10（短期向上）
            ma5  = hist['close'].rolling(5).mean().iloc[-1]
            ma10 = hist['close'].rolling(10).mean().iloc[-1]
            ma20 = hist['close'].rolling(20).mean().iloc[-1]

            # 量能稳定：近5日均量 / 近20日均量
            vol5  = hist['vol'].tail(5).mean()
            vol20 = hist['vol'].tail(20).mean()
            vol_ratio = vol5 / vol20 if vol20 > 0 else 0

            # 基础评分：波幅适中 + 量能稳定 + 价格站上MA5
            score = 0
            if ma5 > ma10:        score += 30
            if price > ma5:       score += 20
            if 3 < avg_range < 6: score += 30  # 波幅最佳区间
            if 0.8 < vol_ratio < 2.0: score += 20

            # ── 移植自开源项目 Sequoia-X (github.com/sngyai/Sequoia) 的技术策略 ──
            signals = []

            # 1. 海龟突破：今日收盘价突破此前20日最高价 + 放量 + 阳线
            close_today, open_today = hist['close'].iloc[-1], hist['open'].iloc[-1]
            amount_today = hist['amt'].iloc[-1]
            prior_20_high = hist['high'].iloc[-21:-1].max() if len(hist) >= 21 else None
            turtle = bool(
                prior_20_high is not None and
                close_today >= prior_20_high and
                amount_today >= 1e8 and
                close_today > open_today
            )
            if turtle:
                signals.append('海龟突破')
                score += 15

            # 2. 均线放量：MA5>MA10>MA20 多头排列 + 放量
            ma_volume = bool(ma5 > ma10 > ma20 and vol_ratio > 1.3)
            if ma_volume:
                signals.append('均线放量')
                score += 10

            # 3. RPS 相对强度（欧奈尔体系）：候选池内排名前列，留待主流程统一计算百分位
            pct_period = None
            if len(hist) > RPS_PERIOD:
                base_close = hist['close'].iloc[-RPS_PERIOD - 1]
                if base_close > 0:
                    pct_period = (close_today - base_close) / base_close

            return {
                'code': code, 'name': name, 'price': price,
                'amount_wan': round(amount / 1e4), 'avg_range': round(avg_range, 2),
                'ma5': round(ma5, 2), 'ma10': round(ma10, 2), 'ma20': round(ma20, 2),
                'vol_ratio': round(vol_ratio, 2), 'score': score,
                'trend': '↑' if ma5 > ma10 else ('↓' if ma5 < ma10 else '→'),
                'signals': signals, 'pct_period': pct_period,
            }
        except Exception:
            return None

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(analyze_one, row) for _, row in df.iterrows()]
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            if r:
                results.append(r)
            if i % 50 == 0:
                print(f'  已处理 {i}/{len(futures)}')

    # RPS 相对强度：在候选池内按120日涨幅排百分位（参考 Sequoia-X 的 RpsBreakoutStrategy）
    valid_pct = [r for r in results if r['pct_period'] is not None]
    if valid_pct:
        s = pd.Series([r['pct_period'] for r in valid_pct])
        ranks = s.rank(pct=True) * 100
        for r, rank in zip(valid_pct, ranks):
            r['rps'] = round(rank, 1)
            if rank >= RPS_THRESHOLD:
                r['signals'].append('RPS强势')
                r['score'] += 15

    for r in results:
        r.pop('pct_period', None)
        r.setdefault('rps', None)
        entry_price, entry_reason = suggest_entry(r)
        r['entry_price']  = entry_price
        r['entry_reason'] = entry_reason

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:TOP_N]


def suggest_entry(r):
    """按信号类型给出建仓建议价，优先级：海龟突破(顺势) > RPS强势(等回踩) > 均线放量(折中) > 无信号(保守折价)"""
    price, ma5 = r['price'], r['ma5']
    if '海龟突破' in r['signals']:
        return round(price, 2), '突破型信号，建议现价附近顺势介入，不必等回调'
    if 'RPS强势' in r['signals']:
        return round(ma5, 2), f'强势股，建议等回踩MA5（{ma5}）再介入，避免追高'
    if '均线放量' in r['signals']:
        mid = round((price + ma5) / 2, 2)
        return mid, f'温和放量，建议现价与MA5之间（约{mid}）择机介入'
    return round(price * 0.98, 2), '无强信号，建议现价小幅折价（-2%）介入，避免追高'

def build_html(results):
    now = datetime.now()

    if not results:
        rows = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#64748b">暂无符合条件的股票</td></tr>'
    else:
        rows = ''
        for r in results:
            trend_color = '#ef4444' if r['trend'] == '↑' else ('#22c55e' if r['trend'] == '↓' else '#94a3b8')
            score_color = '#22c55e' if r['score'] >= 100 else ('#f59e0b' if r['score'] >= 70 else '#94a3b8')
            signal_html = ''.join(f'<span class="sig-tag">{s}</span>' for s in r['signals']) or '<span class="sig-none">—</span>'
            rows += f"""<tr>
              <td><span class="sname">{r['name']}</span><br><span class="scode">{r['code']}</span></td>
              <td style="font-weight:700">{r['price']}</td>
              <td style="color:{trend_color}">{r['trend']} {r['ma5']}</td>
              <td>{r['amount_wan']}万</td>
              <td>{signal_html}</td>
              <td style="color:{score_color};font-weight:700">{r['score']}</td>
              <td><button class="add-pos-btn" onclick='openAddModal({{"code":"{r['code']}","name":"{r['name']}","price":{r['price']},"entry":{r['entry_price']},"reason":"{r['entry_reason']}"}})'>+加入</button></td>
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
  .sig-tag{{display:inline-block;background:#e8f4ff;color:#0958d9;border-radius:4px;padding:1px 5px;font-size:10px;margin:1px;white-space:nowrap}}
  .sig-none{{color:#c0c4cc}}
  .add-pos-btn{{padding:4px 8px;background:#1677ff;color:#fff;border:none;border-radius:6px;font-size:11px;cursor:pointer;white-space:nowrap}}
  .modal-overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:100;align-items:flex-end;justify-content:center}}
  .modal-overlay.open{{display:flex}}
  .modal{{background:#fff;border-radius:20px 20px 0 0;padding:24px 20px 36px;width:100%;max-width:540px;animation:slideUp .25s ease}}
  @keyframes slideUp{{from{{transform:translateY(100%)}}to{{transform:translateY(0)}}}}
  .modal-title{{font-size:16px;font-weight:600;color:#1a1d23;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center}}
  .modal-close{{background:none;border:none;font-size:22px;color:#9ca3af;cursor:pointer;line-height:1}}
  .reason-box{{background:#f0f7ff;border:1px solid #91caff;border-radius:10px;padding:10px 12px;font-size:12px;color:#0958d9;margin-bottom:16px;line-height:1.6}}
  .form-group{{margin-bottom:14px}}
  .form-label{{font-size:12px;color:#8a8f9b;margin-bottom:6px;display:block;font-weight:500}}
  .form-input{{width:100%;padding:11px 12px;border:1.5px solid #e8eaed;border-radius:10px;font-size:15px;color:#1a1d23;background:#f8f9fb;outline:none}}
  .form-input:focus{{border-color:#1677ff;background:#fff}}
  .form-row{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
  .submit-btn{{width:100%;padding:14px;background:#1677ff;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:600;cursor:pointer;margin-top:6px}}
  .submit-btn:disabled{{background:#b0c4de;cursor:not-allowed}}
  .toast{{position:fixed;top:24px;left:50%;transform:translateX(-50%);background:#1a1d23;color:#fff;padding:10px 20px;border-radius:10px;font-size:13px;z-index:200;display:none;white-space:nowrap}}
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
        <th>股票</th><th>现价</th><th>趋势/MA5</th><th>成交额</th><th>信号</th><th>评分</th><th></th>
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
  <div class="crit-item" style="color:#f59e0b">▸ 评分满分140（基础100 + 技术信号加分），≥100为优先关注，仅供参考</div>
</div>

<div class="criteria">
  <div class="criteria-title">技术信号说明（移植自开源项目 Sequoia-X）</div>
  <div class="crit-item">▸ <b>海龟突破</b>：收盘价突破前20日最高价 + 成交额超1亿 + 阳线：+15分</div>
  <div class="crit-item">▸ <b>均线放量</b>：MA5&gt;MA10&gt;MA20 多头排列 + 放量1.3倍以上：+10分</div>
  <div class="crit-item">▸ <b>RPS强势</b>：120日涨幅在候选池内排名前15%（欧奈尔相对强度体系）：+15分</div>
</div>

<a class="back-btn" href="index.html">← 返回持仓信号</a>

<div class="footer">仅供参考，不构成投资建议 · 据此操作风险自负</div>

<!-- 加入持仓弹窗 -->
<div class="modal-overlay" id="addModal" onclick="closeOnBackdrop(event)">
  <div class="modal">
    <div class="modal-title">
      <span id="addModalTitle">加入持仓</span>
      <button class="modal-close" onclick="closeAddModal()">×</button>
    </div>

    <div class="reason-box" id="entryReason"></div>

    <div class="form-row">
      <div class="form-group">
        <label class="form-label">建仓价（元，可调整）</label>
        <input class="form-input" id="entryPrice" type="number" step="0.01">
      </div>
      <div class="form-group">
        <label class="form-label">建仓数量（股）</label>
        <input class="form-input" id="entryShares" type="number" step="100" placeholder="如：500">
      </div>
    </div>
    <p style="font-size:11px;color:#9ca3af;margin:-6px 0 14px" id="cashHint"></p>

    <button class="submit-btn" id="addSubmitBtn" onclick="submitAddPosition()">确认加入持仓</button>
    <p style="font-size:11px;color:#b0b5c0;text-align:center;margin-top:10px">提交后约2-3分钟，刷新持仓页即可看到新卡片</p>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const REPO  = 'sadaviknjx-ctrl/quant-app';
const BRANCH = 'main';
const STOCKS_FILE = 'data/stocks.json';
const WORKFLOW = 'update.yml';

let pending = null;

function showToast(msg, ms=3000) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  setTimeout(() => t.style.display='none', ms);
}}

async function openAddModal(stock) {{
  pending = stock;
  document.getElementById('addModalTitle').textContent = `加入持仓：${{stock.name}}`;
  document.getElementById('entryReason').textContent = stock.reason;
  document.getElementById('entryPrice').value = stock.entry;
  document.getElementById('entryShares').value = '';
  document.getElementById('cashHint').textContent = '正在查询可用资金…';
  document.getElementById('addModal').classList.add('open');

  try {{
    const res = await fetch(`https://raw.githubusercontent.com/${{REPO}}/${{BRANCH}}/data/account.json?_=${{Date.now()}}`);
    if (res.ok) {{
      const acc = await res.json();
      const cash = acc.available_cash;
      const suggestShares = Math.floor(cash * 0.18 / stock.entry / 100) * 100;
      document.getElementById('cashHint').textContent =
        `账户可用资金约${{cash.toFixed(0)}}元（${{acc.date}}）· 按单票≤18%仓位建议约${{suggestShares}}股，仅供参考`;
      if (suggestShares >= 100) document.getElementById('entryShares').value = suggestShares;
    }} else {{
      document.getElementById('cashHint').textContent = '暂无可用资金数据，请自行填写股数';
    }}
  }} catch(e) {{
    document.getElementById('cashHint').textContent = '暂无可用资金数据，请自行填写股数';
  }}
}}

function closeAddModal() {{
  document.getElementById('addModal').classList.remove('open');
}}
function closeOnBackdrop(e) {{
  if (e.target === document.getElementById('addModal')) closeAddModal();
}}

async function submitAddPosition() {{
  const entry  = parseFloat(document.getElementById('entryPrice').value);
  const shares = parseInt(document.getElementById('entryShares').value);
  if (!entry || entry <= 0) {{ showToast('请输入有效建仓价'); return; }}
  if (!shares || shares <= 0 || shares % 100 !== 0) {{ showToast('请输入100的整数倍股数'); return; }}

  let token = localStorage.getItem('gh_token');
  if (!token) {{
    token = prompt('请输入 GitHub Personal Access Token（需要 repo 权限，只需输入一次）：');
    if (!token) return;
    localStorage.setItem('gh_token', token.trim());
    token = token.trim();
  }}

  const btn = document.getElementById('addSubmitBtn');
  btn.disabled = true;
  btn.textContent = '提交中...';

  const symbol = (pending.code.startsWith('6') ? 'sh' : 'sz') + pending.code;

  async function fetchFile() {{
    const res = await fetch(`https://api.github.com/repos/${{REPO}}/contents/${{STOCKS_FILE}}?ref=${{BRANCH}}&_=${{Date.now()}}`, {{
      cache: 'no-store',
      headers: {{ Authorization: `token ${{token}}`, Accept: 'application/vnd.github.v3+json' }}
    }});
    if (!res.ok) throw new Error(`读取失败 (${{res.status}})`);
    return res.json();
  }}

  async function writeFile() {{
    const fileData = await fetchFile();
    const stocks = JSON.parse(decodeURIComponent(escape(atob(fileData.content.replace(/\\n/g,'')))));
    stocks[pending.name] = {{ code: pending.code, symbol: symbol, hold: shares, cost: entry }};
    const newContent = btoa(unescape(encodeURIComponent(JSON.stringify(stocks, null, 2))));
    return fetch(`https://api.github.com/repos/${{REPO}}/contents/${{STOCKS_FILE}}`, {{
      method: 'PUT',
      headers: {{ Authorization: `token ${{token}}`, Accept: 'application/vnd.github.v3+json', 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        message: `position: add ${{pending.name}} ${{shares}}股@${{entry}}`,
        content: newContent, sha: fileData.sha, branch: BRANCH
      }})
    }});
  }}

  try {{
    let putRes = await writeFile();
    if (putRes.status === 409) {{
      await new Promise(r => setTimeout(r, 800));
      putRes = await writeFile();
    }}
    if (!putRes.ok) {{
      const body = await putRes.json().catch(() => ({{}}));
      throw new Error(`写入失败 (${{putRes.status}}): ${{body.message || '未知错误'}}`);
    }}

    await fetch(`https://api.github.com/repos/${{REPO}}/actions/workflows/${{WORKFLOW}}/dispatches`, {{
      method: 'POST',
      headers: {{ Authorization: `token ${{token}}`, Accept: 'application/vnd.github.v3+json', 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ ref: BRANCH }})
    }});

    showToast(`✓ ${{pending.name}} 已加入持仓！约2-3分钟后刷新持仓页查看`, 4000);
    closeAddModal();
  }} catch(err) {{
    showToast('❌ ' + err.message, 4500);
  }} finally {{
    btn.disabled = false;
    btn.textContent = '确认加入持仓';
  }}
}}
</script>
</body>
</html>"""

    out = os.path.join(DOCS, 'screener.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'选股报告已生成: {out}')


def save_results_json(results):
    """落盘选股结果供 generate_report.py 读取，用于持仓页"建议轮动"功能"""
    import json
    out = os.path.join(DATA, 'screener_results.json')
    payload = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'results': results,
    }
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'选股结果已落盘: {out}')


if __name__ == '__main__':
    print('开始选股筛选，预计需要5–10分钟（逐只拉取历史数据）...')
    results = screen()
    print(f'\n筛选完成，共 {len(results)} 只股票入选')
    build_html(results)
    save_results_json(results)
