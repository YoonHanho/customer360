import unittest
from pathlib import Path

from export_html import build_html
from harness.data_loader import REQUIRED_COLUMNS, load_data
from pages.scr002_customer360 import (
    PREDICTION_TOPICS,
    app,
    tab_content,
    update_customer_summary,
    update_nba_panel,
)


ROOT = Path(__file__).resolve().parents[1]


class DashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(ROOT / "data")

    def test_all_fourteen_csvs_match_the_requested_contract(self):
        expected_files = {f"{name}.csv" for name in REQUIRED_COLUMNS}
        actual_files = {path.name for path in (ROOT / "data").glob("*.csv")}
        self.assertEqual(actual_files, expected_files)
        self.assertEqual(set(self.data), set(REQUIRED_COLUMNS))
        self.assertEqual(len(self.data["고객"]), 10)

    def test_customer_references_and_periods_are_consistent(self):
        customer_ids = set(self.data["고객"]["고객번호"])
        for name, frame in self.data.items():
            if name != "고객":
                self.assertTrue(set(frame["고객번호"]).issubset(customer_ids), name)
        self.assertEqual(self.data["잔고추이"].groupby("고객번호").size().unique().tolist(), [36])
        self.assertEqual(self.data["거래금액"].groupby("고객번호").size().unique().tolist(), [60])
        self.assertEqual(self.data["투자수익률"].groupby("고객번호").size().unique().tolist(), [12])
        self.assertEqual(self.data["앱접속일수"].groupby("고객번호").size().unique().tolist(), [12])

    def test_asset_mix_and_customer_example_values(self):
        weights = self.data["자산비중"].groupby("고객번호")["비중"].sum()
        self.assertTrue(((weights - 1).abs() < 0.001).all())
        first_customer = self.data["고객"].iloc[0]
        self.assertEqual(first_customer["고객번호"], "12345678")
        self.assertEqual(first_customer["투자성향"], "위험중립형")
        self.assertEqual(first_customer["만기일"], "2027-01-23")
        self.assertEqual(first_customer["관리점"], "여의도지점")
        self.assertEqual(first_customer["PB"], "김미래PB")
        self.assertEqual(first_customer["직장정보"], "SK하이닉스")

    def test_each_customer_has_sixteen_prediction_cards_and_three_nba_proposals(self):
        predictions = self.data["예측"]
        counts = predictions.groupby("고객번호").size()
        self.assertTrue((counts == 16).all())
        self.assertEqual(set(predictions["예측주제"]), set(PREDICTION_TOPICS))
        nba = self.data["NBA"]
        self.assertEqual(nba.groupby("고객번호").size().unique().tolist(), [3])
        first_customer_nba = nba.loc[nba["고객번호"] == "12345678"].sort_values("제안순서")
        self.assertEqual(first_customer_nba["제안순서"].tolist(), [1, 2, 3])
        first_proposal = first_customer_nba.iloc[0]["NextBestAction"]
        self.assertEqual(
            first_proposal,
            "포트폴리오 점검 / 자산배분 및 목표 비중 점검 / "
            "총 보유 평가액 184,221,319원 기준으로 분산과 목표 비중을 확인합니다.",
        )
        self.assertTrue(all(len(item.split(" / ")) == 3 for item in nba["NextBestAction"]))

    def test_all_requested_dashboard_tabs_render(self):
        customer_id = "12345678"
        for tab in ["customer", "assets", "transactions", "behavior", "predictions"]:
            with self.subTest(tab=tab):
                self.assertIsNotNone(tab_content(tab, customer_id))

    def test_summary_and_nba_show_the_requested_example_values(self):
        metrics = update_customer_summary("12345678")
        rendered_metrics = [
            (metric.children[0].children, metric.children[1].children, metric.children[2].children)
            for metric in metrics
        ]
        self.assertIn(("총자산 AUM", "1.8억", "최근 1개월 +6.2%"), rendered_metrics)
        self.assertIn(("투자성향", "위험중립형", "2027-01-23 만기"), rendered_metrics)
        self.assertIn(("이탈위험", "28점", "매우 낮음"), rendered_metrics)
        self.assertIn(("투자수익률(1년)", "+6.2%", "전월 대비 +2.4%p"), rendered_metrics)
        self.assertIn(("주거래상품", "국내주식", "잔고비중 50%"), rendered_metrics)
        nba = update_nba_panel("12345678")
        self.assertEqual(len(nba) - 1, 3)
        self.assertEqual(nba[1].children[1].children, "포트폴리오 점검")
        self.assertEqual(nba[1].children[2].children, "자산배분 및 목표 비중 점검")
        self.assertIn("184,221,319원", nba[1].children[3].children)
        self.assertFalse(any("nba-score" in card.className for card in nba[1:]))

    def test_turnover_is_rendered_as_a_percentage(self):
        turnover_grid = tab_content("transactions", "12345685").children[2].children[1]
        rendered_turnover = {
            tile.children[0].children: tile.children[1].children
            for tile in turnover_grid.children
        }
        self.assertEqual(rendered_turnover, {"국내주식": "187%", "해외주식": "66%"})

    def test_prediction_cards_use_styles_for_each_interpretation(self):
        prediction_cards = tab_content("predictions", "12345678").children
        self.assertEqual(len(prediction_cards), 16)
        style_by_label = {
            "관심매우높음": "prediction-very-high",
            "관심높음": "prediction-high",
            "관심보통": "prediction-neutral",
            "관심낮음": "prediction-neutral",
            "매우 낮음": "prediction-neutral",
        }
        for card in prediction_cards:
            label = card.children[2].children
            expected_style = style_by_label[label]
            self.assertIn(expected_style, card.className)
            self.assertIn(f"{expected_style}-label", card.children[2].className)

    def test_supplied_logo_is_served_from_dashboard_assets(self):
        response = app.server.test_client().get("/assets/mirae_asset_logo.png")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("image/png"))
        response.close()

    def test_offline_export_embeds_assets_and_preserves_dashboard_controls(self):
        offline_html = build_html()
        self.assertIn('data:image/png;base64,', offline_html)
        self.assertIn("Plotly.newPlot", offline_html)
        self.assertIn("Plotly.react", offline_html)
        self.assertIn(">187%</strong>", offline_html)
        self.assertEqual(offline_html.count('class="content-grid offline-dashboard"'), 10)
        self.assertEqual(offline_html.count('id="trade-asset-select-'), 10)
        self.assertNotRegex(
            offline_html,
            r"""<(?:script|link)\b[^>]*\b(?:src|href)\s*=\s*["']https?://""",
        )


if __name__ == "__main__":
    unittest.main()
