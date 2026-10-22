from fastapi import FastAPI
from app.routes import claims

app = FastAPI(
    title="Campus Lost & Found API",
    version="0.1.0",
    description="API for reporting, searching, and claiming lost or found items on campus.",
)
app.include_router(claims.router)