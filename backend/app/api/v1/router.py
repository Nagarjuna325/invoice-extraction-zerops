# from fastapi import APIRouter
# from app.api.v1.endpoints import health, upload

# api_router = APIRouter()
# api_router.include_router(health.router, prefix="/health", tags=["health"])
# api_router.include_router(upload.router, prefix="/invoices", tags=["upload"])


# """
# API v1 router - includes all endpoints
# """
# from fastapi import APIRouter
# from app.api.v1.endpoints import upload, corrections

# router = APIRouter()

# # Include upload endpoints
# router.include_router(
#     upload.router,
#     prefix="/invoices",
#     tags=["invoices"]
# )

# # Include correction endpoints
# router.include_router(
#     corrections.router,
#     prefix="/invoices",
#     tags=["corrections"]
# )



"""
API v1 router - includes all endpoints
"""
from fastapi import APIRouter
from app.api.v1.endpoints import upload, corrections

# Create main API router
api_router = APIRouter()

# Include upload endpoints
api_router.include_router(
    upload.router,
    prefix="/invoices",
    tags=["invoices"]
)

# Include correction endpoints
api_router.include_router(
    corrections.router,
    prefix="/invoices",
    tags=["corrections"]
)