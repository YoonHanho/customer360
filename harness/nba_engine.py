"""Transparent, deterministic mock NBA scoring with a hard suitability gate."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


RISK_LEVEL = {"안정형": 1, "안정추구형": 2, "위험중립형": 3, "적극투자형": 4, "공격투자형": 5}
WEIGHTS = {"suitability": 0.30, "context": 0.22, "view": 0.16, "urgency": 0.16, "portfolio": 0.12, "fatigue": 0.04}
LEGAL_SUITABILITY_FLOOR = 60


def recommend_actions(customer, holdings: pd.DataFrame, products: pd.DataFrame) -> list[dict]:
    """Return ranked illustrative actions; unsuitable products never pass the gate."""
    customer_id = customer["customer_id"] if isinstance(customer, dict) else customer.customer_id
    risk_profile = customer["risk_profile"] if isinstance(customer, dict) else customer.risk_profile
    churn = float(customer["churn_risk"] if isinstance(customer, dict) else customer.churn_risk)
    profile_risk = RISK_LEVEL.get(risk_profile, 3)
    customer_holdings = holdings.loc[holdings["customer_id"] == customer_id]
    holdings_detail = customer_holdings.merge(products, on="product_id", how="left")
    portfolio_total = float(holdings_detail["amount"].sum()) if not holdings_detail.empty else 0.0

    candidates: list[dict] = []
    maturity_dates = pd.to_datetime(customer_holdings["maturity_date"], errors="coerce") if not customer_holdings.empty else pd.Series(dtype="datetime64[ns]")
    today = pd.Timestamp(date.today())
    maturity_soon = bool(maturity_dates.between(today, today + pd.Timedelta(days=30)).any())
    if maturity_soon:
        candidates.append({
            "category": "만기 재투자", "title": "만기 자금 운용 계획 점검",
            "why": "30일 내 만기 예정 자산이 있어 고객 의향과 현금 수요 확인이 필요합니다.",
            "context": 88, "view": 72, "urgency": 94, "portfolio": 70, "risk_grade": 2,
        })
    if churn >= 55:
        candidates.append({
            "category": "관계 케어", "title": "선제적 안부·자산 현황 확인",
            "why": f"가상 이탈 위험 점수가 {churn:.0f}점으로 관계 상태 확인이 우선입니다.",
            "context": min(100, 70 + churn * 0.3), "view": 55,
            "urgency": min(100, 50 + churn * 0.5), "portfolio": 62, "risk_grade": profile_risk,
        })
    candidates.append({
        "category": "포트폴리오 점검", "title": "자산배분 및 목표 비중 점검",
        "why": f"총 보유 평가액 {portfolio_total:,.0f}원 기준으로 분산과 목표 비중을 확인합니다.",
        "context": 72, "view": 82, "urgency": 64, "portfolio": 86, "risk_grade": profile_risk,
    })

    result = []
    for candidate in candidates:
        grade_distance = abs(profile_risk - candidate["risk_grade"])
        suitability = max(0, 100 - grade_distance * 18)
        if suitability < LEGAL_SUITABILITY_FLOOR:
            continue
        raw = (
            WEIGHTS["suitability"] * suitability
            + WEIGHTS["context"] * candidate["context"]
            + WEIGHTS["view"] * candidate["view"]
            + WEIGHTS["urgency"] * candidate["urgency"]
            + WEIGHTS["portfolio"] * candidate["portfolio"]
            - WEIGHTS["fatigue"] * 10
        )
        result.append({
            **candidate,
            "score": round(min(100, max(0, raw))),
            "suitability": suitability,
            "eligible": True,
        })
    return sorted(result, key=lambda item: item["score"], reverse=True)[:3]
