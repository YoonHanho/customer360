import unittest
from pathlib import Path

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

    def test_high_interest_prediction_cards_use_emphasis_styles(self):
        prediction_cards = tab_content("predictions", "12345678").children
        self.assertEqual(len(prediction_cards), 16)
        emphasized = [
            card
            for card in prediction_cards
            if card.children[2].children == "관심높음"
        ]
        self.assertGreater(len(emphasized), 0)
        self.assertTrue(all("prediction-highlight" in card.className for card in emphasized))

    def test_supplied_logo_is_served_from_dashboard_assets(self):
        response = app.server.test_client().get("/assets/mirae_asset_logo.png")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("image/png"))
        response.close()


if __name__ == "__main__":
    unittest.main()
