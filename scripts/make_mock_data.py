"""Create deterministic, entirely synthetic customer-360 dashboard CSVs."""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
RNG = random.Random(360)
TODAY = date(2026, 10, 22)


def write_csv(name: str, rows: list[dict]) -> None:
    path = OUT / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


customers = []
names = ["김*서", "이*훈", "박*연", "최*민", "정*희", "강*우", "조*은", "윤*석", "장*아", "임*준"]
segments = ["프리미어", "골드", "골드", "프리미어", "실버", "골드", "실버", "프리미어", "골드", "실버"]
risks = ["위험중립형", "적극투자형", "안정추구형", "공격투자형", "안정형", "위험중립형", "안정추구형", "적극투자형", "위험중립형", "안정형"]
goals = ["은퇴 준비", "자산 증식", "주택 자금", "자산 증식", "교육 자금", "은퇴 준비", "현금흐름", "상속·증여", "자산 증식", "교육 자금"]
for i in range(10):
    customers.append({
        "customer_id": f"C{1001+i}", "name_masked": names[i], "segment": segments[i],
        "risk_profile": risks[i], "branch": ["강남", "여의도", "판교"][i % 3],
        "manager": f"PB {chr(65+i)}", "join_date": str(TODAY - timedelta(days=900 + i * 317)),
        "aum": 180_000_000 + i * 92_000_000, "aum_change": round(RNG.uniform(-3, 7), 1),
        "churn_risk": [28, 72, 61, 24, 48, 83, 65, 32, 57, 76][i],
        "health_score": [82, 48, 59, 88, 68, 41, 54, 85, 63, 46][i],
        "volatility": round(RNG.uniform(5.5, 16.5), 1), "mdd": round(RNG.uniform(4, 19), 1),
        "sharpe": round(RNG.uniform(0.45, 1.5), 2), "var_95": round(RNG.uniform(2, 8), 1),
        "turnover": round(RNG.uniform(0.5, 4.0), 1), "wallet_share": RNG.randint(24, 75),
        "investment_goal": goals[i], "investment_horizon": ["3년", "5년", "10년 이상"][i % 3],
        "marketing_consent": "동의" if i % 4 else "미동의",
        "profile_updated": str(TODAY - timedelta(days=30 + i * 19)),
        "login_days": RNG.randint(2, 23), "digital_interest": ["채권 금리", "연금", "해외 주식", "배당 ETF"][i % 4],
    })
write_csv("customers", customers)

products = [
    {"product_id": "P01", "name": "국내 우량주 바스켓", "category": "주식", "risk_grade": 4},
    {"product_id": "P02", "name": "글로벌 인덱스 펀드", "category": "펀드", "risk_grade": 3},
    {"product_id": "P03", "name": "국공채 3년", "category": "채권", "risk_grade": 2},
    {"product_id": "P04", "name": "우량 회사채", "category": "채권", "risk_grade": 3},
    {"product_id": "P05", "name": "예수금", "category": "예탁", "risk_grade": 1},
    {"product_id": "P06", "name": "멀티에셋 인컴 펀드", "category": "펀드", "risk_grade": 3},
    {"product_id": "P07", "name": "원금 비보장형 ELS", "category": "파생", "risk_grade": 5},
    {"product_id": "P08", "name": "미국 국채 ETF", "category": "채권", "risk_grade": 3},
    {"product_id": "P09", "name": "배당 성장 ETF", "category": "주식", "risk_grade": 4},
    {"product_id": "P10", "name": "단기채 펀드", "category": "펀드", "risk_grade": 2},
]
write_csv("products", products)

accounts, holdings = [], []
for i, customer in enumerate(customers):
    total = customer["aum"]
    for j, account_type in enumerate(["종합매매", "연금저축", "CMA"]):
        amount = int(total * [0.58, 0.27, 0.15][j])
        accounts.append({"account_id": f"A{i+1:02d}{j+1}", "customer_id": customer["customer_id"], "type": account_type, "balance": amount, "eval_amount": amount})
    for j in range(4):
        amount = int(total * RNG.uniform(0.08, 0.34))
        maturity = TODAY + timedelta(days=RNG.randint(5, 900)) if j == 0 else ""
        holdings.append({
            "holding_id": f"H{i+1:02d}{j+1}", "customer_id": customer["customer_id"],
            "product_id": products[(i + j) % len(products)]["product_id"], "amount": amount,
            "pnl": int(amount * RNG.uniform(-0.08, 0.13)), "maturity_date": str(maturity),
        })
write_csv("accounts", accounts)
write_csv("holdings", holdings)

transactions = []
channels = ["MTS", "HTS", "영업점", "모바일"]
for i in range(600):
    customer = customers[i % 10]
    tx_date = TODAY - timedelta(days=RNG.randint(0, 365))
    transactions.append({
        "tx_id": f"T{i+1:05d}", "customer_id": customer["customer_id"], "date": str(tx_date),
        "type": RNG.choice(["매수", "매도", "입금", "출금"]), "amount": RNG.randint(100_000, 20_000_000),
        "channel": RNG.choice(channels),
    })
write_csv("transactions", transactions)

consultations = []
topics = ["자산배분", "연금 상담", "만기 안내", "시장 변동 문의", "수수료 문의", "계좌 관리"]
for i in range(120):
    customer = customers[i % 10]
    consultations.append({
        "consult_id": f"CS{i+1:04d}", "customer_id": customer["customer_id"],
        "date": str(TODAY - timedelta(days=RNG.randint(0, 240))),
        "channel": RNG.choice(["챗봇", "콜센터", "지점"]), "topic_code": RNG.choice(topics),
        "resolved": RNG.choice([True, True, True, False]), "csat": RNG.randint(2, 5),
        "summary_masked": RNG.choice(["분산 투자 방향 문의 및 후속 자료 전달 예정.", "연금 계좌 운용 현황 확인 요청.", "시장 변동에 따른 보유자산 설명 진행.", "만기 일정과 현금흐름 계획 상담."]),
    })
write_csv("consultations", consultations)

chatbot_logs = [
    {
        "log_id": f"CB{i+1:04d}", "customer_id": customers[i % 10]["customer_id"],
        "date": str(TODAY - timedelta(days=RNG.randint(0, 120))),
        "intent_code": RNG.choice(["상품정보", "잔고조회", "연금", "시장정보"]),
        "escalated": RNG.choice([True, False, False]),
    }
    for i in range(200)
]
write_csv("chatbot_logs", chatbot_logs)

market_series = []
for index_code, start, drift in [("KOSPI", 2600, 1.2), ("S&P500", 5200, 2.3), ("국고채3년", 3.2, -0.001)]:
    close = start
    for day in range(500):
        close = max(0.1, close + RNG.gauss(drift, 13 if index_code != "국고채3년" else 0.025))
        market_series.append({"date": str(TODAY - timedelta(days=499-day)), "index_code": index_code, "close": round(close, 2)})
write_csv("market_series", market_series)

news = [
    {"news_id": f"N{i+1:03d}", "date": str(TODAY - timedelta(days=i * 2)), "tag": tag,
     "sentiment": sentiment, "title_masked": title, "source": "리서치센터"}
    for i, (tag, sentiment, title) in enumerate([
        ("금리", "중립", "주요국 금리 경로와 채권 시장 점검"),
        ("주식", "긍정", "글로벌 기업 실적 전망 업데이트"),
        ("환율", "주의", "환율 변동성 확대 구간의 리스크 관리"),
        ("연금", "긍정", "장기 투자 관점의 연금 자산배분"),
        ("채권", "중립", "우량 채권 수급과 만기 전략"),
        ("국내시장", "중립", "국내 증시 주간 전략 브리핑"),
    ])
]
write_csv("news", news)

house_view = []
for i, (asset, outlook, headline) in enumerate([
    ("주식", "중립", "실적과 변동성 균형 확인"),
    ("채권", "과중", "우량 채권의 분산 효과 주목"),
    ("펀드", "중립", "비용과 기초자산 구성 점검"),
    ("예탁", "과소", "투자 대기자금 비중 관리"),
    ("파생", "과소", "위험 성향과 손실 가능성 우선 확인"),
]):
    house_view.append({"report_id": f"HV{i+1:02d}", "date": str(TODAY - timedelta(days=i * 3)), "asset_class": asset, "outlook": outlook, "headline": headline, "report_name": "주간 자산배분 전략"})
write_csv("house_view", house_view)

allocation = []
for segment in ["프리미어", "골드", "실버"]:
    weights = {"프리미어": [35, 30, 20, 10, 5], "골드": [30, 30, 22, 13, 5], "실버": [22, 28, 25, 20, 5]}[segment]
    for asset, weight in zip(["주식", "채권", "펀드", "예탁", "파생"], weights):
        allocation.append({"segment": segment, "asset_class": asset, "target_pct": weight})
write_csv("allocation_strategy", allocation)

nba_catalog = [
    {"nba_id": "NBA01", "trigger_type": "maturity", "trigger_cond": "만기 30일 이내", "action": "만기 자금 운용 계획 확인", "template": "만기상담"},
    {"nba_id": "NBA02", "trigger_type": "churn", "trigger_cond": "이탈 위험 55점 이상", "action": "선제적 관계 케어", "template": "케어콜"},
    {"nba_id": "NBA03", "trigger_type": "allocation", "trigger_cond": "목표 비중 점검 필요", "action": "자산배분 리뷰", "template": "포트폴리오리뷰"},
    {"nba_id": "NBA04", "trigger_type": "profile", "trigger_cond": "프로파일 최신화 필요", "action": "투자정보 최신화", "template": "정보확인"},
    {"nba_id": "NBA05", "trigger_type": "digital", "trigger_cond": "관심 시그널 감지", "action": "관심 주제 자료 안내", "template": "관심자료"},
    {"nba_id": "NBA06", "trigger_type": "market", "trigger_cond": "하우스뷰 변경", "action": "시장 영향도 상담", "template": "시장브리핑"},
]
write_csv("nba_catalog", nba_catalog)

nba_history = [
    {"nba_run_id": f"NH{i+1:03d}", "customer_id": customers[i % 10]["customer_id"],
     "nba_id": nba_catalog[i % len(nba_catalog)]["nba_id"],
     "date": str(TODAY - timedelta(days=RNG.randint(0, 180))),
     "status": RNG.choice(["제안", "약정", "보류", "거절"])}
    for i in range(40)
]
write_csv("nba_history", nba_history)

print(f"Wrote {len(list(OUT.glob('*.csv')))} synthetic CSV datasets to {OUT}")
