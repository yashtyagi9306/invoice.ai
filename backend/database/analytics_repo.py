from typing import Any

from backend.database.connection import get_supabase

VALID_GRANULARITIES = {"day", "week", "month", "quarter", "year"}


def fetch_overview() -> dict[str, Any]:
    result = get_supabase().table("v_analytics_overview").select("*").execute()
    return result.data[0] if result.data else {}


def fetch_vendor_summary(limit: int = 10) -> list[dict[str, Any]]:
    result = (
        get_supabase()
        .table("v_vendor_summary")
        .select("*")
        .order("total_spend", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def fetch_risk_distribution() -> list[dict[str, Any]]:
    return get_supabase().table("v_risk_distribution").select("*").execute().data


def fetch_currency_distribution() -> list[dict[str, Any]]:
    return get_supabase().table("v_currency_distribution").select("*").execute().data


def fetch_rule_violation_frequency(limit: int = 10) -> list[dict[str, Any]]:
    result = get_supabase().table("v_rule_violation_frequency").select("*").limit(limit).execute()
    return result.data


def fetch_trends(granularity: str) -> list[dict[str, Any]]:
    if granularity not in VALID_GRANULARITIES:
        raise ValueError(f"Invalid granularity: {granularity}")
    result = get_supabase().rpc("fn_analytics_trends", {"p_granularity": granularity}).execute()
    return result.data
