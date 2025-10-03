from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Kali Personal Assistant API",
    description="FastAPI backend for Kali Personal Assistant",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Kali Personal Assistant API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Import your routers here
# from .routers import example_router
# app.include_router(example_router.router, prefix="/api/v1")
