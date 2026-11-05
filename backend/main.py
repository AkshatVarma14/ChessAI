"""FastAPI application entry point."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes.game import router as game_router

app = FastAPI(
    title="Chess AI API",
    description="Authoritative REST API for Player vs Player and Player vs Computer Chess",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware configuration for local Vite development server
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(game_router)


@app.get("/api/health", tags=["Health"])
def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok", "service": "chess-ai-backend"}


@app.get("/", tags=["Health"])
def root_redirect() -> dict:
    """Root metadata response."""
    return {
        "name": "Chess AI API",
        "docs": "/docs",
        "health": "/api/health",
        "version": "0.2.0",
    }


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Guarantees unhandled internal exceptions return clean JSON instead of raw stack traces."""
    # Note: HTTPExceptions are handled by FastAPI before reaching here
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred while processing the request.",
        },
    )
