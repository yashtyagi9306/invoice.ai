import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.security import verify_api_key
from backend.models.analytics import FinancialMetrics, OverviewMetrics, RiskMetrics, TrendPoint, VendorMetric
from backend.services import analytics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", dependencies=[Depends(verify_api_key)])

GRANULARITY_PATTERN = "^(day|week|month|quarter|year)$"


@router.get("/overview", response_model=OverviewMetrics)
def overview():
    start = time.perf_counter()
    try:
        result = analytics_service.get_overview()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Analytics overview failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Analytics temporarily unavailable") from exc
    logger.info("Analytics overview served in %sms", int((time.perf_counter() - start) * 1000))
    return result


@router.get("/vendors", response_model=list[VendorMetric])
def vendors(limit: int = Query(default=10, ge=1, le=50)):
    try:
        return analytics_service.get_vendor_analytics(limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vendor analytics failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Analytics temporarily unavailable") from exc


@router.get("/risk", response_model=RiskMetrics)
def risk():
    try:
        return analytics_service.get_risk_analytics()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Risk analytics failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Analytics temporarily unavailable") from exc


@router.get("/trends", response_model=list[TrendPoint])
def trends(granularity: str = Query(default="month", pattern=GRANULARITY_PATTERN)):
    try:
        return analytics_service.get_trends(granularity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning("Trend analytics failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Analytics temporarily unavailable") from exc


@router.get("/financial", response_model=FinancialMetrics)
def financial(granularity: str = Query(default="month", pattern=GRANULARITY_PATTERN)):
    try:
        return analytics_service.get_financial_analytics(granularity)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Financial analytics failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Analytics temporarily unavailable") from exc
