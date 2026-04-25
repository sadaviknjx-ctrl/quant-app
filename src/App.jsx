import { useState, useEffect, useRef, useMemo } from "react";

/* ══════════════════════ PART 1: Constants ══════════════════════ */
const FF="'Noto Sans SC','DM Sans',system-ui,sans-serif";
const FM="'JetBrains Mono','Fira Code',monospace";
const T={bg:'#faf9f7',card:'#fff',border:'#e8e5e0',pri:'#2563eb',priL:'#dbeafe',priD:'#1e40af',up:'#dc2626',upL:'#fef2f2',dn:'#16a34a',dnL:'#dcfce7',amb:'#d97706',ambL:'#fef3c7',txt:'#1a1a1a',tx2:'#555',tx3:'#999',surf:'#f3f1ed'};
const today=()=>new Date().toISOString().slice(0,10);
const addDays=(d,n)=>{const x=new Date(d);x.setDate(x.getDate()+n);return x.toISOString().slice(0,10)};
const daysBetween=(d1,d2)=>Math.floor((new Date(d2)-new Date(d1))/86400000);
const upDnC=v=>parseFloat(v)>0?T.up:parseFloat(v)<0?T.dn:T.tx3;
const PROXY_URL='https://quant.sugaryu.xyz';

/* ══════════════════════ PART 2: Storage (localStorage 替代 window.storage) ══════════════════════ */
const S={
  get:async(k,fb)=>{
    try{const r=localStorage.getItem(k);return r?JSON.parse(r):fb}
    catch{return fb}
  },
  set:async(k,v)=>{
    try{localStorage.setItem(k,JSON.stringify(v))}
    catch(e){console.error('Storage error:',e)}
  },
};

/* ══════════════════════ PART 3: Stock Pool (152只精选池) ══════════════════════ */
const STOCK_POOL=[
  // 食品饮料 消费 10
  ['贵州茅台','sh600519','消费'],['五粮液','sz000858','消费'],['泸州老窖','sz000568','消费'],
  ['山西汾酒','sh600809','消费'],['洋河股份','sz002304','消费'],['伊利股份','sh600887','消费'],
  ['双汇发展','sz000895','消费'],['海天味业','sh603288','消费'],['青岛啤酒','sh600600','消费'],
  ['农夫山泉','sh688868','消费'],
  // 家电 消费 5
  ['美的集团','sz000333','消费'],['格力电器','sz000651','消费'],['海尔智家','sh600690','消费'],
  ['老板电器','sz002508','消费'],['苏泊尔','sz002032','消费'],
  // 银行 金融 10
  ['招商银行','sh600036','金融'],['工商银行','sh601398','金融'],['建设银行','sh601939','金融'],
  ['农业银行','sh601288','金融'],['中国银行','sh601988','金融'],['交通银行','sh601328','金融'],
  ['平安银行','sz000001','金融'],['兴业银行','sh601166','金融'],['浦发银行','sh600000','金融'],
  ['宁波银行','sz002142','金融'],
  // 证券保险 金融 8
  ['中信证券','sh600030','金融'],['中国平安','sh601318','金融'],['中国人寿','sh601628','金融'],
  ['东方财富','sz300059','金融'],['中国太保','sh601601','金融'],['新华保险','sh601336','金融'],
  ['华泰证券','sh601688','金融'],['国泰君安','sh601211','金融'],
  // 新能源 12
  ['宁德时代','sz300750','新能源'],['比亚迪','sz002594','新能源'],['隆基绿能','sh601012','新能源'],
  ['阳光电源','sz300274','新能源'],['天齐锂业','sz002466','新能源'],['赣锋锂业','sz002460','新能源'],
  ['通威股份','sh600438','新能源'],['亿纬锂能','sz300014','新能源'],['恩捷股份','sz002812','新能源'],
  ['TCL中环','sz002129','新能源'],['晶澳科技','sz002459','新能源'],['长城汽车','sh601633','新能源'],
  // 汽车 6
  ['长安汽车','sz000625','新能源'],['上汽集团','sh600104','新能源'],['广汽集团','sh601238','新能源'],
  ['福耀玻璃','sh600660','制造'],['华域汽车','sh600741','制造'],['赛力斯','sh601127','新能源'],
  // 电子半导体 12
  ['立讯精密','sz002475','科技'],['歌尔股份','sz002241','科技'],['韦尔股份','sh603501','科技'],
  ['中芯国际','sh688981','科技'],['北方华创','sz002371','科技'],['海光信息','sh688041','科技'],
  ['澜起科技','sh688008','科技'],['紫光国微','sz002049','科技'],['兆易创新','sh603986','科技'],
  ['闻泰科技','sh600745','科技'],['沪电股份','sz002463','科技'],['长电科技','sh600584','科技'],
  // 计算机 10
  ['海康威视','sz002415','科技'],['大华股份','sz002236','科技'],['科大讯飞','sz002230','科技'],
  ['用友网络','sh600588','科技'],['中科曙光','sh603019','科技'],['金山办公','sh688111','科技'],
  ['恒生电子','sh600570','科技'],['广联达','sz002410','科技'],['深信服','sz300454','科技'],
  ['浪潮信息','sz000977','科技'],
  // 通信 6
  ['中兴通讯','sz000063','通信'],['中国移动','sh600941','通信'],['中国电信','sh601728','通信'],
  ['中国联通','sh600050','通信'],['烽火通信','sh600498','通信'],['光迅科技','sz002281','通信'],
  // 医药 15
  ['恒瑞医药','sh600276','医药'],['药明康德','sh603259','医药'],['迈瑞医疗','sz300760','医药'],
  ['爱尔眼科','sz300015','医药'],['长春高新','sz000661','医药'],['片仔癀','sh600436','医药'],
  ['云南白药','sz000538','医药'],['白云山','sh600332','医药'],['同仁堂','sh600085','医药'],
  ['华东医药','sz000963','医药'],['复星医药','sh600196','医药'],['国药一致','sz000028','医药'],
  ['上海医药','sh601607','医药'],['九州通','sh600998','医药'],['东阿阿胶','sz000423','医药'],
  // 地产 6
  ['万科A','sz000002','地产'],['保利发展','sh600048','地产'],['招商蛇口','sz001979','地产'],
  ['金地集团','sh600383','地产'],['中国建筑','sh601668','地产'],['华发股份','sh600325','地产'],
  // 能源 6
  ['中国石油','sh601857','能源'],['中国石化','sh600028','能源'],['中国海油','sh600938','能源'],
  ['中国神华','sh601088','能源'],['陕西煤业','sh601225','能源'],['兖矿能源','sh600188','能源'],
  // 制造 有色钢铁 8
  ['宝钢股份','sh600019','制造'],['紫金矿业','sh601899','制造'],['洛阳钼业','sh603993','制造'],
  ['江西铜业','sh600362','制造'],['云铝股份','sz000807','制造'],['北方稀土','sh600111','制造'],
  ['中国铝业','sh601600','制造'],['山东黄金','sh600547','制造'],
  // 机械 8
  ['三一重工','sh600031','制造'],['徐工机械','sh000425','制造'],['中联重科','sz000157','制造'],
  ['恒立液压','sh601100','制造'],['汇川技术','sz300124','制造'],['中国中车','sh601766','制造'],
  ['振华重工','sh600320','制造'],['杰瑞股份','sz002353','制造'],
  // 军工 6
  ['中航沈飞','sh600760','军工'],['航发动力','sh600893','军工'],['中航光电','sz002179','军工'],
  ['中国重工','sh601989','军工'],['中直股份','sh600038','军工'],['航天电器','sz002025','军工'],
  // 传媒 6
  ['分众传媒','sz002027','传媒'],['芒果超媒','sz300413','传媒'],['东方明珠','sh600637','传媒'],
  ['世纪华通','sz002602','传媒'],['华策影视','sz300133','传媒'],['光线传媒','sz300251','传媒'],
  // 交运 6
  ['京沪高铁','sh601816','交运'],['上海机场','sh600009','交运'],['中远海控','sh601919','交运'],
  ['顺丰控股','sz002352','交运'],['大秦铁路','sh601006','交运'],['招商港口','sz001872','交运'],
  // 公用 4
  ['长江电力','sh600900','公用'],['华能国际','sh600011','公用'],['国电电力','sh600795','公用'],
  ['中国核电','sh601985','公用'],
];

const CODE_MAP={};
STOCK_POOL.forEach(([n,c])=>{CODE_MAP[n]=c});
// 用户已有股票（持仓 + 黑名单 + 历史）补充进 CODE_MAP
const EXTRA_CODES={
  '平潭发展':'sz000592','中安科':'sh600654','山子高科':'sz000981','雷科防务':'sz002413',
  '实达集团':'sh600734','津药药业':'sh600488','岩山科技':'sz002195','永辉超市':'sh601933',
  '航天发展':'sz000547','传媒ETF':'sz512980','通信ETF':'sh515880','标普油气ETF':'sh513350',
};
Object.assign(CODE_MAP,EXTRA_CODES);

const resolveCode=n=>{
  if(CODE_MAP[n])return CODE_MAP[n];
  if(/^\d{6}$/.test(n)){const f=n[0];if(f==='6')return'sh'+n;if(f==='0'||f==='3')return'sz'+n;if(f==='8'||f==='9')return'sh'+n}
  return null;
};

/* ══════════════════════ PART 4: Math + Sector ══════════════════════ */
const MATH={
  kelly:(p,b)=>{const q=1-p,f=(p*b-q)/b;return{half:Math.max(0,f/2),edge:p*b-q}},
  ev:(p,w,l)=>p*w-(1-p)*l,
};
const SECTORS=[
  {s:'金融',kw:/银行|保险|平安|招商|工商|建设|中信|兴业|证券|券商/},
  {s:'新能源',kw:/宁德|比亚迪|光伏|锂|新能源|隆基|通威|蔚来|理想|储能/},
  {s:'消费',kw:/茅台|五粮液|伊利|海天|美的|格力|海尔|洋河|泸州|农夫/},
  {s:'科技',kw:/腾讯|阿里|百度|芯片|半导体|中芯|海康|立讯|京东方|寒武纪/},
  {s:'医药',kw:/恒瑞|药明|迈瑞|片仔癀|云南白药|智飞|医药|生物|制药|津药/},
  {s:'地产',kw:/万科|保利|碧桂园|融创|龙湖|地产/},
  {s:'制造',kw:/三一|中联|徐工|潍柴|福耀|海螺|宝钢|中国建筑/},
  {s:'军工',kw:/航天|中航|中安科|雷科|军工|国防/},
];
const getSector=n=>{for(const r of SECTORS)if(r.kw.test(n))return r.s;return'其他'};

/* ══════════════════════ PART 5: Stock Screening (本地规则筛选) ══════════════════════ */
const HARD_RULES={
  marketCap:50,
  changeMin:-3,changeMax:7,
  turnoverMin:1.0,turnoverMax:12,
  peMin:0,peMax:100,
};

const scoreStock=(q)=>{
  let s=50;
  if(q.turnover>=2&&q.turnover<=8)s+=15;
  else if(q.turnover>=1&&q.turnover<=12)s+=8;
  if(q.changePct>=-1&&q.changePct<=3)s+=15;
  else if(q.changePct>=-3&&q.changePct<=5)s+=8;
  if(q.pe>0&&q.pe<30)s+=10;
  else if(q.pe>0&&q.pe<50)s+=5;
  if(q.marketCap>=100&&q.marketCap<=3000)s+=10;
  else if(q.marketCap>=50)s+=5;
  return Math.min(100,s);
};

const screenStocks=async(excludeCodes=[])=>{
  const excludeSet=new Set(excludeCodes);
  const pool=STOCK_POOL.filter(([n,c])=>!excludeSet.has(c));

  // 分两批请求（每批最多 80 只）
  const batch1=pool.slice(0,80).map(([_,c])=>c).join(',');
  const batch2=pool.slice(80).map(([_,c])=>c).join(',');

  const requests=[fetch(`${PROXY_URL}/quote?code=${batch1}`).then(r=>r.json())];
  if(batch2)requests.push(fetch(`${PROXY_URL}/quote?code=${batch2}`).then(r=>r.json()));

  const results=await Promise.all(requests);
  const allData={};
  results.forEach(r=>{if(r.ok&&r.data)Object.assign(allData,r.data)});

  // 硬规则过滤
  const passed=[];
  for(const[name,code,sector]of pool){
    const q=allData[code];
    if(!q||!q.price)continue;
    if(q.marketCap<HARD_RULES.marketCap)continue;
    if(q.changePct<HARD_RULES.changeMin||q.changePct>HARD_RULES.changeMax)continue;
    if(q.turnover<HARD_RULES.turnoverMin||q.turnover>HARD_RULES.turnoverMax)continue;
    if(q.pe<=HARD_RULES.peMin||q.pe>HARD_RULES.peMax)continue;

    passed.push({
      name,code,sector,
      price:q.price,change:q.changePct,
      turnover:q.turnover,pe:q.pe,
      marketCap:q.marketCap,pb:q.pb,
      score:scoreStock(q),
    });
  }

  passed.sort((a,b)=>b.score-a.score);

  // 板块分散：每板块最多 2 支，取 5 支
  const picked=[];
  const sectorCount={};
  for(const s of passed){
    if((sectorCount[s.sector]||0)>=2)continue;
    const winProb=s.score;
    const p=winProb/100;
    const k=MATH.kelly(p,1.67);
    const ev=MATH.ev(p,5,3);
    const pos=Math.min(25,Math.max(0,k.half*100*0.5));
    picked.push({
      ...s,
      winProb,
      ev:ev.toFixed(1),
      position:pos.toFixed(0),
      stopLoss:(s.price*0.97).toFixed(2),
      catalyst:`量价评分${s.score} · 换手${s.turnover}% · 涨跌${s.change>0?'+':''}${s.change}%`,
      risk:'本地规则筛选 · 关注大盘环境与个股消息面',
    });
    sectorCount[s.sector]=(sectorCount[s.sector]||0)+1;
    if(picked.length>=5)break;
  }

  // 市场环境推断（基于通过率）
  const passRate=passed.length/pool.length;
  let regime='range';
  if(passRate>0.4)regime='bull';
  else if(passRate<0.1)regime='bear';

  return{
    candidates:picked,
    market:{
      regime,
      reason:`从${pool.length}只股池筛出${passed.length}支符合条件，覆盖${Object.keys(sectorCount).length}个板块`,
    },
  };
};

/* ══════════════════════ PART 6: Initial Data ══════════════════════ */
const REGIME_CFG={bull:{icon:'🐂',label:'牛市',c:T.up,mult:1},range:{icon:'😐',label:'震荡',c:T.amb,mult:.5},bear:{icon:'🐻',label:'熊市',c:T.dn,mult:.5},extreme:{icon:'⚡',label:'极端',c:T.up,mult:0}};

const INIT_HOLDINGS=[
  {name:'平潭发展',code:'sz000592',buyPrice:11.872,qty:500,buyDate:'2026-04-08',stopLoss:11.872*0.97,targetDays:5,currentPrice:0,pnl:0,pnlPct:0,holdDays:0,status:'normal',advice:''},
  {name:'中安科',code:'sh600654',buyPrice:4.591,qty:400,buyDate:'2026-04-15',stopLoss:4.591*0.97,targetDays:5,currentPrice:0,pnl:0,pnlPct:0,holdDays:0,status:'normal',advice:''},
];
const INIT_BLACKLIST=[
  {name:'平潭发展',code:'sz000592',lossCount:10,expireDate:'2026-05-19',reason:'连亏10次，累计亏¥3130'},
  {name:'实达集团',code:'sh600734',lossCount:5,expireDate:'2026-05-19',reason:'连亏5次，累计亏¥653'},
  {name:'山子高科',code:'sz000981',lossCount:5,expireDate:'2026-05-19',reason:'连亏5次，累计亏¥258'},
  {name:'雷科防务',code:'sz002413',lossCount:2,expireDate:'2026-05-19',reason:'连亏2次，累计亏¥685'},
  {name:'传媒ETF',code:'sz512980',lossCount:2,expireDate:'2026-05-19',reason:'连亏2次，累计亏¥67'},
  {name:'标普油气ETF',code:'sh513350',lossCount:2,expireDate:'2026-05-19',reason:'连亏2次，累计亏¥36'},
];
const INIT_HISTORY=[
  {name:'平潭发展',code:'sz000592',buyPrice:11.9,sellPrice:9.3,qty:100,pnl:-260,buyDate:'2025-11-21',sellDate:'2025-11-27',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.9,sellPrice:9.3,qty:100,pnl:-260,buyDate:'2025-11-21',sellDate:'2025-11-27',reason:'止损'},
  {name:'航天发展',code:'sz000547',buyPrice:13.71,sellPrice:11.71,qty:100,pnl:-200,buyDate:'2025-11-21',sellDate:'2025-11-27',reason:'止损'},
  {name:'通信ETF',code:'sh515880',buyPrice:2.733,sellPrice:2.669,qty:500,pnl:-32,buyDate:'2025-11-27',sellDate:'2025-11-28',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.7,sellPrice:12.05,qty:100,pnl:135,buyDate:'2025-11-28',sellDate:'2025-12-03',reason:'止盈'},
  {name:'通信ETF',code:'sh515880',buyPrice:2.672,sellPrice:2.76,qty:500,pnl:44,buyDate:'2025-11-28',sellDate:'2025-12-03',reason:'止盈'},
  {name:'通信ETF',code:'sh515880',buyPrice:2.751,sellPrice:2.76,qty:200,pnl:1.8,buyDate:'2025-12-01',sellDate:'2025-12-03',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.41,sellPrice:12.0,qty:100,pnl:59,buyDate:'2025-12-05',sellDate:'2025-12-08',reason:'止盈'},
  {name:'实达集团',code:'sh600734',buyPrice:6.95,sellPrice:5.32,qty:200,pnl:-326,buyDate:'2025-12-09',sellDate:'2025-12-16',reason:'止损'},
  {name:'实达集团',code:'sh600734',buyPrice:6.84,sellPrice:5.32,qty:100,pnl:-152,buyDate:'2025-12-09',sellDate:'2025-12-16',reason:'止损'},
  {name:'实达集团',code:'sh600734',buyPrice:5.9,sellPrice:5.32,qty:100,pnl:-58,buyDate:'2025-12-12',sellDate:'2025-12-16',reason:'止损'},
  {name:'实达集团',code:'sh600734',buyPrice:5.27,sellPrice:4.8,qty:100,pnl:-47,buyDate:'2025-12-16',sellDate:'2025-12-17',reason:'止损'},
  {name:'实达集团',code:'sh600734',buyPrice:5.5,sellPrice:4.8,qty:100,pnl:-70,buyDate:'2025-12-16',sellDate:'2025-12-17',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.21,sellPrice:14.8,qty:100,pnl:259,buyDate:'2025-12-08',sellDate:'2025-12-19',reason:'止盈'},
  {name:'永辉超市',code:'sh601933',buyPrice:5.89,sellPrice:5.52,qty:100,pnl:-37,buyDate:'2025-12-19',sellDate:'2025-12-22',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:15.3,sellPrice:13.28,qty:100,pnl:-202,buyDate:'2025-12-16',sellDate:'2025-12-23',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:14.5,sellPrice:14.0,qty:100,pnl:-50,buyDate:'2025-12-17',sellDate:'2025-12-26',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.78,sellPrice:15.6,qty:100,pnl:282,buyDate:'2025-12-22',sellDate:'2025-12-29',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:13.09,sellPrice:16.76,qty:100,pnl:367,buyDate:'2025-12-23',sellDate:'2025-12-30',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:16.0,sellPrice:15.3,qty:100,pnl:-70,buyDate:'2025-12-30',sellDate:'2026-01-05',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:15.21,sellPrice:15.71,qty:100,pnl:50,buyDate:'2025-12-31',sellDate:'2026-01-05',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:16.0,sellPrice:14.52,qty:100,pnl:-148,buyDate:'2025-12-31',sellDate:'2026-01-06',reason:'止损'},
  {name:'山子高科',code:'sz000981',buyPrice:4.5,sellPrice:4.56,qty:300,pnl:18,buyDate:'2026-01-07',sellDate:'2026-01-08',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:15.14,sellPrice:15.5,qty:100,pnl:36,buyDate:'2026-01-09',sellDate:'2026-01-14',reason:'止盈'},
  {name:'雷科防务',code:'sz002413',buyPrice:18.76,sellPrice:16.43,qty:100,pnl:-233,buyDate:'2026-01-12',sellDate:'2026-01-14',reason:'止损'},
  {name:'岩山科技',code:'sz002195',buyPrice:11.14,sellPrice:13.0,qty:100,pnl:186,buyDate:'2026-01-12',sellDate:'2026-01-14',reason:'止盈'},
  {name:'传媒ETF',code:'sz512980',buyPrice:1.352,sellPrice:1.221,qty:300,pnl:-39.3,buyDate:'2026-01-14',sellDate:'2026-01-16',reason:'止损'},
  {name:'传媒ETF',code:'sz512980',buyPrice:1.361,sellPrice:1.221,qty:200,pnl:-28,buyDate:'2026-01-14',sellDate:'2026-01-16',reason:'止损'},
  {name:'雷科防务',code:'sz002413',buyPrice:17.23,sellPrice:12.71,qty:100,pnl:-452,buyDate:'2026-01-14',sellDate:'2026-01-20',reason:'止损'},
  {name:'山子高科',code:'sz000981',buyPrice:5.65,sellPrice:4.64,qty:100,pnl:-101,buyDate:'2026-01-14',sellDate:'2026-01-28',reason:'止损'},
  {name:'山子高科',code:'sz000981',buyPrice:5.06,sellPrice:4.64,qty:100,pnl:-42,buyDate:'2026-01-16',sellDate:'2026-01-28',reason:'止损'},
  {name:'山子高科',code:'sz000981',buyPrice:5.1,sellPrice:4.64,qty:100,pnl:-46,buyDate:'2026-01-19',sellDate:'2026-01-28',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:14.81,sellPrice:11.18,qty:100,pnl:-363,buyDate:'2026-01-14',sellDate:'2026-02-05',reason:'止损'},
  {name:'山子高科',code:'sz000981',buyPrice:4.76,sellPrice:4.67,qty:100,pnl:-9,buyDate:'2026-01-28',sellDate:'2026-02-06',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:14.8,sellPrice:10.95,qty:100,pnl:-385,buyDate:'2026-01-15',sellDate:'2026-02-24',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.3,sellPrice:11.02,qty:100,pnl:-28,buyDate:'2026-01-20',sellDate:'2026-02-25',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.97,sellPrice:11.63,qty:100,pnl:66,buyDate:'2026-01-28',sellDate:'2026-02-26',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.27,sellPrice:11.12,qty:100,pnl:-115,buyDate:'2026-02-06',sellDate:'2026-02-27',reason:'止损'},
  {name:'标普油气ETF',code:'sh513350',buyPrice:1.137,sellPrice:1.261,qty:200,pnl:24.8,buyDate:'2026-02-24',sellDate:'2026-03-02',reason:'止盈'},
  {name:'标普油气ETF',code:'sh513350',buyPrice:1.145,sellPrice:1.261,qty:100,pnl:11.6,buyDate:'2026-02-27',sellDate:'2026-03-02',reason:'止盈'},
  {name:'标普油气ETF',code:'sh513350',buyPrice:1.258,sellPrice:1.373,qty:200,pnl:23,buyDate:'2026-03-02',sellDate:'2026-03-03',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.71,sellPrice:12.59,qty:100,pnl:188,buyDate:'2026-02-24',sellDate:'2026-03-03',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.72,sellPrice:12.59,qty:100,pnl:187,buyDate:'2026-02-25',sellDate:'2026-03-03',reason:'止盈'},
  {name:'标普油气ETF',code:'sh513350',buyPrice:1.258,sellPrice:1.444,qty:200,pnl:37.2,buyDate:'2026-03-02',sellDate:'2026-03-04',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.06,sellPrice:12.68,qty:100,pnl:162,buyDate:'2026-02-26',sellDate:'2026-03-04',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.85,sellPrice:12.68,qty:100,pnl:183,buyDate:'2026-02-27',sellDate:'2026-03-04',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.22,sellPrice:12.4,qty:100,pnl:18,buyDate:'2026-03-03',sellDate:'2026-03-05',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.37,sellPrice:12.4,qty:100,pnl:3,buyDate:'2026-03-03',sellDate:'2026-03-05',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.5,sellPrice:12.27,qty:200,pnl:-46,buyDate:'2026-03-05',sellDate:'2026-03-06',reason:'止损'},
  {name:'标普油气ETF',code:'sh513350',buyPrice:1.43,sellPrice:1.399,qty:100,pnl:-3.1,buyDate:'2026-03-05',sellDate:'2026-03-09',reason:'止损'},
  {name:'标普油气ETF',code:'sh513350',buyPrice:1.398,sellPrice:1.399,qty:100,pnl:0.1,buyDate:'2026-03-06',sellDate:'2026-03-09',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.85,sellPrice:11.76,qty:100,pnl:-9,buyDate:'2026-03-06',sellDate:'2026-03-10',reason:'止损'},
  {name:'标普油气ETF',code:'sh513350',buyPrice:1.398,sellPrice:1.234,qty:100,pnl:-16.4,buyDate:'2026-03-06',sellDate:'2026-03-11',reason:'止损'},
  {name:'标普油气ETF',code:'sh513350',buyPrice:1.319,sellPrice:1.234,qty:200,pnl:-17,buyDate:'2026-03-10',sellDate:'2026-03-11',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.85,sellPrice:11.41,qty:100,pnl:-44,buyDate:'2026-03-06',sellDate:'2026-03-12',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.87,sellPrice:11.18,qty:100,pnl:-69,buyDate:'2026-03-09',sellDate:'2026-03-16',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.12,sellPrice:11.34,qty:100,pnl:-78,buyDate:'2026-03-09',sellDate:'2026-03-17',reason:'止损'},
  {name:'山子高科',code:'sz000981',buyPrice:4.68,sellPrice:4.38,qty:200,pnl:-60,buyDate:'2026-03-17',sellDate:'2026-03-19',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.12,sellPrice:9.56,qty:100,pnl:-256,buyDate:'2026-03-09',sellDate:'2026-03-23',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.58,sellPrice:9.56,qty:100,pnl:-202,buyDate:'2026-03-11',sellDate:'2026-03-23',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.0,sellPrice:9.56,qty:100,pnl:-144,buyDate:'2026-03-12',sellDate:'2026-03-23',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.97,sellPrice:9.56,qty:100,pnl:-141,buyDate:'2026-03-17',sellDate:'2026-03-23',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.25,sellPrice:9.56,qty:100,pnl:-169,buyDate:'2026-03-17',sellDate:'2026-03-23',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.01,sellPrice:10.18,qty:100,pnl:17,buyDate:'2026-03-20',sellDate:'2026-03-24',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.4,sellPrice:10.18,qty:100,pnl:-22,buyDate:'2026-03-23',sellDate:'2026-03-24',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.4,sellPrice:10.51,qty:100,pnl:11,buyDate:'2026-03-23',sellDate:'2026-03-25',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.4,sellPrice:10.36,qty:100,pnl:-4,buyDate:'2026-03-23',sellDate:'2026-03-25',reason:'止损'},
  {name:'平潭发展',code:'sz000592',buyPrice:9.96,sellPrice:10.36,qty:100,pnl:40,buyDate:'2026-03-24',sellDate:'2026-03-25',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:9.96,sellPrice:11.62,qty:100,pnl:166,buyDate:'2026-03-24',sellDate:'2026-03-30',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:10.74,sellPrice:11.62,qty:100,pnl:88,buyDate:'2026-03-26',sellDate:'2026-03-30',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.0,sellPrice:11.62,qty:100,pnl:62,buyDate:'2026-03-26',sellDate:'2026-03-30',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:11.03,sellPrice:12.77,qty:100,pnl:174,buyDate:'2026-03-26',sellDate:'2026-03-31',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.15,sellPrice:12.75,qty:100,pnl:60,buyDate:'2026-04-01',sellDate:'2026-04-02',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.35,sellPrice:11.9,qty:100,pnl:-45,buyDate:'2026-04-01',sellDate:'2026-04-07',reason:'止损'},
  {name:'津药药业',code:'sh600488',buyPrice:6.96,sellPrice:7.66,qty:300,pnl:210,buyDate:'2026-04-03',sellDate:'2026-04-07',reason:'止盈'},
  {name:'平潭发展',code:'sz000592',buyPrice:12.47,sellPrice:12.27,qty:100,pnl:-20,buyDate:'2026-04-02',sellDate:'2026-04-08',reason:'止损'},
  {name:'津药药业',code:'sh600488',buyPrice:8.0,sellPrice:6.92,qty:100,pnl:-108,buyDate:'2026-04-08',sellDate:'2026-04-09',reason:'止损'},
  {name:'中安科',code:'sh600654',buyPrice:4.59,sellPrice:4.55,qty:200,pnl:-8,buyDate:'2026-04-09',sellDate:'2026-04-16',reason:'止损'},
];

/* ══════════════════════ PART 7: UI Components ══════════════════════ */
const Card=({children,style})=><div style={{background:T.card,borderRadius:16,border:`1px solid ${T.border}`,padding:16,boxShadow:'0 1px 3px rgba(0,0,0,.04)',marginBottom:10,...style}}>{children}</div>;

// ─── 候选池 Tab ───
const CandidatesTab=({onAddHolding,holdings,blacklist,onShowHistory})=>{
  const[candidates,setCandidates]=useState([]);
  const[loading,setLoading]=useState(false);
  const[regime,setRegime]=useState(null);
  const[error,setError]=useState('');
  const[lastDate,setLastDate]=useState('');
  const init=useRef(false);

  useEffect(()=>{
    if(init.current)return;init.current=true;
    (async()=>{
      const saved=await S.get('qv5-candidates',null);
      if(saved){
        if(saved.date&&saved.date!==today()){
          const arch=await S.get('qv5-cand-history',[]);
          arch.unshift(saved);
          await S.set('qv5-cand-history',arch.slice(0,30));
          await S.set('qv5-candidates',null);
          setCandidates([]);
        }else if(saved.candidates){
          setCandidates(saved.candidates);
          setRegime(saved.regime);
          setLastDate(saved.date||'');
        }
      }
    })();
  },[]);

  const refresh=async()=>{
    setLoading(true);setError('');
    try{
      const excludeCodes=[
        ...holdings.map(h=>resolveCode(h.name)).filter(Boolean),
        ...blacklist.filter(b=>b.expireDate>today()).map(b=>b.code),
      ];
      const raw=await screenStocks(excludeCodes);
      if(raw&&raw.candidates&&raw.candidates.length>0){
        setRegime(raw.market);
        setCandidates(raw.candidates);
        setLastDate(today());
        S.set('qv5-candidates',{date:today(),candidates:raw.candidates,regime:raw.market});
      }else{
        setError('今日无股票通过硬规则筛选（市场可能极端）');
      }
    }catch(e){
      setError('筛选失败：'+e.message);
    }
    setLoading(false);
  };

  const sectorDist=useMemo(()=>{
    const m={};candidates.forEach(c=>{m[c.sector]=(m[c.sector]||0)+1});return Object.entries(m);
  },[candidates]);
  const rCfg=REGIME_CFG[regime?.regime]||REGIME_CFG.range;

  return(<div>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
      <div>
        <div style={{fontSize:14,fontWeight:700}}>{today()} 候选池</div>
        {lastDate&&lastDate===today()&&<div style={{fontSize:10,color:T.tx3,marginTop:2}}>已生成 · 跨日自动归档</div>}
      </div>
      <div style={{display:'flex',gap:6,alignItems:'center'}}>
        <button onClick={onShowHistory} style={{padding:'6px 10px',borderRadius:8,border:`1px solid ${T.border}`,background:T.card,fontSize:11,color:T.tx2,cursor:'pointer'}}>📜 历史</button>
        {regime&&<span style={{fontSize:11,padding:'3px 10px',borderRadius:12,background:rCfg.c+'15',color:rCfg.c,fontWeight:700}}>{rCfg.icon}{rCfg.label}</span>}
        <button onClick={refresh} disabled={loading} style={{padding:'8px 14px',borderRadius:10,border:'none',background:loading?T.border:T.pri,color:'#fff',fontSize:13,fontWeight:700,cursor:loading?'wait':'pointer'}}>
          {loading?'筛选中...':'🔍 刷新候选'}
        </button>
      </div>
    </div>
    {error&&<div style={{background:T.upL,borderRadius:10,padding:10,fontSize:12,color:T.up,marginBottom:10}}>❌ {error}</div>}

    {loading&&<div style={{textAlign:'center',padding:'50px 20px'}}><div style={{width:32,height:32,border:`3px solid ${T.border}`,borderTopColor:T.pri,borderRadius:'50%',margin:'0 auto 12px',animation:'spin 1s linear infinite'}}/><style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style><div style={{fontSize:13,color:T.tx2}}>本地筛选中（拉取行情→应用规则→板块分散）...</div></div>}

    {!loading&&candidates.map((c,i)=>(
      <CandidateCard key={i} c={c} onAdd={()=>onAddHolding(c)} regime={rCfg}/>
    ))}

    {!loading&&sectorDist.length>0&&(
      <div style={{display:'flex',gap:6,flexWrap:'wrap',marginTop:8}}>
        {sectorDist.map(([s,n])=><span key={s} style={{fontSize:11,padding:'2px 8px',borderRadius:10,background:T.surf,color:T.tx2}}>{s} ×{n}</span>)}
      </div>
    )}

    {!loading&&candidates.length===0&&!error&&<div style={{textAlign:'center',padding:'40px 20px',color:T.tx3,fontSize:13}}>点击「刷新候选」获取今日候选池</div>}
  </div>);
};

const CandidateCard=({c,onAdd,regime})=>{
  const[showAdd,setShowAdd]=useState(false);
  const[qty,setQty]=useState(100);
  const probColor=c.winProb>=70?T.up:c.winProb>=50?T.amb:T.dn;

  return(
    <Card>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:8}}>
        <div>
          <div style={{display:'flex',alignItems:'center',gap:6}}>
            <span style={{fontSize:15,fontWeight:700}}>{c.name}</span>
            <span style={{fontSize:10,fontFamily:FM,color:T.tx3}}>{c.code}</span>
            <span style={{fontSize:10,padding:'1px 6px',borderRadius:4,background:T.surf,color:T.tx2}}>{c.sector}</span>
          </div>
          <div style={{display:'flex',alignItems:'baseline',gap:6,marginTop:3}}>
            <span style={{fontSize:20,fontWeight:800,fontFamily:FM}}>¥{c.price}</span>
            <span style={{fontSize:13,fontWeight:700,fontFamily:FM,color:upDnC(c.change)}}>{c.change>0?'+':''}{c.change}%</span>
          </div>
        </div>
        <div style={{textAlign:'center',padding:'4px 12px',borderRadius:10,background:probColor+'12',border:`1px solid ${probColor}30`}}>
          <div style={{fontSize:20,fontWeight:800,color:probColor,fontFamily:FM}}>{c.winProb}</div>
          <div style={{fontSize:9,color:T.tx3}}>/100</div>
        </div>
      </div>

      <div style={{display:'flex',gap:8,marginBottom:8,fontSize:11,color:T.tx2}}>
        <span>换手{c.turnover||'?'}%</span><span>PE{c.pe||'?'}</span><span>仓位≤{c.position}%</span>
      </div>
      <div style={{fontSize:12,color:T.tx2,lineHeight:1.6,marginBottom:6}}>💡 {c.catalyst}</div>
      <div style={{fontSize:12,color:T.amb,lineHeight:1.5,marginBottom:8}}>⚠️ {c.risk}</div>
      <div style={{display:'flex',gap:12,fontSize:11,color:T.tx3,marginBottom:10}}>
        <span>止盈+5%</span><span style={{color:T.up}}>止损-3% (¥{c.stopLoss})</span><span>持有5日</span>
      </div>

      {!showAdd&&<button onClick={()=>setShowAdd(true)} style={{width:'100%',padding:'10px',borderRadius:10,border:`1.5px solid ${T.pri}`,background:T.priL,color:T.pri,fontSize:13,fontWeight:700,cursor:'pointer'}}>加入持仓</button>}
      {showAdd&&(
        <div style={{background:T.surf,borderRadius:10,padding:12}}>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8,marginBottom:8}}>
            <div><div style={{fontSize:10,color:T.tx3,marginBottom:2}}>买入价</div>
              <div style={{fontSize:16,fontWeight:700,fontFamily:FM}}>¥{c.price}</div></div>
            <div><div style={{fontSize:10,color:T.tx3,marginBottom:2}}>数量（股）</div>
              <input type="number" value={qty} onChange={e=>setQty(+e.target.value||100)} step={100} min={100}
                style={{width:'100%',padding:'6px 8px',border:`1px solid ${T.border}`,borderRadius:6,fontSize:14,fontFamily:FM,outline:'none',boxSizing:'border-box'}}/></div>
          </div>
          <div style={{display:'flex',gap:6}}>
            <button onClick={()=>setShowAdd(false)} style={{flex:1,padding:'8px',borderRadius:8,border:`1px solid ${T.border}`,background:T.card,color:T.tx2,fontSize:12,cursor:'pointer'}}>取消</button>
            <button onClick={()=>{onAdd({...c,qty,buyPrice:c.price});setShowAdd(false)}} style={{flex:2,padding:'8px',borderRadius:8,border:'none',background:T.pri,color:'#fff',fontSize:12,fontWeight:700,cursor:'pointer'}}>确认买入 ¥{(c.price*qty).toFixed(0)}</button>
          </div>
        </div>
      )}
    </Card>
  );
};

// ─── 持仓 Tab ───
const HoldingsTab=({holdings,onSell,onStopLossAction,modal,setModal,onRefresh,lastUpdate,refreshing})=>{
  const totalPnl=holdings.reduce((s,h)=>s+h.pnl,0);
  const totalValue=holdings.reduce((s,h)=>s+(h.currentPrice||h.buyPrice)*h.qty,0);
  const totalCost=holdings.reduce((s,h)=>s+h.buyPrice*h.qty,0);
  const totalRetPct=totalCost>0?((totalValue-totalCost)/totalCost*100):0;

  return(<div>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10}}>
      <div style={{fontSize:11,color:T.tx3}}>
        {lastUpdate?`更新于 ${lastUpdate}`:'未刷新'}
        {' · 交易时段每15分钟自动刷新'}
      </div>
      <button onClick={onRefresh} disabled={refreshing} style={{padding:'5px 12px',borderRadius:8,border:`1px solid ${T.border}`,background:refreshing?T.surf:T.card,fontSize:11,fontWeight:600,color:T.pri,cursor:refreshing?'wait':'pointer'}}>
        {refreshing?'⏳ 刷新中...':'🔄 刷新行情'}
      </button>
    </div>
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr',gap:6,marginBottom:14}}>
      {[['总市值',`¥${totalValue.toFixed(0)}`,T.pri],['总投入',`¥${totalCost.toFixed(0)}`,T.tx2],['总盈亏',`${totalPnl>0?'+':''}¥${totalPnl.toFixed(0)}`,totalPnl>=0?T.up:T.dn],['总收益率',`${totalRetPct>=0?'+':''}${totalRetPct.toFixed(1)}%`,totalRetPct>=0?T.up:T.dn]].map(([l,v,c],i)=>
        <div key={i} style={{background:T.surf,borderRadius:12,padding:8,textAlign:'center'}}>
          <div style={{fontSize:9,color:T.tx3}}>{l}</div>
          <div style={{fontSize:15,fontWeight:800,color:c,fontFamily:FM}}>{v}</div>
        </div>
      )}
    </div>

    {holdings.length===0&&<div style={{textAlign:'center',padding:'40px 20px',color:T.tx3,fontSize:13}}>暂无持仓，去候选池挑选</div>}

    {holdings.sort((a,b)=>a.pnlPct-b.pnlPct).map((h,i)=>{
      const isOverdue=h.holdDays>(h.targetDays||5)+2&&h.pnl<0;
      // 本地规则建议
      const localAdvice=(()=>{
        if(h.status==='stop_loss_hit')return{advice:'清仓',reasoning:'触及止损线',urgency:'high'};
        if(isOverdue)return{advice:'评估',reasoning:'超期未盈利',urgency:'medium'};
        if(h.pnlPct>=5)return{advice:'减仓',reasoning:'达到+5%止盈位',urgency:'medium'};
        if(h.pnlPct>=3&&h.holdDays>=3)return{advice:'部分减仓',reasoning:'锁定利润',urgency:'low'};
        if(h.pnlPct<=-2)return{advice:'警惕',reasoning:'接近止损线',urgency:'medium'};
        return{advice:'持有',reasoning:'未触发条件',urgency:'low'};
      })();
      const adviceObj=h.currentPrice>0?localAdvice:null;
      return(
        <Card key={i} style={{borderLeft:`3px solid ${h.pnlPct>=0?T.up:T.dn}`,background:isOverdue?T.ambL+'40':T.card}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:6}}>
            <div>
              <div style={{display:'flex',alignItems:'center',gap:6}}>
                <span style={{fontSize:15,fontWeight:700}}>{h.name}</span>
                <span style={{fontSize:10,fontFamily:FM,color:T.tx3}}>{h.code}</span>
              </div>
              <div style={{display:'flex',gap:12,marginTop:3,fontSize:12}}>
                <span>现价 <b style={{fontFamily:FM}}>¥{h.currentPrice?h.currentPrice.toFixed(2):'—'}</b></span>
                <span style={{color:T.tx3}}>成本 <b style={{fontFamily:FM}}>¥{h.buyPrice}</b></span>
              </div>
            </div>
            <div style={{textAlign:'right'}}>
              <div style={{fontSize:18,fontWeight:800,fontFamily:FM,color:h.pnlPct>=0?T.up:T.dn}}>
                {h.pnlPct>=0?'+':''}{h.pnlPct.toFixed(2)}%
              </div>
              <div style={{fontSize:11,color:T.tx2}}>¥{h.pnl>=0?'+':''}{h.pnl.toFixed(0)}</div>
            </div>
          </div>

          <div style={{display:'flex',gap:8,marginBottom:8}}>
            {[
              ['股数',`${h.qty}股`],
              ['投入',`¥${(h.buyPrice*h.qty).toFixed(0)}`],
              ['市值',`¥${((h.currentPrice||h.buyPrice)*h.qty).toFixed(0)}`],
              ['收益率',`${h.pnlPct>=0?'+':''}${h.pnlPct.toFixed(2)}%`],
            ].map(([l,v],j)=>(
              <div key={j} style={{flex:1,background:T.surf,borderRadius:8,padding:'4px 6px',textAlign:'center'}}>
                <div style={{fontSize:9,color:T.tx3}}>{l}</div>
                <div style={{fontSize:12,fontWeight:700,fontFamily:FM,color:j===3?(h.pnlPct>=0?T.up:T.dn):T.txt}}>{v}</div>
              </div>
            ))}
          </div>

          <div style={{margin:'8px 0'}}>
            <div style={{display:'flex',justifyContent:'space-between',fontSize:10,color:T.tx3,marginBottom:2}}>
              <span>止损 ¥{h.stopLoss.toFixed(2)}</span>
              <span>目标 ¥{(h.buyPrice*1.05).toFixed(2)}</span>
            </div>
            <div style={{height:6,background:T.border,borderRadius:3,position:'relative',overflow:'hidden'}}>
              {(()=>{
                const sl=h.stopLoss,tg=h.buyPrice*1.05,cp=h.currentPrice||h.buyPrice;
                const pct=Math.max(0,Math.min(100,(cp-sl)/(tg-sl)*100));
                return <div style={{width:`${pct}%`,height:'100%',borderRadius:3,background:pct<20?T.up:pct>80?T.dn:T.amb}}/>;
              })()}
            </div>
          </div>

          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:6}}>
            <span style={{fontSize:12,color:isOverdue?T.up:T.tx2}}>
              持有{h.holdDays}日/目标{h.targetDays||5}日{isOverdue&&' ⚠️超期'}
            </span>
            <button onClick={()=>onSell(h)} style={{padding:'6px 14px',borderRadius:8,border:`1px solid ${T.dn}`,background:T.dnL,color:T.dn,fontSize:11,fontWeight:700,cursor:'pointer'}}>
              手动卖出
            </button>
          </div>

          {adviceObj&&(
            <div style={{background:T.surf,borderRadius:8,padding:'8px 10px',fontSize:12,color:T.tx2,lineHeight:1.5}}>
              <span style={{fontWeight:700,color:adviceObj.urgency==='high'?T.up:T.pri}}>{adviceObj.advice}</span> {adviceObj.reasoning}
            </div>
          )}
        </Card>
      );
    })}

    {modal&&<StopLossModal h={modal} onAction={onStopLossAction} onClose={()=>setModal(null)}/>}
  </div>);
};

const StopLossModal=({h,onAction,onClose})=>{
  const[reason,setReason]=useState('');
  return(
    <div style={{position:'fixed',top:0,left:0,right:0,bottom:0,background:'rgba(220,38,38,.15)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:999,padding:20}}>
      <div style={{background:T.card,borderRadius:20,padding:24,maxWidth:400,width:'100%',boxShadow:'0 20px 60px rgba(0,0,0,.2)'}}>
        <div style={{textAlign:'center',marginBottom:16}}>
          <div style={{fontSize:36,marginBottom:8}}>🚨</div>
          <div style={{fontSize:18,fontWeight:800,color:T.up}}>止损触发</div>
          <div style={{fontSize:14,color:T.tx2,marginTop:4}}>{h.name} ¥{h.currentPrice?.toFixed(2)}</div>
          <div style={{fontSize:13,color:T.up,marginTop:4}}>跌至止损线 ¥{h.stopLoss.toFixed(2)} | 亏损 ¥{Math.abs(h.pnl).toFixed(0)}</div>
        </div>
        <button onClick={()=>onAction('sell',h)} style={{width:'100%',padding:'14px',borderRadius:12,border:'none',background:T.up,color:'#fff',fontSize:15,fontWeight:800,cursor:'pointer',marginBottom:8}}>
          立即清仓（建议）
        </button>
        <div style={{marginBottom:8}}>
          <button onClick={()=>{if(reason.length>=10)onAction('lower',h,reason);else alert('理由不少于10字')}} style={{width:'100%',padding:'12px',borderRadius:12,border:`1.5px solid ${T.amb}`,background:T.ambL,color:T.amb,fontSize:13,fontWeight:700,cursor:'pointer'}}>
            下调止损至-5%继续持有
          </button>
          <input value={reason} onChange={e=>setReason(e.target.value)} placeholder="为什么下调？（≥10字，记违规）"
            style={{width:'100%',marginTop:6,padding:'8px 10px',border:`1px solid ${T.border}`,borderRadius:8,fontSize:12,outline:'none',boxSizing:'border-box',fontFamily:FF}}/>
        </div>
        <button onClick={()=>onAction('manual',h)} style={{width:'100%',padding:'12px',borderRadius:12,border:`1px solid ${T.border}`,background:T.card,color:T.tx2,fontSize:13,cursor:'pointer'}}>
          我已手动卖出
        </button>
      </div>
    </div>
  );
};

// ─── 复盘 Tab ───
const ReviewTab=({history,blacklist,onForceUnban,holdings})=>{
  const[review,setReview]=useState(null);
  const[reviewLoading,setReviewLoading]=useState(false);

  const monthStats=useMemo(()=>{
    const monthStart=today().slice(0,7)+'-01';
    const mh=history.filter(h=>h.sellDate>=monthStart);
    const wins=mh.filter(h=>h.pnl>0),losses=mh.filter(h=>h.pnl<0);
    const avgWin=wins.length?wins.reduce((s,h)=>s+h.pnl,0)/wins.length:0;
    const avgLoss=losses.length?Math.abs(losses.reduce((s,h)=>s+h.pnl,0)/losses.length):0;
    let maxConsecLoss=0,cur=0;
    mh.sort((a,b)=>a.sellDate.localeCompare(b.sellDate)).forEach(h=>{if(h.pnl<0){cur++;maxConsecLoss=Math.max(maxConsecLoss,cur)}else cur=0});
    return{count:mh.length,wr:mh.length?wins.length/mh.length:0,total:mh.reduce((s,h)=>s+h.pnl,0),
      avgWin,avgLoss,profitFactor:avgLoss>0?avgWin/avgLoss:0,maxConsecLoss};
  },[history]);

  const stockPnl=useMemo(()=>{
    const m={};history.forEach(h=>{m[h.name]=(m[h.name]||0)+h.pnl});
    return Object.entries(m).sort((a,b)=>a[1]-b[1]).slice(0,8);
  },[history]);

  const weekStart=addDays(today(),-7);
  const weekTrades=history.filter(h=>h.sellDate>=weekStart).length;
  const monthTrades=monthStats.count;

  // 本地复盘（不调 AI）
  const runReview=async()=>{
    setReviewLoading(true);
    const t=today();
    const todayTrades=history.filter(h=>h.sellDate===t);
    const todayPnl=todayTrades.reduce((s,h)=>s+(h.pnl||0),0);
    const floatPnl=holdings.reduce((s,h)=>s+(h.pnl||0),0);

    const advice=[];
    if(floatPnl<-500)advice.push('持仓浮亏较大，明日优先评估止损');
    if(holdings.length===0)advice.push('当前空仓，明日关注候选池');
    if(monthTrades>20)advice.push(`本月已交易${monthTrades}笔，频次过高需克制`);
    if(monthStats.wr<0.4&&monthTrades>=5)advice.push(`本月胜率${(monthStats.wr*100).toFixed(0)}%偏低，检查入场标准`);
    if(monthStats.profitFactor<1&&monthTrades>=5)advice.push(`盈亏比${monthStats.profitFactor.toFixed(2)}<1，赚少亏多需修正`);
    if(advice.length===0)advice.push('继续保持纪律，等待明日候选');

    const reviewText=`今日完成${todayTrades.length}笔交易，今日盈亏 ¥${todayPnl>0?'+':''}${todayPnl.toFixed(0)}。当前持仓${holdings.length}只，浮动盈亏 ¥${floatPnl>0?'+':''}${floatPnl.toFixed(0)}。本月累计${monthTrades}笔，胜率${(monthStats.wr*100).toFixed(0)}%，盈亏比${monthStats.profitFactor.toFixed(2)}。`;

    setReview({review:reviewText,tomorrow:advice});
    setReviewLoading(false);
  };

  const colorIf=(v,g,y)=>v>=g?T.dn:v>=y?T.amb:T.up;

  return(<div>
    {(weekTrades>5||monthTrades>20)&&(
      <div style={{background:monthTrades>20?T.upL:T.ambL,borderRadius:10,padding:'8px 12px',fontSize:12,color:monthTrades>20?T.up:T.amb,fontWeight:600,marginBottom:12}}>
        ⚠️ {monthTrades>20?`本月已交易${monthTrades}笔 > 20笔，过度交易！`:`本周已交易${weekTrades}笔 > 5笔`}
      </div>
    )}

    <Card>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10}}>
        <div style={{fontSize:14,fontWeight:700}}>📋 当日复盘</div>
        <button onClick={runReview} disabled={reviewLoading} style={{padding:'6px 14px',borderRadius:8,border:'none',background:T.pri,color:'#fff',fontSize:12,fontWeight:700,cursor:reviewLoading?'wait':'pointer'}}>
          {reviewLoading?'生成中...':'生成复盘'}
        </button>
      </div>
      {review?(
        <div>
          <div style={{fontSize:13,color:T.tx2,lineHeight:1.7,marginBottom:10}}>{review.review}</div>
          {review.tomorrow&&<div style={{background:T.surf,borderRadius:10,padding:12}}>
            <div style={{fontSize:12,fontWeight:700,color:T.txt,marginBottom:6}}>明日要点</div>
            {review.tomorrow.map((t,i)=><div key={i} style={{fontSize:12,color:T.tx2,lineHeight:1.6}}>• {t}</div>)}
          </div>}
        </div>
      ):<div style={{fontSize:12,color:T.tx3}}>15:30后点击「生成复盘」</div>}
    </Card>

    <Card>
      <div style={{fontSize:14,fontWeight:700,marginBottom:10}}>📊 本月统计</div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:8,marginBottom:12}}>
        {[
          ['交易频次',`${monthStats.count}笔`,colorIf(20-monthStats.count,0,-10)],
          ['胜率',`${(monthStats.wr*100).toFixed(0)}%`,colorIf(monthStats.wr,.5,.4)],
          ['盈亏比',monthStats.profitFactor.toFixed(1),colorIf(monthStats.profitFactor,1.3,1)],
          ['累计',`¥${monthStats.total>0?'+':''}${monthStats.total.toFixed(0)}`,monthStats.total>=0?T.up:T.dn],
          ['最大连亏',`${monthStats.maxConsecLoss}次`,monthStats.maxConsecLoss<=2?T.dn:T.up],
          ['平均盈亏',`${monthStats.avgWin>0?'+':''}¥${monthStats.avgWin.toFixed(0)}/-¥${monthStats.avgLoss.toFixed(0)}`,T.tx2],
        ].map(([l,v,c],i)=>
          <div key={i} style={{background:T.surf,borderRadius:10,padding:10,textAlign:'center'}}>
            <div style={{fontSize:10,color:T.tx3}}>{l}</div>
            <div style={{fontSize:15,fontWeight:800,color:c,fontFamily:FM}}>{v}</div>
          </div>
        )}
      </div>

      {stockPnl.length>0&&(
        <div>
          <div style={{fontSize:12,fontWeight:600,color:T.tx2,marginBottom:6}}>每股累计盈亏</div>
          {stockPnl.map(([name,pnl],i)=>(
            <div key={i} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'4px 0',borderBottom:`1px solid ${T.border}22`}}>
              <span style={{fontSize:12,fontWeight:600}}>{name}</span>
              <div style={{display:'flex',alignItems:'center',gap:6}}>
                <span style={{fontSize:13,fontWeight:700,fontFamily:FM,color:pnl>=0?T.up:T.dn}}>¥{pnl>=0?'+':''}{pnl.toFixed(0)}</span>
                {pnl<-200&&<span style={{fontSize:9,padding:'1px 5px',borderRadius:3,background:T.upL,color:T.up}}>⚠️死磕股</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>

    <Card>
      <div style={{fontSize:14,fontWeight:700,marginBottom:10}}>🚫 黑名单</div>
      {blacklist.filter(b=>b.expireDate&&b.expireDate>today()).length===0&&<div style={{fontSize:12,color:T.tx3}}>当前无黑名单股票</div>}
      {blacklist.filter(b=>b.expireDate&&b.expireDate>today()).map((b,i)=>(
        <div key={i} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 0',borderBottom:`1px solid ${T.border}22`}}>
          <div>
            <span style={{fontSize:13,fontWeight:600}}>{b.name}</span>
            <span style={{fontSize:10,color:T.tx3,marginLeft:6}}>{b.code}</span>
            <div style={{fontSize:11,color:T.tx2}}>{b.reason} · 解禁{b.expireDate}</div>
          </div>
          <button onClick={()=>onForceUnban(b)} style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${T.amb}`,background:T.ambL,color:T.amb,fontSize:10,fontWeight:700,cursor:'pointer'}}>
            强制解禁
          </button>
        </div>
      ))}
    </Card>
  </div>);
};

// ─── 历史候选池 Modal ───
const CandidatesHistoryModal=({onClose})=>{
  const[arch,setArch]=useState([]);
  useEffect(()=>{S.get('qv5-cand-history',[]).then(setArch)},[]);
  return(
    <div style={{position:'fixed',top:0,left:0,right:0,bottom:0,background:'rgba(0,0,0,.4)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:999,padding:16}}>
      <div style={{background:T.card,borderRadius:16,padding:18,maxWidth:560,width:'100%',maxHeight:'85vh',overflowY:'auto'}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14}}>
          <div style={{fontSize:15,fontWeight:700}}>📜 历史候选池</div>
          <button onClick={onClose} style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${T.border}`,background:T.card,fontSize:12,cursor:'pointer'}}>关闭</button>
        </div>
        {arch.length===0&&<div style={{textAlign:'center',padding:'40px 20px',color:T.tx3,fontSize:13}}>还没有历史候选池<br/><span style={{fontSize:11}}>每天生成的候选池会在跨日后自动归档到这里</span></div>}
        {arch.map((day,i)=>{
          const wins=day.candidates?.filter(c=>c.winProb>=70).length||0;
          const sectors=[...new Set((day.candidates||[]).map(c=>c.sector))];
          const r=REGIME_CFG[day.regime?.regime]||REGIME_CFG.range;
          return(
            <div key={i} style={{borderLeft:`3px solid ${r.c}`,paddingLeft:12,marginBottom:14}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:6}}>
                <div style={{fontSize:13,fontWeight:700}}>{day.date} <span style={{fontSize:10,color:r.c,marginLeft:6}}>{r.icon}{r.label}</span></div>
                <div style={{fontSize:11,color:T.tx3}}>{day.candidates?.length||0}支 · 高信号{wins}支</div>
              </div>
              <div style={{fontSize:11,color:T.tx3,marginBottom:6}}>板块：{sectors.join('、')}</div>
              {day.candidates?.map((c,j)=>(
                <div key={j} style={{display:'flex',justifyContent:'space-between',padding:'4px 8px',background:T.surf,borderRadius:6,marginBottom:3,fontSize:11}}>
                  <span style={{fontWeight:600}}>{c.name} <span style={{color:T.tx3,fontFamily:FM,fontSize:10}}>{c.code}</span></span>
                  <span style={{display:'flex',gap:8}}>
                    <span style={{fontFamily:FM}}>¥{c.price}</span>
                    <span style={{color:c.winProb>=70?T.up:c.winProb>=50?T.amb:T.dn,fontWeight:700,fontFamily:FM}}>{c.winProb}</span>
                    <span style={{color:T.tx3,fontSize:10}}>{c.sector}</span>
                  </span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ─── 卖出 Modal ───
const SellModal=({h,onConfirm,onCancel})=>{
  const[price,setPrice]=useState(h.currentPrice||h.buyPrice);
  return(
    <div style={{position:'fixed',top:0,left:0,right:0,bottom:0,background:'rgba(0,0,0,.3)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:999,padding:20}}>
      <div style={{background:T.card,borderRadius:20,padding:24,maxWidth:360,width:'100%'}}>
        <div style={{fontSize:16,fontWeight:700,marginBottom:12}}>卖出 {h.name}</div>
        <div style={{marginBottom:12}}>
          <div style={{fontSize:12,color:T.tx3,marginBottom:4}}>卖出价格</div>
          <input type="number" value={price} onChange={e=>setPrice(+e.target.value)} step={0.01}
            style={{width:'100%',padding:'10px',border:`1.5px solid ${T.border}`,borderRadius:10,fontSize:16,fontFamily:FM,outline:'none',boxSizing:'border-box'}}/>
        </div>
        <div style={{fontSize:12,color:T.tx2,marginBottom:16}}>
          {h.qty}股 × ¥{price} = ¥{(h.qty*price).toFixed(0)} | 盈亏 ¥{((price-h.buyPrice)*h.qty).toFixed(0)}
        </div>
        <div style={{display:'flex',gap:8}}>
          <button onClick={onCancel} style={{flex:1,padding:'11px',borderRadius:10,border:`1px solid ${T.border}`,background:T.card,color:T.tx2,fontSize:13,cursor:'pointer'}}>取消</button>
          <button onClick={()=>onConfirm(h,price)} style={{flex:2,padding:'11px',borderRadius:10,border:'none',background:T.dn,color:'#fff',fontSize:13,fontWeight:700,cursor:'pointer'}}>确认卖出</button>
        </div>
      </div>
    </div>
  );
};

/* ══════════════════════ PART 8: App ══════════════════════ */
export default function App(){
  const[tab,setTab]=useState('candidates');
  const[holdings,setHoldings]=useState([]);
  const[blacklist,setBlacklist]=useState([]);
  const[history,setHistory]=useState([]);
  const[modal,setModal]=useState(null);
  const[sellModal,setSellModal]=useState(null);
  const[lastUpdate,setLastUpdate]=useState('');
  const[shownStopLoss,setShownStopLoss]=useState({});
  const[showCandHistory,setShowCandHistory]=useState(false);
  const[refreshing,setRefreshing]=useState(false);
  const init=useRef(false);

  useEffect(()=>{
    if(init.current)return;init.current=true;
    (async()=>{
      const ver=await S.get('qv6-version','');
      const needReinit=ver!=='6.0';
      let h=needReinit?null:await S.get('qv5-holdings',null);
      if(!h||h.length===0){h=INIT_HOLDINGS;await S.set('qv5-holdings',h)}
      setHoldings(h);
      let bl=needReinit?null:await S.get('qv5-blacklist',null);
      if(!bl||bl.length===0){bl=INIT_BLACKLIST;await S.set('qv5-blacklist',bl)}
      setBlacklist(bl);
      let hist=needReinit?null:await S.get('qv5-history',null);
      if(!hist||hist.length===0){hist=INIT_HISTORY;await S.set('qv5-history',hist)}
      setHistory(hist);
      if(needReinit)await S.set('qv6-version','6.0');
    })();
  },[]);

  const refreshHoldings=async()=>{
    if(!holdings.length||refreshing)return;
    setRefreshing(true);
    try{
      const codeMap={};holdings.forEach(h=>{const c=resolveCode(h.name);if(c)codeMap[c]=h.name});
      const codes=Object.keys(codeMap);
      if(!codes.length){setRefreshing(false);return}

      const resp=await fetch(`${PROXY_URL}/quote?code=${codes.join(',')}`);
      if(!resp.ok)throw new Error(`HTTP ${resp.status}`);
      const json=await resp.json();
      if(!json.ok||!json.data)throw new Error('Worker返回格式错误');

      const upd=holdings.map(h=>{
        const code=resolveCode(h.name);
        const q=json.data[code];
        if(!q||!q.price)return h;
        const cp=q.price;
        let status='normal';
        if(cp<=h.stopLoss)status='stop_loss_hit';
        else if(daysBetween(h.buyDate,today())>(h.targetDays||5)+2&&cp<h.buyPrice)status='overdue';
        return{...h,currentPrice:cp,status,
          pnl:(cp-h.buyPrice)*h.qty,
          pnlPct:(cp/h.buyPrice-1)*100,
          holdDays:daysBetween(h.buyDate,today())};
      });
      setHoldings(upd);await S.set('qv5-holdings',upd);
      setLastUpdate(new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}));
      const hit=upd.find(h=>h.status==='stop_loss_hit'&&!shownStopLoss[h.code]);
      if(hit){setModal(hit);setShownStopLoss(p=>({...p,[hit.code]:true}));setTab('holdings')}
    }catch(e){
      console.error('Worker fetch失败：',e);
      alert(`持仓刷新失败：${e.message}\n\n打开F12 → Network看请求详情。`);
    }
    setRefreshing(false);
  };

  const isTradingHours=()=>{const h=new Date().getHours(),m=new Date().getMinutes();const t=h*60+m;return t>=555&&t<=915};

  useEffect(()=>{
    if(!holdings.length)return;
    refreshHoldings();
    const iv=setInterval(()=>{if(isTradingHours())refreshHoldings()},15*60*1000);
    return()=>clearInterval(iv);
  },[holdings.length]);

  const closePosition=async(h,sellPrice,reason)=>{
    const pnl=(sellPrice-h.buyPrice)*h.qty;
    const entry={...h,sellPrice,sellDate:today(),pnl:parseFloat(pnl.toFixed(2)),reason};
    const newHist=[...history,entry];setHistory(newHist);await S.set('qv5-history',newHist);
    const newHoldings=holdings.filter(x=>x.code!==h.code||x.buyDate!==h.buyDate);
    setHoldings(newHoldings);await S.set('qv5-holdings',newHoldings);
    if(pnl<0){
      const bl=[...blacklist];
      const found=bl.find(b=>b.code===h.code);
      if(found){found.lossCount+=1;if(found.lossCount>=2){found.expireDate=addDays(today(),30);found.reason=`连亏${found.lossCount}次`}}
      else bl.push({name:h.name,code:h.code,lossCount:1,expireDate:null,reason:'首次亏损'});
      setBlacklist(bl);await S.set('qv5-blacklist',bl);
    }
  };

  const addHolding=async(c)=>{
    const h={name:c.name,code:c.code||resolveCode(c.name)||'',buyPrice:c.buyPrice||c.price,qty:c.qty||100,
      buyDate:today(),stopLoss:(c.buyPrice||c.price)*0.97,targetDays:5,
      currentPrice:c.price||0,pnl:0,pnlPct:0,holdDays:0,status:'normal',advice:''};
    const next=[...holdings,h];setHoldings(next);await S.set('qv5-holdings',next);
    setTab('holdings');
  };

  const handleStopLossAction=async(action,h,reason)=>{
    if(action==='sell'){await closePosition(h,h.currentPrice,'止损')}
    else if(action==='lower'){
      const upd=holdings.map(x=>(x.code===h.code&&x.buyDate===h.buyDate)?{...x,stopLoss:x.buyPrice*0.95,status:'normal'}:x);
      setHoldings(upd);await S.set('qv5-holdings',upd);
      const disc=await S.get('qv5-discipline',[]);
      disc.push({type:'lower_stop',code:h.code,name:h.name,reason,date:today()});
      await S.set('qv5-discipline',disc);
    }else{await closePosition(h,h.currentPrice,'手动卖出')}
    setModal(null);
  };

  const handleSell=(h)=>setSellModal(h);
  const confirmSell=async(h,price)=>{await closePosition(h,price,'手动卖出');setSellModal(null)};

  const forceUnban=async(b)=>{
    const reason=prompt(`为什么要解禁${b.name}？（≥10字）`);
    if(!reason||reason.length<10){alert('理由不少于10字');return}
    if(!confirm(`确认？${b.name}已让你累计亏损。`))return;
    const next=blacklist.filter(x=>x.code!==b.code);
    setBlacklist(next);await S.set('qv5-blacklist',next);
    const disc=await S.get('qv5-discipline',[]);
    disc.push({type:'force_unban',code:b.code,name:b.name,reason,date:today()});
    await S.set('qv5-discipline',disc);
  };

  const tabs=[['candidates','📊','候选池'],['holdings','💼','持仓'],['review','📈','复盘']];

  return(
    <div style={{fontFamily:FF,background:T.bg,color:T.txt,minHeight:'100vh',maxWidth:640,margin:'0 auto'}}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>

      <div style={{padding:'16px 20px 10px',borderBottom:`1px solid ${T.border}`,background:'linear-gradient(180deg,#fff,#faf9f7)'}}>
        <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:10}}>
          <div style={{width:34,height:34,borderRadius:10,background:`linear-gradient(135deg,${T.pri},${T.priD})`,display:'flex',alignItems:'center',justifyContent:'center',fontSize:16,fontWeight:900,color:'#fff'}}>Q</div>
          <div style={{flex:1}}>
            <h1 style={{margin:0,fontSize:17,fontWeight:800}}>A股量化助手 <span style={{fontSize:10,color:T.tx3,fontWeight:400}}>v6.0</span></h1>
          </div>
          {holdings.length>0&&<div style={{fontSize:11,color:T.tx3,fontFamily:FM}}>{holdings.length}只持仓</div>}
        </div>
        <div style={{display:'flex',gap:0}}>
          {tabs.map(([id,ic,lb])=>(
            <button key={id} onClick={()=>setTab(id)} style={{
              flex:1,padding:'10px 0',fontSize:13,fontWeight:tab===id?700:500,cursor:'pointer',
              border:'none',borderBottom:`2px solid ${tab===id?T.pri:'transparent'}`,
              background:'transparent',color:tab===id?T.pri:T.tx2,fontFamily:FF,
              display:'flex',alignItems:'center',justifyContent:'center',gap:5,
            }}><span style={{fontSize:15}}>{ic}</span>{lb}</button>
          ))}
        </div>
      </div>

      <div style={{padding:'14px 20px 40px'}}>
        {tab==='candidates'&&<CandidatesTab onAddHolding={addHolding} holdings={holdings} blacklist={blacklist} onShowHistory={()=>setShowCandHistory(true)}/>}
        {tab==='holdings'&&<HoldingsTab holdings={holdings} onSell={handleSell} onStopLossAction={handleStopLossAction} modal={modal} setModal={setModal} onRefresh={refreshHoldings} lastUpdate={lastUpdate} refreshing={refreshing}/>}
        {tab==='review'&&<ReviewTab history={history} blacklist={blacklist} onForceUnban={forceUnban} holdings={holdings}/>}
      </div>

      {sellModal&&<SellModal h={sellModal} onConfirm={confirmSell} onCancel={()=>setSellModal(null)}/>}
      {showCandHistory&&<CandidatesHistoryModal onClose={()=>setShowCandHistory(false)}/>}
    </div>
  );
}
