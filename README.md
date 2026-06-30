# 量化A股助手

个人化的A股做T辅助工具，网站：[quant.sugaryu.xyz](https://quant.sugaryu.xyz)

## 功能
- **做T辅助信号**：每个交易日17:30自动更新，给持仓股票计算高抛/低吸/止损挂单价
- **强势持有识别**：120日涨幅超过30%的持仓自动切换为"持有为主"模式，不建议做T（基于历史回测）
- **选股推荐**：接入开源项目 [Sequoia-X](https://github.com/sngyai/Sequoia) 的海龟突破、RPS强势、均线放量三种技术信号
- **做T战绩统计**：网页直接录入每笔高抛/低吸交易，自动统计胜率和收益
- **持仓自动同步**：通过 Cowork 定时任务读取同花顺客户端真实持仓，自动更新到网站配置

## 目录结构
```
scripts/
  generate_report.py       主报告生成（持仓信号 + 做T战绩）
  stock_screener.py        选股推荐
  backtest_t_strategy.py   做T信号策略回测工具
  add_trade.py             命令行录入交易（备用，主要用网页弹窗）
docs/                       GitHub Pages 静态站点输出目录
data/                       行情历史数据 + 交易记录
.github/workflows/          GitHub Actions 自动更新任务
```

## 本地运行
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/generate_report.py
python scripts/stock_screener.py
```

仅供个人参考，不构成投资建议。
