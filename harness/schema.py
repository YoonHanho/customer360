"""Required CSV columns for the synthetic customer-360 data contract."""

REQUIRED_COLUMNS = {
    "customers": {"customer_id", "name_masked", "segment", "risk_profile", "branch", "manager", "join_date"},
    "accounts": {"account_id", "customer_id", "type", "balance", "eval_amount"},
    "holdings": {"holding_id", "customer_id", "product_id", "amount", "pnl", "maturity_date"},
    "products": {"product_id", "name", "category", "risk_grade"},
    "transactions": {"tx_id", "customer_id", "date", "type", "amount", "channel"},
    "consultations": {"consult_id", "customer_id", "date", "channel", "topic_code", "resolved", "csat", "summary_masked"},
    "chatbot_logs": {"log_id", "customer_id", "date", "intent_code", "escalated"},
    "market_series": {"date", "index_code", "close"},
    "news": {"news_id", "date", "tag", "sentiment", "title_masked", "source"},
    "house_view": {"report_id", "date", "asset_class", "outlook", "headline", "report_name"},
    "allocation_strategy": {"segment", "asset_class", "target_pct"},
    "nba_catalog": {"nba_id", "trigger_type", "trigger_cond", "action", "template"},
    "nba_history": {"nba_run_id", "customer_id", "nba_id", "date", "status"},
}
