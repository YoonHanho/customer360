import unittest
from pathlib import Path

from harness.data_loader import REQUIRED_COLUMNS, load_data
from harness.nba_engine import LEGAL_SUITABILITY_FLOOR, recommend_actions


ROOT = Path(__file__).resolve().parents[1]


class DashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(ROOT / "data")

    def test_all_thirteen_datasets_match_required_contract(self):
        self.assertEqual(set(self.data), set(REQUIRED_COLUMNS))
        self.assertEqual(len(self.data["customers"]), 10)
        self.assertEqual(len(list((ROOT / "data").glob("*.csv"))), 13)

    def test_relationships_reference_existing_customers_and_products(self):
        customer_ids = set(self.data["customers"]["customer_id"])
        product_ids = set(self.data["products"]["product_id"])
        self.assertTrue(set(self.data["holdings"]["customer_id"]).issubset(customer_ids))
        self.assertTrue(set(self.data["holdings"]["product_id"]).issubset(product_ids))
        self.assertTrue(set(self.data["transactions"]["customer_id"]).issubset(customer_ids))


class NbaEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(ROOT / "data")

    def test_every_customer_has_an_explainable_action_and_suitability_gate(self):
        for customer in self.data["customers"].itertuples():
            actions = recommend_actions(customer, self.data["holdings"], self.data["products"])
            with self.subTest(customer_id=customer.customer_id):
                self.assertGreater(len(actions), 0)
                self.assertLessEqual(len(actions), 3)
                self.assertEqual(actions, sorted(actions, key=lambda action: action["score"], reverse=True))
                self.assertTrue(all(action["eligible"] for action in actions))
                self.assertTrue(all(action["suitability"] >= LEGAL_SUITABILITY_FLOOR for action in actions))
                self.assertTrue(all(action["why"] for action in actions))


if __name__ == "__main__":
    unittest.main()
