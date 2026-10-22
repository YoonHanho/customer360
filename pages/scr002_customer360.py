"""Synthetic customer-360° wealth-management dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, State, callback, dash_table, dcc, html

from harness.data_loader import load_data
from harness.nba_engine import recommend_actions


ROOT = Path(__file__).resolve().parents[1]
DATA = load_data(ROOT / "data")
CUSTOMERS = DATA["customers"]
PRODUCTS = DATA["products"]
HOUSE_VIEW = DATA["house_view"]
ALLOCATION = DATA["allocation_strategy"]
TRANSACTIONS = DATA["transactions"]
CONSULTATIONS = DATA["consultations"]
NEWS = DATA["news"]

COLORS = {
    "navy": "#172d4f",
    "blue": "#365ee8",
    "teal": "#16a68a",
    "amber": "#e2a43a",
    "red": "#df6570",
    "muted": "#78869b",
    "line": "#e8edf4",
    "surface": "#ffffff",
    "background": "#f4f7fb",
}

app = Dash(
    __name__,
    title="고객 360° | WM 인사이트",
    assets_folder=str(ROOT / "assets"),
    suppress_callback_exceptions=True,
)
server = app.server


def money(value: float) -> str:
    if value >= 100_000_000:
        return f"{value / 100_000_000:,.1f}억"
    return f"{value / 10_000:,.0f}만원"


def figure_layout(fig, height: int = 260):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color=COLORS["muted"], size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor=COLORS["line"])
    fig.update_yaxes(gridcolor=COLORS["line"], zeroline=False)
    return fig


def customer_options():
    return [
        {"label": f"{row.name_masked} · {row.segment}", "value": row.customer_id}
        for row in CUSTOMERS.itertuples()
    ]


def selected_customer(customer_id: str):
    row = CUSTOMERS.loc[CUSTOMERS["customer_id"] == customer_id].iloc[0]
    holdings = DATA["holdings"].loc[DATA["holdings"]["customer_id"] == customer_id].merge(
        PRODUCTS, on="product_id", how="left"
    )
    return row, holdings


def portfolio_figure(holdings: pd.DataFrame):
    allocation = holdings.groupby("category", as_index=False)["amount"].sum()
    fig = px.pie(
        allocation,
        values="amount",
        names="category",
        hole=0.68,
        color_discrete_sequence=["#365ee8", "#16a68a", "#72a3fa", "#e2a43a", "#b5c0d2"],
    )
    fig.update_traces(textinfo="none", hovertemplate="%{label}<br>%{percent}<extra></extra>")
    fig.update_layout(showlegend=True)
    return figure_layout(fig, 250)


def risk_figure(customer_id: str):
    tx = TRANSACTIONS.loc[TRANSACTIONS["customer_id"] == customer_id].copy()
    tx["date"] = pd.to_datetime(tx["date"])
    monthly = tx.set_index("date").resample("ME")["amount"].sum().tail(12).reset_index()
    fig = px.area(monthly, x="date", y="amount", color_discrete_sequence=[COLORS["blue"]])
    fig.update_traces(line=dict(width=2), fillcolor="rgba(54,94,232,0.10)")
    fig.update_yaxes(title="거래 금액", tickformat="~s")
    fig.update_xaxes(title=None)
    return figure_layout(fig, 250)


def tab_content(tab: str, customer_id: str):
    customer, holdings = selected_customer(customer_id)
    cust_consults = CONSULTATIONS.loc[
        CONSULTATIONS["customer_id"] == customer_id
    ].sort_values("date", ascending=False)

    if tab == "profile":
        fields = [
            ("고객 구분", customer.segment),
            ("투자 성향", customer.risk_profile),
            ("담당 지점 / PB", f"{customer.branch} · {customer.manager}"),
            ("가입일", customer.join_date),
            ("투자 목표", customer.investment_goal),
            ("투자 기간", customer.investment_horizon),
            ("마케팅 동의", customer.marketing_consent),
            ("정보 최신화", customer.profile_updated),
        ]
        return html.Div(
            [html.Div([html.Span(label), html.Strong(value)], className="profile-item") for label, value in fields],
            className="profile-grid",
        )

    if tab == "portfolio":
        portfolio_table = dash_table.DataTable(
            data=holdings[["name", "category", "amount", "pnl", "maturity_date"]].rename(
                columns={
                    "name": "상품",
                    "category": "자산군",
                    "amount": "평가금액(원)",
                    "pnl": "평가손익(원)",
                    "maturity_date": "만기",
                }
            ).to_dict("records"),
            columns=[{"name": col, "id": col} for col in ["상품", "자산군", "평가금액(원)", "평가손익(원)", "만기"]],
            page_size=5,
            style_as_list_view=True,
            style_header={"fontWeight": "700", "color": COLORS["muted"]},
            style_cell={"padding": "11px 8px", "fontSize": "12px", "textAlign": "left"},
        )
        return html.Div(
            [
                html.Div(
                    [
                        html.Div("자산군별 배분", className="section-heading"),
                        dcc.Graph(figure=portfolio_figure(holdings), config={"displayModeBar": False}),
                    ],
                    className="chart-panel",
                ),
                html.Div([html.Div("보유 상품", className="section-heading"), portfolio_table], className="chart-panel"),
            ],
            className="two-column",
        )

    if tab == "risk":
        return html.Div(
            [
                html.Div(
                    [
                        html.Div("최근 12개월 거래 흐름", className="section-heading"),
                        dcc.Graph(figure=risk_figure(customer_id), config={"displayModeBar": False}),
                    ],
                    className="chart-panel",
                ),
                html.Div(
                    [
                        html.Div("리스크 스냅샷", className="section-heading"),
                        html.Div(
                            [
                                html.Div([html.Small("연환산 변동성"), html.Strong(f"{customer.volatility:.1f}%")], className="metric-tile"),
                                html.Div([html.Small("최대 낙폭(MDD)"), html.Strong(f"-{customer.mdd:.1f}%")], className="metric-tile"),
                                html.Div([html.Small("샤프 비율"), html.Strong(f"{customer.sharpe:.2f}")], className="metric-tile"),
                                html.Div([html.Small("1개월 VaR(95%)"), html.Strong(f"{customer.var_95:.1f}%")], className="metric-tile"),
                            ],
                            className="metric-grid",
                        ),
                        html.P("목업 데이터 기반 참고 지표이며 실제 투자 판단 또는 수익을 보장하지 않습니다.", className="fine-print"),
                    ],
                    className="chart-panel",
                ),
            ],
            className="two-column",
        )

    if tab == "behavior":
        tx = TRANSACTIONS.loc[TRANSACTIONS["customer_id"] == customer_id]
        channel_counts = tx["channel"].value_counts().rename_axis("channel").reset_index(name="count")
        fig = px.bar(channel_counts, x="channel", y="count", color_discrete_sequence=[COLORS["teal"]])
        fig.update_layout(showlegend=False)
        fig.update_xaxes(title=None)
        fig.update_yaxes(title="거래 건수")
        return html.Div(
            [
                html.Div([html.Div("채널별 거래", className="section-heading"), dcc.Graph(figure=figure_layout(fig), config={"displayModeBar": False})], className="chart-panel"),
                html.Div(
                    [
                        html.Div("행동 시그널", className="section-heading"),
                        html.Div([html.Small("최근 90일 거래"), html.Strong(f"{len(tx)}건")], className="metric-tile"),
                        html.Div([html.Small("추정 회전율"), html.Strong(f"{customer.turnover:.1f}x")], className="metric-tile"),
                        html.P("행동 편향 지표는 목업 시그널이며 고객 성향을 확정적으로 진단하지 않습니다.", className="fine-print"),
                    ],
                    className="chart-panel",
                ),
            ],
            className="two-column",
        )

    if tab == "consult":
        return html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div([html.Strong(item.topic_code), html.Span(f"{item.date} · {item.channel}", className="timeline-meta")]),
                                html.P(item.summary_masked),
                                html.Span("상담 완료" if item.resolved else "후속 확인 필요", className="status-pill"),
                            ],
                            className="timeline-item",
                        )
                        for item in cust_consults.head(6).itertuples()
                    ]
                    or [html.P("등록된 상담 이력이 없습니다.", className="empty-state")],
                    className="timeline",
                )
            ]
        )

    if tab == "market":
        gaps = ALLOCATION.loc[ALLOCATION["segment"] == customer.segment].merge(
            HOUSE_VIEW[["asset_class", "outlook"]], on="asset_class", how="left"
        )
        rows = []
        for item in gaps.itertuples():
            rows.append(
                html.Div(
                    [
                        html.Span(item.asset_class),
                        html.Span(f"목표 {item.target_pct:.0f}%"),
                        html.Span(item.outlook or "중립", className=f"outlook outlook-{item.outlook or '중립'}"),
                    ],
                    className="allocation-row",
                )
            )
        return html.Div(
            [
                html.Div([html.Div("하우스뷰 정합성", className="section-heading"), *rows], className="chart-panel"),
                html.Div(
                    [
                        html.Div("시장 브리핑", className="section-heading"),
                        *[
                            html.Div(
                                [html.Span(news.tag, className="news-tag"), html.Strong(news.title_masked), html.Small(f"{news.date} · {news.source}")],
                                className="news-item",
                            )
                            for news in NEWS.sort_values("date", ascending=False).head(4).itertuples()
                        ],
                    ],
                    className="chart-panel",
                ),
            ],
            className="two-column",
        )

    if tab == "digital":
        logs = DATA["chatbot_logs"].loc[DATA["chatbot_logs"]["customer_id"] == customer_id]
        return html.Div(
            [
                html.Div([html.Small("최근 30일 접속"), html.Strong(f"{customer.login_days}일")], className="metric-tile"),
                html.Div([html.Small("주요 관심"), html.Strong(customer.digital_interest)], className="metric-tile"),
                html.Div([html.Small("상담 연결 요청"), html.Strong(f"{int(logs['escalated'].sum())}회")], className="metric-tile"),
                html.P("디지털 행동은 합성 로그 기반으로 실시간 수집·추적 기능을 제공하지 않습니다.", className="fine-print"),
            ],
            className="digital-summary",
        )

    if tab == "health":
        return html.Div(
            [
                html.Div([html.Small("이탈 위험"), html.Strong(f"{customer.churn_risk:.0f}점"), html.Div(html.Span(style={"width": f"{customer.churn_risk:.0f}%"}), className="score-track")], className="health-score"),
                html.Div([html.Small("관계 건강도"), html.Strong(f"{customer.health_score:.0f}점"), html.Div(html.Span(style={"width": f"{customer.health_score:.0f}%"}), className="score-track")], className="health-score"),
                html.Div([html.Small("추정 지갑 점유율"), html.Strong(f"{customer.wallet_share:.0f}%")], className="metric-tile"),
                html.Div([html.Small("관계 케어"), html.Strong("우선 관리" if customer.churn_risk >= 60 else "정기 관리")], className="metric-tile"),
            ],
            className="metric-grid",
        )

    if tab == "simulation":
        return html.Div(
            [
                html.Div(
                    [
                        html.Label("추가 투자 제안 금액"),
                        dcc.Slider(id="proposal-amount", min=0, max=50_000_000, step=5_000_000, value=10_000_000, marks={0: "0", 25_000_000: "2,500만", 50_000_000: "5,000만"}),
                        html.Label("목표 자금 (10년 후)"),
                        dcc.Input(id="goal-amount", type="number", min=10_000_000, step=10_000_000, value=150_000_000, className="input"),
                        html.Button("목표 달성률 계산", id="simulate-button", n_clicks=0, className="button button-primary"),
                    ],
                    className="simulation-controls",
                ),
                html.Div(id="simulation-result", className="simulation-result", children="금액과 목표를 설정한 뒤 시뮬레이션을 실행하세요."),
            ],
            className="simulation-panel",
        )

    return html.P("선택한 분석 영역을 준비하지 못했습니다.", className="empty-state")


first_customer = CUSTOMERS.iloc[0]["customer_id"]
app.layout = html.Div(
    [
        html.Header(
            [
                html.Div([html.Div("WM INSIGHTS", className="brand-eyebrow"), html.H1("고객 360°"), html.P("고객 맥락과 시장 시그널을 연결하는 자산관리 인사이트", className="header-subtitle")]),
                html.Div([html.Span("목업 · 가상 데이터", className="demo-badge"), html.Span("PB 업무 홈", className="header-context")], className="header-right"),
            ],
            className="topbar",
        ),
        html.Main(
            [
                html.Section(
                    [
                        html.Div([html.Label("관리 고객"), dcc.Dropdown(id="customer-select", options=customer_options(), value=first_customer, clearable=False, searchable=True, className="customer-select")], className="selector-wrap"),
                        html.Div(id="customer-summary", className="snapshot-strip"),
                    ],
                    className="customer-header card",
                ),
                html.Div(
                    [
                        html.Section(
                            [
                                html.Div([html.H2("고객 인사이트"), html.Span("고객 정보는 화면 내 합성 데이터입니다.", className="muted-note")], className="section-title-row"),
                                dcc.Tabs(
                                    id="customer-tabs",
                                    value="profile",
                                    children=[
                                        dcc.Tab(label=label, value=value, className="tab", selected_className="tab-selected")
                                        for label, value in [
                                            ("프로파일", "profile"),
                                            ("자산·포트폴리오", "portfolio"),
                                            ("성과·리스크", "risk"),
                                            ("거래 행태", "behavior"),
                                            ("상담·접점", "consult"),
                                            ("디지털 행동", "digital"),
                                            ("시장·상품", "market"),
                                            ("건강도·관계", "health"),
                                            ("목표 시뮬레이션", "simulation"),
                                        ]
                                    ],
                                    className="tabs",
                                ),
                                html.Div(id="tab-panel", className="tab-panel"),
                            ],
                            className="card insights-card",
                        ),
                        html.Aside(id="nba-panel", className="card nba-panel"),
                    ],
                    className="content-grid",
                ),
                html.Div(
                    [
                        html.Section(
                            [
                                html.Div([html.H2("오늘의 우선 액션"), html.Span("적합성·긴급도·고객 맥락을 반영한 설명 가능한 목업 점수", className="muted-note")], className="section-title-row"),
                                html.Div(id="action-queue"),
                            ],
                            className="card queue-card",
                        ),
                        html.Section(
                            [
                                html.Div([html.H2("하우스뷰"), html.Span("주간 전략 요약", className="muted-note")], className="section-title-row"),
                                html.Div(id="house-view-panel", className="house-view-grid"),
                            ],
                            className="card house-card",
                        ),
                    ],
                    className="bottom-grid",
                ),
                html.Div(id="action-feedback", className="toast", role="status"),
            ],
            className="page-content",
        ),
        html.Footer("본 화면은 가상 데이터 기반 목업입니다. 투자 권유·실제 거래·실시간 모델 추론 기능을 포함하지 않습니다.", className="footer"),
    ],
    className="app-shell",
)


@callback(Output("customer-summary", "children"), Input("customer-select", "value"))
def update_customer_summary(customer_id):
    customer, _ = selected_customer(customer_id)
    metrics = [
        ("총자산 AUM", money(customer.aum), f"최근 1개월 {customer.aum_change:+.1f}%"),
        ("투자 성향", customer.risk_profile, f"{customer.segment} 고객"),
        ("이탈 위험", f"{customer.churn_risk:.0f}점", "모형 참고 점수"),
        ("관계 건강도", f"{customer.health_score:.0f}점", "100점 만점"),
    ]
    return [
        html.Div([html.Small(label), html.Strong(value), html.Span(note)], className="snapshot-metric")
        for label, value, note in metrics
    ]


@callback(
    Output("tab-panel", "children"),
    Input("customer-tabs", "value"),
    Input("customer-select", "value"),
)
def update_tab(tab, customer_id):
    return tab_content(tab, customer_id)


@callback(
    Output("nba-panel", "children"),
    Input("customer-select", "value"),
)
def update_nba_panel(customer_id):
    customer, _ = selected_customer(customer_id)
    actions = recommend_actions(customer, DATA["holdings"], PRODUCTS)
    cards = []
    for action in actions:
        cards.append(
            html.Div(
                [
                    html.Div([html.Span(action["category"], className="action-label"), html.Span(f"{action['score']}점", className="action-score")], className="action-heading"),
                    html.Strong(action["title"], className="action-title"),
                    html.P(action["why"], className="action-why"),
                    html.Div([html.Span("적합성 검토"), html.Strong("상품 특정 전")], className="suitability-line"),
                ],
                className="nba-card",
            )
        )
    return [
        html.Div([html.H2("Next Best Action"), html.Span("추천 근거 보기", className="muted-note")], className="section-title-row"),
        html.P("가상 데이터 규칙 기반 추천 · 실제 모델 아님", className="recommendation-note"),
        *cards,
        html.Div(
            [
                html.Button("모바일 제안서 초안", id="proposal-button", n_clicks=0, className="button button-primary"),
                html.Button("상담 약속 등록", id="appointment-button", n_clicks=0, className="button button-secondary"),
                dcc.Dropdown(id="decline-reason", options=[{"label": reason, "value": reason} for reason in ["시기 미도래", "투자 의향 없음", "추가 설명 필요"]], placeholder="거부 사유 선택", clearable=True, className="decline-select"),
            ],
            className="nba-actions",
        ),
    ]


@callback(
    Output("action-queue", "children"),
    Output("house-view-panel", "children"),
    Input("customer-select", "value"),
)
def update_book_widgets(customer_id):
    tasks = []
    for customer in CUSTOMERS.itertuples():
        recommendations = recommend_actions(customer, DATA["holdings"], PRODUCTS)
        if recommendations:
            top = recommendations[0]
            tasks.append((top["score"], customer, top))
    tasks.sort(key=lambda item: item[0], reverse=True)
    queue = html.Div(
        [
            html.Div(
                [
                    html.Div([html.Strong(customer.name_masked), html.Small(f"{customer.segment} · {customer.manager}")], className="queue-customer"),
                    html.Div([html.Strong(action["title"]), html.Small(action["why"])], className="queue-action"),
                    html.Span(f"{score}점", className="queue-score"),
                ],
                className="queue-row",
            )
            for score, customer, action in tasks[:5]
        ],
        className="queue-list",
    )
    views = HOUSE_VIEW.sort_values("date", ascending=False).drop_duplicates("asset_class")
    house = [
        html.Div([html.Span(row.asset_class), html.Strong(row.outlook), html.Small(row.headline)], className="house-view-item")
        for row in views.itertuples()
    ]
    return queue, house


@callback(
    Output("simulation-result", "children"),
    Input("simulate-button", "n_clicks"),
    State("customer-select", "value"),
    State("proposal-amount", "value"),
    State("goal-amount", "value"),
    prevent_initial_call=True,
)
def run_goal_simulation(n_clicks, customer_id, proposal_amount, goal_amount):
    customer, _ = selected_customer(customer_id)
    goal = max(float(goal_amount or 1), 1)
    contribution = max(float(proposal_amount or 0), 0)
    horizon_years = 10
    initial = customer.aum + contribution
    seed = sum(ord(char) for char in customer_id) + int(contribution)
    rng = __import__("random").Random(seed)
    annual_return = 0.045
    annual_volatility = max(float(customer.volatility) / 100, 0.03)
    outcomes = []
    for _ in range(1500):
        balance = initial
        for _ in range(horizon_years):
            balance *= max(0.0, 1 + rng.gauss(annual_return, annual_volatility))
        outcomes.append(balance)
    success_rate = sum(balance >= goal for balance in outcomes) / len(outcomes) * 100
    median = sorted(outcomes)[len(outcomes) // 2]
    return html.Div(
        [
            html.Div([html.Small("목표 달성 추정 확률"), html.Strong(f"{success_rate:.1f}%")], className="simulation-highlight"),
            html.P(f"10년 후 예상 중간값 {money(median)} · {len(outcomes):,}회 가상 경로"),
            html.P("가정 수익률 4.5%, 변동성은 고객 목업 지표를 사용합니다. 실제 예측·수익 보장이 아닙니다.", className="fine-print"),
        ]
    )


@callback(
    Output("action-feedback", "children"),
    Output("action-feedback", "className"),
    Input("proposal-button", "n_clicks"),
    Input("appointment-button", "n_clicks"),
    Input("decline-reason", "value"),
    prevent_initial_call=True,
)
def show_action_feedback(proposal_clicks, appointment_clicks, decline_reason):
    from dash import ctx

    if ctx.triggered_id == "proposal-button":
        if not proposal_clicks:
            return "", "toast"
        return "가상 모바일 제안서 초안을 생성했습니다. 발송은 수행하지 않았습니다.", "toast toast-visible"
    if ctx.triggered_id == "appointment-button":
        if not appointment_clicks:
            return "", "toast"
        return "상담 약속 입력을 확인했습니다. 외부 일정에는 등록되지 않았습니다.", "toast toast-visible"
    if decline_reason:
        return f"거부 사유를 목업 화면에 기록했습니다: {decline_reason}", "toast toast-visible"
    return "", "toast"


if __name__ == "__main__":
    app.run(debug=False)
