import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import init_db, get_db
from backend.app.schemas import HealthResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("voxlead")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing VoxLead AI backend...")
    try:
        init_db()
        logger.info("Database and pgvector initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    yield
    logger.info("Shutting down VoxLead AI backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous AI Sales Voice Agent MVP with RAG, Lead Intelligence, and Business Integrations",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint validating database and pgvector extension."""
    db_status = "connected"
    pgvector_status = "active"

    try:
        # Check DB connection
        db.execute(text("SELECT 1"))
        # Check pgvector extension
        res = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
        if not res:
            pgvector_status = "missing"
    except Exception as e:
        db_status = f"error: {str(e)}"
        pgvector_status = "unknown"

    return HealthResponse(
        status="healthy" if db_status == "connected" and pgvector_status == "active" else "degraded",
        version=settings.VERSION,
        database=db_status,
        pgvector=pgvector_status,
        mock_mode=settings.MOCK_MODE,
    )

@app.get("/ready", tags=["System"])
def readiness_check():
    return {"status": "ready"}

# Include API routes
from backend.app.api.routes import router as api_router
app.include_router(api_router, prefix=settings.API_PREFIX)
