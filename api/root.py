from constants import ENV
from fastapi import APIRouter
# from fastapi.responses import FileResponse


router = APIRouter()

# @router.get("/favicon.ico", include_in_schema=False)
# async def favicon():
#     return FileResponse(("public/favicon.ico", "/favicon.ico")[ENV=='prod'])

@router.get('/')
def root():
    return {
        "service": "tawg-bot-backend",
        "status": "ok"
    }
