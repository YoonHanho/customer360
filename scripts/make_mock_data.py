"""Generate deterministic, entirely synthetic customer-360 dashboard CSVs."""

from __future__ import annotations

import csv
import math
import random
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
RNG = random.Random(360)
TODAY = date(2026, 10, 1)
CUSTOMER_IDS = [str(12345678 + index) for index in range(10)]
ASSET_CLASSES = ["국내주식", "해외주식", "ETF", "펀드", "채권", "기타"]
TRADE_ASSET_CLASSES = ASSET_CLASSES[:-1]
PREDICTION_TOPICS = [
    "국내주식", "해외주식", "ETF", "IRP", "ISA", "DC", "ELS", "랩어카운트",
    "개인연금", "개인투자용국채", "채권", "로보어드바이저", "펀드", "순입금",
    "순출금", "이탈",
]
PRODUCT_NAMES = {
    "국내주식": ["삼성전자", "SK하이닉스", "현대차", "NAVER", "KB금융", "삼성전자우"],
    "해외주식": ["애플", "마이크로소프트", "엔비디아", "아마존", "코카콜라", "테슬라"],
    "ETF": ["KODEX 200", "TIGER 미국S&P500", "ACE 미국나스닥100", "KODEX 배당가치", "TIGER 단기채권"],
    "펀드": ["글로벌 배당주 펀드", "인덱스 성장 펀드", "아시아 채권 펀드", "멀티에셋 인컴 펀드"],
    "채권": ["국고채 3년", "국고채 5년", "우량 회사채", "특수채 2년"],
    "기타": ["CMA 예수금", "발행어음", "금 현물", "대체투자 상품"],
}


def write_csv(name: str, rows: list[dict]) -> None:
    path = OUT / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def month_range(end: date, count: int) -> list[str]:
    end_index = end.year * 12 + end.month - 1
    result = []
    for offset in range(count - 1, -1, -1):
        year, month_index = divmod(end_index - offset, 12)
        result.append(f"{year:04d}-{month_index + 1:02d}")
    return result


MONTHS_36 = month_range(TODAY, 36)
MONTHS_12 = MONTHS_36[-12:]


customers = []
customer_tiers = ["VIP", "골드", "골드", "VIP", "일반", "골드", "일반", "VIP", "골드", "일반"]
risks = ["위험중립형", "적극투자형", "안정추구형", "공격투자형", "안정형", "위험중립형", "안정추구형", "적극투자형", "위험중립형", "안정형"]
asset_values = [
    184_221_319, 263_450_000, 124_800_000, 392_100_000, 98_350_000,
    217_600_000, 143_250_000, 486_700_000, 306_450_000, 112_900_000,
]
masked_names = ["김*서", "이*훈", "박*연", "최*민", "정*희", "강*우", "조*은", "윤*석", "장*아", "임*준"]
branches = ["여의도지점", "강남센터", "판교지점", "광화문센터", "부산지점"]
managers = ["김미래PB", "이준호PB", "박서연PB", "최민수PB", "정희진PB"]
employers = ["SK하이닉스", "삼성전자", "현대자동차", "네이버", "LG에너지솔루션"]
for index, customer_id in enumerate(CUSTOMER_IDS):
    customers.append({
        "고객번호": customer_id,
        "고객등급": customer_tiers[index],
        "연령": 52 if index == 0 else 35 + (index * 7) % 29,
        "성별": "남성" if index % 2 == 0 else "여성",
        "투자성향": risks[index],
        "TM동의": "Y" if index % 3 != 1 else "N",
        "EMAIL동의": "N" if index == 0 else ("Y" if index % 3 == 0 else "N"),
        "PUSH동의": "Y" if index % 4 != 2 else "N",
        "관리점": branches[index % len(branches)],
        "PB": managers[index % len(managers)],
        "가입일": "2022-11-02" if index == 0 else f"{2020 + index % 5}-{(index * 2 % 12) + 1:02d}-{(index * 3 % 27) + 1:02d}",
        "주거래상품": "국내주식" if index == 0 else ASSET_CLASSES[index % len(ASSET_CLASSES)],
        "주거래상품비중": 0.60 if index == 0 else round(0.35 + (index % 5) * 0.07, 2),
        "직장정보": "SK하이닉스" if index == 0 else employers[index % len(employers)],
        "만기일": "2027-01-23" if index == 0 else f"2027-{(index % 12) + 1:02d}-{(index * 2 % 27) + 1:02d}",
    })
write_csv("고객", customers)


balance_trend = []
for index, (customer_id, current_value) in enumerate(zip(CUSTOMER_IDS, asset_values)):
    previous_value = round(current_value / 1.062) if index == 0 else round(current_value / (1 + 0.015 * (index % 4 + 1)))
    start_value = current_value * (0.66 + (index % 4) * 0.025)
    for month_index, month in enumerate(MONTHS_36):
        if month_index == 35:
            amount = current_value
        elif month_index == 34:
            amount = previous_value
        else:
            progress = month_index / 34
            seasonality = math.sin(month_index * 0.72 + index) * current_value * 0.008
            amount = round(start_value + (previous_value - start_value) * progress + seasonality)
        balance_trend.append({"고객번호": customer_id, "기준월": month, "자산": amount})
write_csv("잔고추이", balance_trend)


asset_allocations = []
holdings = []
for customer_index, (customer_id, total) in enumerate(zip(CUSTOMER_IDS, asset_values)):
    if customer_index == 0:
        weights = [0.50, 0.18, 0.12, 0.08, 0.09, 0.03]
    else:
        raw = [RNG.uniform(0.04, 0.32) for _ in ASSET_CLASSES]
        weight_total = sum(raw)
        weights = [value / weight_total for value in raw]
    amounts = [round(total * weight) for weight in weights]
    amounts[-1] += total - sum(amounts)
    for asset_class, weight in zip(ASSET_CLASSES, weights):
        asset_allocations.append({
            "고객번호": customer_id,
            "자산구분": asset_class,
            "비중": round(weight, 4),
        })
    for asset_index, (asset_class, category_amount) in enumerate(zip(ASSET_CLASSES, amounts)):
        product_count = 1 if category_amount < 1_000_000 else (2 if asset_index < 2 else 1)
        splits = [category_amount // product_count] * product_count
        splits[-1] += category_amount - sum(splits)
        for split_index, evaluation in enumerate(splits):
            product_list = PRODUCT_NAMES[asset_class]
            product_name = product_list[(customer_index + asset_index + split_index) % len(product_list)]
            profit_rate = RNG.uniform(-0.06, 0.16)
            if customer_index == 0 and asset_class == "국내주식" and split_index == 0:
                product_name = "삼성전자"
                profit_rate = 0.20
            purchase = round(evaluation / (1 + profit_rate)) if evaluation else 0
            holdings.append({
                "고객번호": customer_id,
                "잔고순위": 0,
                "상품명": product_name,
                "자산군": asset_class,
                "매입금액": purchase,
                "평가금액": evaluation,
                "수익률": (evaluation - purchase) / purchase if purchase else 0,
            })
write_csv("자산비중", asset_allocations)
for customer_id in CUSTOMER_IDS:
    customer_holdings = sorted(
        [row for row in holdings if row["고객번호"] == customer_id],
        key=lambda row: row["평가금액"],
        reverse=True,
    )
    for rank, holding in enumerate(customer_holdings, start=1):
        holding["잔고순위"] = rank
write_csv("보유상품", holdings)


transactions = []
for customer_index, customer_id in enumerate(CUSTOMER_IDS):
    for month_index, month in enumerate(MONTHS_12):
        for class_index, asset_class in enumerate(TRADE_ASSET_CLASSES):
            amount = RNG.randint(1_000_000, 17_000_000)
            amount = round(amount * (1 + month_index * 0.025) * (1 + class_index * 0.12))
            transactions.append({
                "고객번호": customer_id,
                "자산군": asset_class,
                "기준월": month,
                "거래금액": amount,
            })
write_csv("거래금액", transactions)


investment_returns = []
for customer_index, customer_id in enumerate(CUSTOMER_IDS):
    returns = [RNG.uniform(-0.035, 0.085) for _ in MONTHS_12]
    returns[-1] = 0.062 if customer_index == 0 else round(RNG.uniform(-0.02, 0.11), 3)
    returns[-2] = 0.038 if customer_index == 0 else round(returns[-1] - RNG.uniform(-0.025, 0.025), 3)
    for month, value in zip(MONTHS_12, returns):
        investment_returns.append({
            "고객번호": customer_id,
            "기준월": month,
            "투자수익률(1년)": round(value, 3),
        })
write_csv("투자수익률", investment_returns)


turnover = []
for customer_index, customer_id in enumerate(CUSTOMER_IDS):
    turnover.extend([
        {
            "고객번호": customer_id,
            "자산구분": "국내주식",
            "회전율": 1.12 if customer_index == 0 else round(RNG.uniform(0.4, 2.8), 2),
        },
        {
            "고객번호": customer_id,
            "자산구분": "해외주식",
            "회전율": 0.76 if customer_index == 0 else round(RNG.uniform(0.3, 2.4), 2),
        },
    ])
write_csv("회전율", turnover)


login_counts = []
for customer_index, customer_id in enumerate(CUSTOMER_IDS):
    for month_index, month in enumerate(MONTHS_12):
        days = 23 if customer_index == 0 and month_index == 11 else RNG.randint(4, 23)
        login_counts.append({"고객번호": customer_id, "기준월": month, "접속일수": days})
write_csv("앱접속일수", login_counts)


menu_names = ["잔고조회", "국내주식", "해외주식", "이체", "수익률", "관심종목", "연금", "ETF", "거래내역", "상품검색"]
app_menus = [
    {"고객번호": customer_id, "순위": rank, "메뉴명": menu}
    for customer_index, customer_id in enumerate(CUSTOMER_IDS)
    for rank, menu in enumerate(
        menu_names[customer_index % len(menu_names):] + menu_names[:customer_index % len(menu_names)],
        start=1,
    )
]
write_csv("앱메뉴TOP", app_menus)


search_words = ["삼성전자", "미국 ETF", "배당주", "연금저축", "국고채"]
search_terms = [
    {"고객번호": customer_id, "순위": rank, "검색어": word}
    for customer_index, customer_id in enumerate(CUSTOMER_IDS)
    for rank, word in enumerate(
        search_words[customer_index % len(search_words):] + search_words[:customer_index % len(search_words)],
        start=1,
    )
]
write_csv("검색어", search_terms)


chatbot_texts = [
    "잔고 조회는 어떻게 하나요?",
    "해외주식 거래 가능 시간을 알려주세요.",
    "연금 계좌의 세액공제 한도가 궁금합니다.",
    "ETF 매수 수수료를 확인하고 싶어요.",
    "만기 예정 상품의 재투자 방법을 알려주세요.",
]
write_csv("챗봇상담", [
    {"고객번호": customer_id, "챗봇상담내역": chatbot_texts[index % len(chatbot_texts)]}
    for index, customer_id in enumerate(CUSTOMER_IDS)
])
call_center_texts = [
    "연금 계좌에서 ETF 매수는 어떻게 하나요?",
    "해외주식 배당금 입금 일정을 문의하셨습니다.",
    "계좌 이체 한도 변경 절차를 안내했습니다.",
    "만기 상품 재투자 상담을 요청하셨습니다.",
    "거래내역 확인 방법을 안내했습니다.",
]
write_csv("고객센터상담", [
    {"고객번호": customer_id, "고객센터상담내역": call_center_texts[index % len(call_center_texts)]}
    for index, customer_id in enumerate(CUSTOMER_IDS)
])


base_scores = {
    "국내주식": 89, "해외주식": 76, "ETF": 84, "IRP": 67, "ISA": 73,
    "DC": 65, "ELS": 54, "랩어카운트": 55, "개인연금": 71,
    "개인투자용국채": 64, "채권": 78, "로보어드바이저": 48, "펀드": 62,
    "순입금": 59, "순출금": 24, "이탈": 28,
}
predictions = []
for customer_index, customer_id in enumerate(CUSTOMER_IDS):
    for topic in PREDICTION_TOPICS:
        score = base_scores[topic] if customer_index == 0 else max(
            10, min(98, base_scores[topic] + RNG.randint(-22, 18))
        )
        if topic == "이탈":
            score = [28, 72, 61, 24, 48, 83, 65, 32, 57, 76][customer_index]
        if score >= 85:
            interpretation = "관심매우높음"
        elif score >= 70:
            interpretation = "관심높음"
        elif score >= 50:
            interpretation = "관심보통"
        else:
            interpretation = "관심낮음"
        if topic == "이탈" and customer_index == 0:
            interpretation = "매우 낮음"
        predictions.append({
            "고객번호": customer_id,
            "예측주제": topic,
            "예측점수": f"{score}점",
            "예측해석": interpretation,
        })
write_csv("예측", predictions)


nba = []
for customer_index, (customer_id, total) in enumerate(zip(CUSTOMER_IDS, asset_values)):
    proposals = [
        (
            "포트폴리오 점검",
            "자산배분 및 목표 비중 점검",
            f"총 보유 평가액 {total:,.0f}원 기준으로 분산과 목표 비중을 확인합니다.",
        ),
        (
            "투자수익률 확인",
            "최근 수익률 및 보유 상품 점검",
            f"총 보유 평가액 {total:,.0f}원과 최근 성과를 바탕으로 보유 상품을 함께 확인합니다.",
        ),
        (
            "관심 상품 안내",
            "고객 관심 자산군 정보 제공",
            f"{customers[customer_index]['주거래상품']} 중심의 상품 정보와 관련 투자 유의사항을 안내합니다.",
        ),
    ]
    nba.extend(
        {
            "고객번호": customer_id,
            "제안순서": order,
            "NextBestAction": " / ".join(proposal),
        }
        for order, proposal in enumerate(proposals, start=1)
    )
write_csv("NBA", nba)

print(f"Wrote {len(list(OUT.glob('*.csv')))} synthetic CSV datasets to {OUT}")
