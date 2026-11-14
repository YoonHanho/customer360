"""Synthetic customer-360° wealth-management dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, callback, dash_table, dcc, html

from harness.data_loader import load_data


ROOT = Path(__file__).resolve().parents[1]
DATA = load_data(ROOT / "data")
CUSTOMERS = DATA["고객"]
BALANCE_TREND = DATA["잔고추이"]
ASSET_ALLOCATION = DATA["자산비중"]
HOLDINGS = DATA["보유상품"]
TRANSACTION_AMOUNTS = DATA["거래금액"]
INVESTMENT_RETURNS = DATA["투자수익률"]
TURNOVER = DATA["회전율"]
APP_LOGINS = DATA["앱접속일수"]
APP_MENU_TOP = DATA["앱메뉴TOP"]
SEARCH_TERMS = DATA["검색어"]
CHATBOT_CONSULTATIONS = DATA["챗봇상담"]
CALL_CENTER_CONSULTATIONS = DATA["고객센터상담"]
PREDICTIONS = DATA["예측"]
NBA = DATA["NBA"]

COLORS = {
    "orange": "#F58220",
    "blue": "#043B72",
    "orange_light": "#F0B26B",
    "orange_dark": "#CB6015",
    "brown": "#AD624E",
    "gray": "#84888B",
    "cyan": "#00A9CE",
    "cyan_dark": "#0086B8",
    "blue_light": "#7E9FC3",
    "sky": "#8DC8E8",
    "ink": "#48535B",
    "sand": "#C2AC97",
    "gray_light": "#A0A6A8",
    "gray_pale": "#CDCECB",
    "warm_white": "#E5E4E1",
    "background": "#ECEFF4",
    "muted": "#84888B",
    "line": "#CDCECB",
}
ASSET_CLASSES = ["국내주식", "해외주식", "ETF", "펀드", "채권", "기타"]
TRADE_ASSET_CLASSES = ASSET_CLASSES[:-1]
PREDICTION_TOPICS = [
    "국내주식",
    "해외주식",
    "ETF",
    "IRP",
    "ISA",
    "DC",
    "ELS",
    "랩어카운트",
    "개인연금",
    "개인투자용국채",
    "채권",
    "로보어드바이저",
    "펀드",
    "순입금",
    "순출금",
    "이탈",
]
PREDICTION_STYLE_BY_INTERPRETATION = {
    "관심매우높음": "prediction-very-high",
    "관심높음": "prediction-high",
    "관심보통": "prediction-neutral",
    "관심낮음": "prediction-neutral",
    "매우 낮음": "prediction-neutral",
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


def churn_label_and_style(score_str: str) -> tuple[str, str]:
    """이탈 예측 점수를 (표시 문구, CSS 클래스) 로 변환한다.
    점수가 낮을수록 이탈 위험이 낮음(안전)을 의미한다."""
    score = int(str(score_str).replace("점", ""))
    if score >= 70:
        return "이탈위험높음", "prediction-churn-danger"
    if score >= 50:
        return "이탈위험보통", "prediction-churn-warning"
    return "이탈위험낮음", "prediction-churn-safe"


def selected_customer(customer_id: str) -> pd.Series:
    matched = CUSTOMERS.loc[CUSTOMERS["고객번호"] == customer_id]
    if matched.empty:
        raise ValueError(f"Unknown customer number: {customer_id}")
    return matched.iloc[0]


def customer_rows(dataset: pd.DataFrame, customer_id: str) -> pd.DataFrame:
    return dataset.loc[dataset["고객번호"] == customer_id].copy()


def figure_layout(fig, height: int = 280):
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


def balance_figure(customer_id: str):
    monthly = customer_rows(BALANCE_TREND, customer_id).sort_values("기준월")
    fig = px.line(
        monthly,
        x="기준월",
        y="자산",
        markers=True,
        color_discrete_sequence=[COLORS["orange"]],
    )
    fig.update_traces(line=dict(width=3), hovertemplate="%{x}<br>%{y:,.0f}원<extra></extra>")
    fig.update_yaxes(title="자산", tickformat="~s")
    fig.update_xaxes(title=None, nticks=8)
    return figure_layout(fig)


def allocation_figure(customer_id: str):
    allocation = customer_rows(ASSET_ALLOCATION, customer_id)
    fig = px.pie(
        allocation,
        values="비중",
        names="자산구분",
        hole=0.58,
        color_discrete_sequence=[
            COLORS["orange"],
            COLORS["blue"],
            COLORS["orange_light"],
            COLORS["cyan"],
            COLORS["blue_light"],
            COLORS["gray_light"],
        ],
    )
    fig.update_traces(
        texttemplate="%{percent}",
        hovertemplate="%{label}<br>%{percent}<extra></extra>",
    )
    return figure_layout(fig, 280)


def transaction_figure(customer_id: str, asset_class: str):
    monthly = customer_rows(TRANSACTION_AMOUNTS, customer_id)
    monthly = monthly.loc[monthly["자산군"] == asset_class].sort_values("기준월")
    fig = px.line(
        monthly,
        x="기준월",
        y="거래금액",
        markers=True,
        color_discrete_sequence=[COLORS["blue"]],
    )
    fig.update_traces(line=dict(width=3), hovertemplate="%{x}<br>%{y:,.0f}원<extra></extra>")
    fig.update_yaxes(title="거래 금액", tickformat="~s")
    fig.update_xaxes(title=None, nticks=8)
    return figure_layout(fig)


def return_figure(customer_id: str):
    monthly = customer_rows(INVESTMENT_RETURNS, customer_id).sort_values("기준월")
    monthly["수익률(%)"] = monthly["투자수익률(1년)"] * 100
    fig = px.bar(
        monthly,
        x="기준월",
        y="수익률(%)",
        color_discrete_sequence=[COLORS["orange"]],
    )
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title="1년 수익률", ticksuffix="%")
    fig.update_xaxes(title=None, nticks=8)
    return figure_layout(fig)


def login_figure(customer_id: str):
    monthly = customer_rows(APP_LOGINS, customer_id).sort_values("기준월")
    fig = px.bar(
        monthly,
        x="기준월",
        y="접속일수",
        color_discrete_sequence=[COLORS["orange"]],
    )
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title="접속 일수", rangemode="tozero")
    fig.update_xaxes(title=None, nticks=8)
    return figure_layout(fig)


def product_table(customer_id: str):
    rows = customer_rows(HOLDINGS, customer_id).sort_values(
        "잔고순위"
    ).head(5).copy()
    rows["매입금액"] = rows["매입금액"].map(lambda value: f"{value:,.0f}")
    rows["평가금액"] = rows["평가금액"].map(lambda value: f"{value:,.0f}")
    rows["수익률"] = rows["수익률"].map(lambda value: f"{value * 100:+.1f}%")
    rows = rows.rename(
        columns={
            "상품명": "상품명",
            "자산군": "자산군",
            "매입금액": "매입금액(원)",
            "평가금액": "평가금액(원)",
            "수익률": "수익률",
        }
    )
    columns = ["상품명", "자산군", "매입금액(원)", "평가금액(원)", "수익률"]
    return dash_table.DataTable(
        data=rows[columns].to_dict("records"),
        columns=[{"name": column, "id": column} for column in columns],
        page_size=5,
        style_as_list_view=True,
        style_header={"fontWeight": "700", "color": COLORS["muted"], "borderBottom": f"1px solid {COLORS['line']}"},
        style_cell={
            "padding": "11px 8px",
            "fontSize": "12px",
            "textAlign": "left",
            "border": "none",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_cell_conditional=[
            {"if": {"column_id": column}, "textAlign": "right"}
            for column in ["매입금액(원)", "평가금액(원)", "수익률"]
        ],
    )


def profile_content(customer_id: str):
    customer = selected_customer(customer_id)
    marketing = (
        f"TM({customer['TM동의']}), EMAIL({customer['EMAIL동의']}), "
        f"PUSH({customer['PUSH동의']})"
    )
    fields = [
        ("고객등급", customer["고객등급"]),
        ("연령/성별", f"{customer['연령']}세 ({customer['성별']})"),
        ("투자성향", customer["투자성향"]),
        ("마케팅동의", marketing),
        ("관리점/PB", f"{customer['관리점']}, {customer['PB']}"),
        ("가입일", customer["가입일"]),
        (
            "주거래상품",
            f"{customer['주거래상품']} ({customer['주거래상품비중'] * 100:.0f}%)",
        ),
        ("직장정보", customer["직장정보"]),
    ]
    return html.Div(
        [
            html.Div([html.Span(label), html.Strong(value)], className="profile-item")
            for label, value in fields
        ],
        className="profile-grid",
    )


def asset_content(customer_id: str):
    return html.Div(
        [
            html.Div(
                [
                    html.Div("자산 잔고 추이 · 최근 3년", className="section-heading"),
                    dcc.Graph(figure=balance_figure(customer_id), config={"displayModeBar": False}),
                ],
                className="chart-panel",
            ),
            html.Div(
                [
                    html.Div("자산군별 비중", className="section-heading"),
                    dcc.Graph(figure=allocation_figure(customer_id), config={"displayModeBar": False}),
                ],
                className="chart-panel",
            ),
            html.Div(
                [
                    html.Div("보유 상품 · 잔고 TOP 5", className="section-heading"),
                    product_table(customer_id),
                ],
                className="chart-panel wide-panel",
            ),
        ],
        className="asset-grid",
    )


def trade_content(customer_id: str):
    latest = customer_rows(TURNOVER, customer_id)

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("자산군별 월간 거래 금액 · 최근 1년", className="section-heading"),
                            dcc.Dropdown(
                                id="trade-asset-select",
                                options=[{"label": item, "value": item} for item in TRADE_ASSET_CLASSES],
                                value="국내주식",
                                clearable=False,
                                className="asset-select",
                            ),
                        ],
                        className="chart-heading-row",
                    ),
                    dcc.Graph(
                        id="transaction-figure",
                        figure=transaction_figure(customer_id, "국내주식"),
                        config={"displayModeBar": False},
                    ),
                ],
                className="chart-panel",
            ),
            html.Div(
                [
                    html.Div("투자수익률(1년) · 월별 추이", className="section-heading"),
                    dcc.Graph(figure=return_figure(customer_id), config={"displayModeBar": False}),
                ],
                className="chart-panel",
            ),
            html.Div(
                [
                    html.Div("최근 월 회전율", className="section-heading"),
                    html.Div(
                        [
                            html.Div(
                                [html.Small(row["자산구분"]), html.Strong(f"{row['회전율'] * 100:.0f}%")],
                                className="metric-tile",
                            )
                            for _, row in latest.iterrows()
                        ],
                        className="turnover-grid",
                    ),
                ],
                className="chart-panel wide-panel",
            ),
        ],
        className="asset-grid",
    )


def behavior_content(customer_id: str):
    menus = customer_rows(APP_MENU_TOP, customer_id).sort_values("순위").head(10)
    searches = customer_rows(SEARCH_TERMS, customer_id).sort_values("순위").head(5)
    chatbot = customer_rows(CHATBOT_CONSULTATIONS, customer_id)
    call_center = customer_rows(CALL_CENTER_CONSULTATIONS, customer_id)
    return html.Div(
        [
            html.Div(
                [
                    html.Div("앱 접속일수 · 최근 1년", className="section-heading"),
                    dcc.Graph(figure=login_figure(customer_id), config={"displayModeBar": False}),
                ],
                className="chart-panel",
            ),
            html.Div(
                [
                    html.Div("앱 메뉴 TOP 10 · 최근 월", className="section-heading"),
                    html.Div(
                        [
                            html.Div(
                                [html.Span(f"{int(row['순위']):02d}"), html.Strong(row["메뉴명"])],
                                className="menu-card",
                            )
                            for _, row in menus.iterrows()
                        ],
                        className="menu-grid",
                    ),
                ],
                className="chart-panel",
            ),
            html.Div(
                [
                    html.Div("최근 검색어", className="section-heading"),
                    html.Div(
                        [html.Span(row["검색어"], className="search-chip") for _, row in searches.iterrows()],
                        className="search-list",
                    ),
                ],
                className="chart-panel",
            ),
            html.Div(
                [
                    html.Div("챗봇 상담", className="section-heading"),
                    html.P(
                        chatbot.iloc[0]["챗봇상담내역"] if not chatbot.empty else "상담 내역이 없습니다.",
                        className="consultation-text",
                    ),
                    html.Div("고객센터 상담", className="section-heading secondary-heading"),
                    html.P(
                        call_center.iloc[0]["고객센터상담내역"] if not call_center.empty else "상담 내역이 없습니다.",
                        className="consultation-text",
                    ),
                ],
                className="chart-panel",
            ),
        ],
        className="behavior-grid",
    )


def predictions_content(customer_id: str):
    predictions = customer_rows(PREDICTIONS, customer_id).copy()
    predictions["정렬순서"] = predictions["예측주제"].map(
        {topic: index for index, topic in enumerate(PREDICTION_TOPICS)}
    )
    predictions = predictions.sort_values("정렬순서")
    cards = []
    for _, row in predictions.iterrows():
        if row["예측주제"] == "이탈":
            label, style = churn_label_and_style(row["예측점수"])
            card = html.Div(
                [
                    html.Span(row["예측주제"], className="prediction-topic"),
                    html.Strong(row["예측점수"], className="prediction-score"),
                    html.Span(label, className=f"prediction-interpretation {style}-label"),
                ],
                className=f"prediction-card {style}",
            )
        else:
            card_style = PREDICTION_STYLE_BY_INTERPRETATION.get(
                row["예측해석"], "prediction-neutral"
            )
            card = html.Div(
                [
                    html.Span(row["예측주제"], className="prediction-topic"),
                    html.Strong(row["예측점수"], className="prediction-score"),
                    html.Span(
                        row["예측해석"],
                        className=f"prediction-interpretation {card_style}-label",
                    ),
                ],
                className=f"prediction-card {card_style}",
            )
        cards.append(card)
    return html.Div(cards, className="prediction-grid")


def tab_content(tab: str, customer_id: str):
    if tab == "customer":
        return profile_content(customer_id)
    if tab == "assets":
        return asset_content(customer_id)
    if tab == "transactions":
        return trade_content(customer_id)
    if tab == "behavior":
        return behavior_content(customer_id)
    if tab == "predictions":
        return predictions_content(customer_id)
    return html.P("선택한 고객 정보를 찾을 수 없습니다.", className="empty-state")


first_customer = str(CUSTOMERS.iloc[0]["고객번호"])
app.layout = html.Div(
    [
        html.Header(
            [
                html.Div(
                    [
                        html.Img(
                            src="/assets/mirae_asset_logo.png",
                            alt="미래에셋증권",
                            className="brand-logo",
                        ),
                        html.Div(
                            [
                                html.Div("WM INSIGHTS", className="brand-eyebrow"),
                                html.H1("고객 360°"),
                                html.P("고객 맥락과 자산 흐름을 한눈에 보는 고객 인사이트", className="header-subtitle"),
                            ],
                            className="brand-copy",
                        ),
                    ],
                    className="brand-lockup",
                ),
                html.Div(
                    [html.Span("목업 · 가상 데이터", className="demo-badge"), html.Span("PB 고객 인사이트", className="header-context")],
                    className="header-right",
                ),
            ],
            className="topbar",
        ),
        html.Main(
            [
                html.Section(
                    [
                        html.Div(
                            [
                                html.Label("고객 선택"),
                                dcc.Dropdown(
                                    id="customer-select",
                                    options=[
                                        {
                                            "label": f"{row['고객번호']} · {row['고객등급']} · {row['PB']}",
                                            "value": str(row["고객번호"]),
                                        }
                                        for _, row in CUSTOMERS.iterrows()
                                    ],
                                    value=first_customer,
                                    clearable=False,
                                    searchable=True,
                                    className="customer-select",
                                ),
                            ],
                            className="selector-wrap",
                        ),
                        html.Div(id="customer-summary", className="snapshot-strip"),
                    ],
                    className="customer-header card",
                ),
                html.Div(
                    [
                        html.Section(
                            [
                                html.Div(
                                    [
                                        html.H2("고객 인사이트"),
                                        html.Span("고객 선택에 따라 목업 지표가 갱신됩니다.", className="muted-note"),
                                    ],
                                    className="section-title-row",
                                ),
                                dcc.Tabs(
                                    id="customer-tabs",
                                    value="customer",
                                    children=[
                                        dcc.Tab(label=label, value=value, className="tab", selected_className="tab-selected")
                                        for label, value in [
                                            ("고객", "customer"),
                                            ("자산", "assets"),
                                            ("거래", "transactions"),
                                            ("행동", "behavior"),
                                            ("예측", "predictions"),
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
            ],
            className="page-content",
        ),
        html.Footer(
            "모든 고객·거래·예측 정보는 화면 시연을 위한 가상 데이터이며 실제 투자 권유가 아닙니다.",
            className="footer",
        ),
    ],
    className="app-shell",
)


@callback(Output("customer-summary", "children"), Input("customer-select", "value"))
def update_customer_summary(customer_id: str):
    customer = selected_customer(customer_id)
    balances = customer_rows(BALANCE_TREND, customer_id).sort_values("기준월")
    latest_balance = balances.iloc[-1]
    previous_balance = balances.iloc[-2]
    monthly_change = (latest_balance["자산"] / previous_balance["자산"] - 1) * 100

    returns = customer_rows(INVESTMENT_RETURNS, customer_id).sort_values("기준월")
    current_return = returns.iloc[-1]["투자수익률(1년)"] * 100
    previous_return = returns.iloc[-2]["투자수익률(1년)"] * 100
    return_delta = current_return - previous_return

    churn = customer_rows(PREDICTIONS, customer_id)
    churn = churn.loc[churn["예측주제"] == "이탈"].iloc[0]
    churn_label, _ = churn_label_and_style(churn["예측점수"])
    allocation = customer_rows(ASSET_ALLOCATION, customer_id)
    main_product_share = allocation.loc[
        allocation["자산구분"] == customer["주거래상품"], "비중"
    ].iloc[0]

    metrics = [
        ("총자산 AUM", money(float(latest_balance["자산"])), f"최근 1개월 {monthly_change:+.1f}%"),
        ("투자성향", customer["투자성향"], f"{customer['만기일']} 만기"),
        ("이탈위험", churn["예측점수"], churn_label),
        ("투자수익률(1년)", f"{current_return:+.1f}%", f"전월 대비 {return_delta:+.1f}%p"),
        ("주거래상품", customer["주거래상품"], f"잔고비중 {main_product_share * 100:.0f}%"),
    ]
    return [
        html.Div(
            [html.Small(label), html.Strong(value), html.Span(note)],
            className="snapshot-metric",
        )
        for label, value, note in metrics
    ]


@callback(
    Output("tab-panel", "children"),
    Input("customer-tabs", "value"),
    Input("customer-select", "value"),
)
def update_tab(tab: str, customer_id: str):
    return tab_content(tab, customer_id)


@callback(
    Output("transaction-figure", "figure"),
    Input("trade-asset-select", "value"),
    Input("customer-select", "value"),
)
def update_transaction_figure(asset_class: str, customer_id: str):
    return transaction_figure(customer_id, asset_class)


@callback(Output("nba-panel", "children"), Input("customer-select", "value"))
def update_nba_panel(customer_id: str):
    actions = customer_rows(NBA, customer_id).sort_values("제안순서")
    cards = []
    for _, row in actions.iterrows():
        parts = str(row["NextBestAction"]).split(" / ", maxsplit=2)
        if len(parts) != 3:
            raise ValueError(
                f"NBA proposal {row['제안순서']} for customer {customer_id} "
                "must have topic, content, and detail"
            )
        cards.append(
            html.Div(
                [
                    html.Span(f"{int(row['제안순서']):02d}", className="nba-order"),
                    html.Strong(parts[0], className="nba-topic"),
                    html.Strong(parts[1], className="nba-title"),
                    html.P(parts[2], className="nba-explanation"),
                ],
                className="nba-recommendation",
            )
        )
    return [
        html.Div(
            [
                html.H2("Next Best Action"),
            ],
            className="section-title-row",
        ),
        *cards,
    ]


if __name__ == "__main__":
    app.run(debug=False)
