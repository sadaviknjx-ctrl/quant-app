#!/usr/bin/env python3
"""每次做T后运行此脚本快速录入交易记录"""
import csv, os
from datetime import datetime

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_CSV = os.path.join(ROOT, 'data', 'trades.csv')

STOCKS = ['三峡新材', '京东方A', '华远控股', '铜陵有色']

def ask(prompt, valid=None):
    while True:
        val = input(prompt).strip()
        if not val:
            continue
        if valid and val not in valid:
            print(f'  请输入: {" / ".join(valid)}')
            continue
        return val

def main():
    print('\n── 做T交易录入 ──')

    # 日期
    today = datetime.now().strftime('%Y-%m-%d')
    date_in = input(f'日期 [{today}]: ').strip()
    date = date_in if date_in else today

    # 股票
    print('股票: ' + ' / '.join(f'{i+1}.{s}' for i, s in enumerate(STOCKS)))
    idx = ask(f'选择 (1-{len(STOCKS)}): ', [str(i+1) for i in range(len(STOCKS))])
    stock = STOCKS[int(idx) - 1]

    # 操作
    action = ask('操作 (高抛/低吸): ', ['高抛', '低吸'])

    # 数量
    while True:
        try:
            shares = int(ask('数量 (股): '))
            if shares > 0:
                break
        except ValueError:
            pass
        print('  请输入正整数')

    # 价格
    while True:
        try:
            price = float(ask('成交价格: '))
            if price > 0:
                break
        except ValueError:
            pass
        print('  请输入有效价格')

    note = input('备注 (可留空): ').strip()

    row = [date, stock, action, shares, price, note]
    print(f'\n  {date}  {stock}  {action}  {shares}股 @ {price}  {note}')
    confirm = ask('确认写入? (y/n): ', ['y', 'n'])
    if confirm != 'y':
        print('已取消')
        return

    file_exists = os.path.exists(TRADES_CSV)
    with open(TRADES_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['date', 'stock', 'action', 'shares', 'price', 'note'])
        writer.writerow(row)

    print(f'✓ 已写入 {TRADES_CSV}')
    print('\n更新报告请运行:')
    print('  python3.11 scripts/generate_report.py && git add data/docs && git commit -m "trade: update" && git push')

if __name__ == '__main__':
    main()
