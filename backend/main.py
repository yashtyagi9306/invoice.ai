import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.analytics import router as analytics_router
from backend.api.invoice import router as invoice_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Invoice AI Platform", version="0.1.0")
app.include_router(invoice_router)
app.include_router(analytics_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s: %s", request.url.path, type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok"}
