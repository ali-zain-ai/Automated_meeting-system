"""
MindFuelByAli — FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.routes import slots, bookings, admin

# Initialize FastAPI app
app = FastAPI(
    title="MindFuelByAli API",
    description="Consultation & Meeting Scheduling Platform for AI, ML & Tech",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
settings = get_settings()
allowed_origins = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(slots.router)
app.include_router(bookings.router)
app.include_router(admin.router)


# Health check
@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MindFuelByAli API",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "MindFuelByAli API",
        "version": "1.0.0",
        "booking_system": "active",
    }
