from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.endpoints import router
from app.utils.exceptions import PDFProcessingError

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-grade PDF processing API with OpenAI integration",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["PDF Processing"])

# Global exception handler
@app.exception_handler(PDFProcessingError)
async def pdf_processing_exception_handler(request, exc: PDFProcessingError):
    logger.error("pdf_processing_exception", error=str(exc))
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": exc.message, "details": exc.details},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": str(exc.detail)},
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_shutdown")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,  # Use our custom logging
    )
