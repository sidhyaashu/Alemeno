from fastapi import FastAPI
from app.core.config import settings
from app.db.database import engine, Base
from app.api.v1.api_router import api_router
from app.middleware.error_handler import add_exception_handlers

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for asynchronous transaction processing and LLM classification",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add global exception handlers
add_exception_handlers(app)

# Include API V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}
