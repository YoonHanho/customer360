"""Dash 고객 360 대시보드를 독립 실행 가능한 단독(오프라인) HTML 파일로 내보내는 스크립트.

서버(Flask/Dash) 없이 웹 브라우저에서 바로 열람할 수 있도록,
모든 고객 데이터와 Plotly 차트, 탭 전환 스크립트, 스타일시트를 단일 HTML 파일로 패키징합니다.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from dash import html as dash_html
from dash.development.base_component import Component
from plotly.offline import get_plotlyjs
from plotly.utils import PlotlyJSONEncoder

from pages.scr002_customer360 import (
    CUSTOMERS,
    ROOT,
    TRADE_ASSET_CLASSES,
    app,
    tab_content,
    transaction_figure,
    update_customer_summary,
    update_nba_panel,
)


# 닫는 태그가 없는 HTML 빈 태그(Void tags) 목록
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

# Dash 속성명을 표준 HTML 속성명으로 변환하는 매핑
ATTRIBUTE_NAMES = {
    "className": "class",
    "htmlFor": "for",
    "tabIndex": "tabindex",
    "readOnly": "readonly",
    "autoFocus": "autofocus",
}


def _walk(value: Any):
    """Dash 컴포넌트 트리를 재귀적으로 순회하여 하위 컴포넌트들을 yield하는 제너레이터."""
    if isinstance(value, Component):
        yield value
        yield from _walk(value.to_plotly_json()["props"].get("children"))
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def _find_by_id(root: Component, component_id: str) -> Component:
    """컴포넌트 트리에서 지정된 id를 가진 컴포넌트를 검색하여 반환."""
    for component in _walk(root):
        if component.to_plotly_json()["props"].get("id") == component_id:
            return component
    raise ValueError(f"Dashboard component not found: {component_id}")


def _find_by_class(root: Component, class_name: str) -> Component:
    """컴포넌트 트리에서 지정된 클래스명을 가진 컴포넌트를 검색하여 반환."""
    for component in _walk(root):
        classes = component.to_plotly_json()["props"].get("className", "").split()
        if class_name in classes:
            return component
    raise ValueError(f"Dashboard component with class not found: {class_name}")


def _style_text(style: dict[str, Any]) -> str:
    """스타일 딕셔너리(카멜케이스)를 인라인 CSS 스타일 문자열(케밥케이스)로 변환."""
    declarations = []
    for name, value in style.items():
        if value is not None:
            css_name = re.sub(r"([A-Z])", r"-\1", name).lower()
            declarations.append(f"{css_name}:{value}")
    return ";".join(declarations)


def _json_text(value: Any) -> str:
    """PlotlyJSONEncoder를 사용하여 데이터를 안전한 JSON 문자열로 직렬화."""
    return json.dumps(value, cls=PlotlyJSONEncoder, ensure_ascii=False).replace("<", "\\u003c")


class OfflineRenderer:
    """Dash 컴포넌트 및 Plotly 차트를 정적 HTML 태그와 오프라인 스크립트용 데이터로 변환하는 렌더러."""

    def __init__(self) -> None:
        """렌더러 초기화 및 그래프 데이터 저장소 준비."""
        self.graphs: dict[str, dict[str, Any]] = {}
        self.transaction_graphs: dict[str, dict[str, dict[str, Any]]] = {}
        self.transaction_graph_id_by_customer: dict[str, str] = {}
        self.graph_number = 0

    def render(self, component: Any, customer_id: str | None = None) -> str:
        """Dash 컴포넌트를 해당하는 HTML 문자열로 재귀 렌더링."""
        if component is None:
            return ""
        if isinstance(component, (list, tuple)):
            return "".join(self.render(item, customer_id) for item in component)
        if not isinstance(component, Component):
            return html.escape(str(component))

        payload = component.to_plotly_json()
        namespace = payload["namespace"]
        component_type = payload["type"]
        props = payload["props"]

        if namespace == "dash_core_components" and component_type == "Dropdown":
            return self._render_dropdown(props, customer_id)
        if namespace == "dash_core_components" and component_type == "Graph":
            return self._render_graph(props, customer_id)
        if namespace == "dash_table" and component_type == "DataTable":
            return self._render_table(props)
        if namespace != "dash_html_components":
            raise ValueError(f"Unsupported dashboard component: {namespace}.{component_type}")

        tag = component_type.lower()
        attributes = self._render_attributes(props, tag)
        child_customer_id = props.get("data-customer-id", customer_id)
        children = self.render(props.get("children"), child_customer_id)
        if tag in VOID_TAGS:
            return f"<{tag}{attributes}>"
        return f"<{tag}{attributes}>{children}</{tag}>"

    def _render_attributes(self, props: dict[str, Any], tag: str) -> str:
        """컴포넌트 속성(props)을 HTML 속성 문자열로 변환 (로컬 이미지 base64 인라인 포함)."""
        attributes: list[str] = []
        for name, value in props.items():
            if name in {"children", "key", "loading_state", "dangerouslySetInnerHTML"} or value is None:
                continue
            if name == "style":
                value = _style_text(value)
                if not value:
                    continue
            if name == "src" and tag == "img" and value.startswith("/assets/"):
                asset_path = (ROOT / "assets" / value.removeprefix("/assets/")).resolve()
                assets_root = (ROOT / "assets").resolve()
                try:
                    asset_path.relative_to(assets_root)
                except ValueError as error:
                    raise ValueError(f"Asset path is outside the assets folder: {value}") from error
                if not asset_path.is_file():
                    raise FileNotFoundError(f"Dashboard asset not found: {asset_path}")
                mime_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
                encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
                value = f"data:{mime_type};base64,{encoded}"
            attribute_name = ATTRIBUTE_NAMES.get(name, name)
            if isinstance(value, bool):
                if attribute_name.startswith(("aria-", "data-")):
                    value = str(value).lower()
                elif value:
                    attributes.append(f" {attribute_name}=\"{attribute_name}\"")
                    continue
                else:
                    continue
            attributes.append(f" {attribute_name}=\"{html.escape(str(value), quote=True)}\"")
        return "".join(attributes)

    def _render_dropdown(self, props: dict[str, Any], customer_id: str | None) -> str:
        """Dash Dropdown 컴포넌트를 정적 HTML <select> 태그로 렌더링."""
        component_id = props.get("id", "")
        element_id = (
            f"{component_id}-{customer_id}"
            if component_id == "trade-asset-select" and customer_id is not None
            else component_id
        )
        classes = "offline-select " + props.get("className", "")
        role = {
            "customer-select": "customer-select",
            "trade-asset-select": "trade-asset-select",
        }.get(component_id)
        role_attribute = f' data-role="{role}"' if role else ""
        selected_value = str(props.get("value", ""))
        options = []
        for option in props.get("options", []):
            value = str(option["value"])
            selected = " selected" if value == selected_value else ""
            options.append(
                f'<option value="{html.escape(value, quote=True)}"{selected}>'
                f'{html.escape(str(option["label"]))}</option>'
            )
        return (
            f'<select id="{html.escape(element_id, quote=True)}" '
            f'class="{html.escape(classes.strip(), quote=True)}"{role_attribute}>'
            f'{"".join(options)}</select>'
        )

    def _render_graph(self, props: dict[str, Any], customer_id: str | None) -> str:
        """Plotly Graph 컴포넌트를 오프라인 렌더링용 placeholder <div> 태그로 변환하고 정의 저장."""
        self.graph_number += 1
        graph_id = f"offline-plot-{self.graph_number}"
        component_id = props.get("id", "")
        figure = props["figure"]
        if hasattr(figure, "to_plotly_json"):
            figure = figure.to_plotly_json()
        config = props.get("config", {})
        self.graphs[graph_id] = {"figure": figure, "config": config}
        if component_id == "transaction-figure" and customer_id is not None:
            self.transaction_graph_id_by_customer[customer_id] = graph_id
            self.transaction_graphs[customer_id] = {
                asset_class: transaction_figure(customer_id, asset_class).to_plotly_json()
                for asset_class in TRADE_ASSET_CLASSES
            }
        component_attribute = (
            f' data-component-id="{html.escape(component_id, quote=True)}"'
            if component_id
            else ""
        )
        return (
            f'<div id="{graph_id}" class="offline-chart" '
            f'data-plotly-initialized="false"{component_attribute}></div>'
        )

    def _render_table(self, props: dict[str, Any]) -> str:
        """Dash DataTable 컴포넌트를 정적 HTML <table> 태그로 렌더링."""
        columns = props.get("columns", [])
        data = props.get("data", [])
        right_aligned = {
            rule["if"]["column_id"]
            for rule in props.get("style_cell_conditional", [])
            if isinstance(rule.get("if"), dict) and rule["if"].get("column_id")
        }
        header_style = _style_text(props.get("style_header", {}))
        cell_style = _style_text(props.get("style_cell", {}))
        header_cells = "".join(
            f'<th style="{html.escape(header_style, quote=True)}">{html.escape(str(column["name"]))}</th>'
            for column in columns
        )
        rows = []
        for row in data:
            cells = []
            for column in columns:
                column_id = column["id"]
                style = cell_style
                if column_id in right_aligned:
                    style = f"{style};text-align:right" if style else "text-align:right"
                cell_value = row.get(column_id, "")
                cells.append(
                    f'<td style="{html.escape(style, quote=True)}">'
                    f'{html.escape(str(cell_value))}</td>'
                )
            rows.append(f"<tr>{''.join(cells)}</tr>")
        return (
            '<div class="offline-table-wrap"><table class="offline-data-table">'
            f"<thead><tr>{header_cells}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        )


def build_html() -> str:
    """모든 고객 데이터와 차트, 인터랙티브 동작 스크립트가 포함된 완전한 독립형 HTML 문자열을 생성."""
    layout = app.layout
    if not isinstance(layout, Component):
        raise TypeError("The dashboard layout must be a Dash component.")

    customer_select = _find_by_id(layout, "customer-select")
    selector_wrap = _find_by_class(layout, "selector-wrap")
    title_row = _find_by_class(layout, "section-title-row")
    tabs = _find_by_id(layout, "customer-tabs")
    tab_components = tabs.to_plotly_json()["props"]["children"]
    tab_specs = [(tab.label, tab.value) for tab in tab_components]
    renderer = OfflineRenderer()
    summaries = []
    dashboards = []

    for _, customer in CUSTOMERS.iterrows():
        customer_id = str(customer["고객번호"])
        nba_panel = update_nba_panel(customer_id)
        nba_tabs = nba_panel[1].children
        summaries.append(
            dash_html.Div(
                update_customer_summary(customer_id),
                className="summary-view",
                **{"data-customer-id": customer_id, "hidden": customer_id != str(CUSTOMERS.iloc[0]["고객번호"])},
            )
        )
        tab_buttons = [
            dash_html.Button(
                label,
                type="button",
                className="tab tab-selected" if index == 0 else "tab",
                **{"data-tab-target": tab_value, "aria-selected": str(index == 0).lower()},
            )
            for index, (label, tab_value) in enumerate(tab_specs)
        ]
        tab_panels = [
            dash_html.Div(
                tab_content(value, customer_id),
                className="offline-tab-panel",
                **{
                    "data-tab-panel": value,
                    "hidden": index != 0,
                },
            )
            for index, (_, value) in enumerate(tab_specs)
        ]
        nba_tab_buttons = [
            dash_html.Button(
                tab.label,
                type="button",
                className="tab tab-selected" if index == 0 else "tab",
                **{
                    "data-nba-tab-target": tab.value,
                    "aria-selected": str(index == 0).lower(),
                },
            )
            for index, tab in enumerate(nba_tabs)
        ]
        nba_tab_panels = [
            dash_html.Div(
                tab.children,
                className="nba-tab-panel",
                **{
                    "data-nba-tab-panel": tab.value,
                    "hidden": index != 0,
                },
            )
            for index, tab in enumerate(nba_tabs)
        ]
        dashboards.append(
            dash_html.Div(
                [
                    dash_html.Section(
                        [
                            title_row,
                            dash_html.Div(tab_buttons, className="tabs offline-tabs"),
                            dash_html.Div(tab_panels, className="tab-panel"),
                        ],
                        className="card insights-card",
                    ),
                    dash_html.Aside(
                        [
                            nba_panel[0],
                            dash_html.Div(nba_tab_buttons, className="tabs nba-tabs"),
                            dash_html.Div(nba_tab_panels, className="nba-tab-panels"),
                        ],
                        className="card nba-panel",
                    ),
                ],
                className="content-grid offline-dashboard",
                **{
                    "data-customer-id": customer_id,
                    "hidden": customer_id != str(CUSTOMERS.iloc[0]["고객번호"]),
                },
            )
        )

    main = dash_html.Main(
        [
            dash_html.Section(
                [
                    dash_html.Div(
                        [selector_wrap.to_plotly_json()["props"]["children"][0], customer_select],
                        className="selector-wrap",
                    ),
                    dash_html.Div(summaries, className="snapshot-strip"),
                ],
                className="customer-header card",
            ),
            *dashboards,
        ],
        className="page-content",
    )
    page = dash_html.Div(
        [layout.children[0], main, layout.children[-1]],
        className="app-shell",
    )
    rendered_page = renderer.render(page)
    graph_data = {
        "graphs": renderer.graphs,
        "transactionGraphs": renderer.transaction_graphs,
        "transactionGraphIds": renderer.transaction_graph_id_by_customer,
    }
    css = (ROOT / "assets" / "theme.css").read_text(encoding="utf-8")
    offline_css = """
select.offline-select {
  min-height: 36px;
  padding: 7px 10px;
  color: var(--ink);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.offline-tabs { display: flex; flex-wrap: wrap; }
.offline-tabs button { cursor: pointer; background: transparent; }
.nba-tabs { display: flex; margin-top: 12px; }
.nba-tabs button { flex: 1 1 0; cursor: pointer; background: transparent; }
.nba-tab-panels { padding-top: 12px; }
.nba-tab-panel .nba-recommendation { margin-top: 0; }
.summary-view { display: contents; }
.offline-chart { width: 100%; min-height: 280px; }
.offline-table-wrap { width: 100%; overflow-x: auto; }
.offline-data-table { width: 100%; border-collapse: collapse; }
.offline-data-table th { font-weight: 700; color: var(--muted); border-bottom: 1px solid var(--line); }
.offline-data-table td { border: none; }
[hidden] { display: none !important; }
"""
    scripts = f"""
const dashboardData = JSON.parse(document.getElementById("offline-dashboard-data").textContent);
const dashboardRoot = document.getElementById("offline-dashboard-root");

function resizeVisibleCharts(dashboard) {{
  requestAnimationFrame(() => {{
    dashboard.querySelectorAll(".offline-tab-panel:not([hidden]) .offline-chart").forEach((chart) => {{
      if (chart.dataset.plotlyInitialized === "true") {{
        Plotly.Plots.resize(chart);
        return;
      }}
      const definition = dashboardData.graphs[chart.id];
      Plotly.newPlot(chart, definition.figure.data, definition.figure.layout, {{
        ...definition.config,
        responsive: true
      }}).then(() => {{
        chart.dataset.plotlyInitialized = "true";
      }});
    }});
  }});
}}

function activateCustomer(customerId) {{
  document.querySelectorAll("[data-customer-id]").forEach((element) => {{
    element.hidden = element.dataset.customerId !== customerId;
  }});
  const dashboard = Array.from(dashboardRoot.querySelectorAll(".offline-dashboard"))
    .find((element) => element.dataset.customerId === customerId);
  if (dashboard) {{
    setActiveTab(dashboard, "customer");
  }}
}}

function setActiveTab(dashboard, tabValue) {{
  dashboard.querySelectorAll("[data-tab-panel]").forEach((panel) => {{
    panel.hidden = panel.dataset.tabPanel !== tabValue;
  }});
  dashboard.querySelectorAll("[data-tab-target]").forEach((button) => {{
    const selected = button.dataset.tabTarget === tabValue;
    button.classList.toggle("tab-selected", selected);
    button.setAttribute("aria-selected", String(selected));
  }});
  resizeVisibleCharts(dashboard);
}}

function setActiveNbaTab(panel, tabValue) {{
  panel.querySelectorAll("[data-nba-tab-panel]").forEach((tabPanel) => {{
    tabPanel.hidden = tabPanel.dataset.nbaTabPanel !== tabValue;
  }});
  panel.querySelectorAll("[data-nba-tab-target]").forEach((button) => {{
    const selected = button.dataset.nbaTabTarget === tabValue;
    button.classList.toggle("tab-selected", selected);
    button.setAttribute("aria-selected", String(selected));
  }});
}}

dashboardRoot.addEventListener("change", (event) => {{
  if (event.target.id === "customer-select") {{
    activateCustomer(event.target.value);
    return;
  }}
  if (event.target.dataset.role !== "trade-asset-select") {{
    return;
  }}
  const dashboard = event.target.closest(".offline-dashboard");
  const customerId = dashboard.dataset.customerId;
  const graphId = dashboardData.transactionGraphIds[customerId];
  const chart = dashboard.querySelector('[data-component-id="transaction-figure"]');
  dashboardData.graphs[graphId].figure =
    dashboardData.transactionGraphs[customerId][event.target.value];
  if (chart.dataset.plotlyInitialized === "true") {{
    const figure = dashboardData.graphs[graphId].figure;
    Plotly.react(chart, figure.data, figure.layout, {{
      ...dashboardData.graphs[graphId].config,
      responsive: true
    }});
  }} else {{
    resizeVisibleCharts(dashboard);
  }}
}});

dashboardRoot.addEventListener("click", (event) => {{
  const nbaButton = event.target.closest("[data-nba-tab-target]");
  if (nbaButton) {{
    setActiveNbaTab(nbaButton.closest(".nba-panel"), nbaButton.dataset.nbaTabTarget);
    return;
  }}
  const button = event.target.closest("[data-tab-target]");
  if (button) {{
    setActiveTab(button.closest(".offline-dashboard"), button.dataset.tabTarget);
  }}
}});

window.addEventListener("resize", () => {{
  const dashboard = dashboardRoot.querySelector(".offline-dashboard:not([hidden])");
  if (dashboard) {{
    dashboard.querySelectorAll(".offline-chart[data-plotly-initialized='true']").forEach(Plotly.Plots.resize);
  }}
}});

activateCustomer(document.getElementById("customer-select").value);
"""
    return (
        "<!doctype html>\n"
        '<html lang="ko">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>고객 360° | WM 인사이트</title>\n'
        f"<style>\n{css}\n{offline_css}\n</style>\n"
        "</head>\n<body>\n"
        f'<div id="offline-dashboard-root">{rendered_page}</div>\n'
        '<script type="application/json" id="offline-dashboard-data">'
        f"{_json_text(graph_data)}"
        "</script>\n"
        f"<script>\n{get_plotlyjs()}\n</script>\n"
        f"<script>\n{scripts}\n</script>\n"
        "</body>\n</html>\n"
    )


def export_html(output_path: Path) -> Path:
    """오프라인 대시보드 HTML을 생성하여 지정된 경로에 파일로 저장."""
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html(), encoding="utf-8")
    return output_path


def main() -> None:
    """CLI 인자(--output)를 처리하여 독립형 오프라인 대시보드 HTML 파일을 생성하는 메인 함수."""
    parser = argparse.ArgumentParser(description="Create a self-contained offline dashboard HTML file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "customer360_offline.html",
        help="HTML output path (default: customer360_offline.html in the project folder)",
    )
    arguments = parser.parse_args()
    output_path = export_html(arguments.output)
    print(f"Offline dashboard created: {output_path}")


if __name__ == "__main__":
    main()
