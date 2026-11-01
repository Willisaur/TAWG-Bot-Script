from constants import CONFIG
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from utils.logger import configure_logger


# configure_logger()

app = FastAPI(
    title="TAWG Bot",
    description="Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=[CONFIG.FRONTEND_DOMAIN],
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# routes
from root import router as root
from analyze import router as analyze

app.include_router(root)
app.include_router(analyze)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=5001, reload=True)
