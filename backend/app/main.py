from app.routes.equity_routes import equity_router
from app.routes.strategy_routes import strategy_router
from app.routes.user_routes import user_router
from app.db.database import engine
from app.db.database import Base
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.db.models import *

# Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):
    print("\n=== ERROR ===")
    print(type(exc).__name__)
    print(str(exc))
    print("=============\n")

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

origins = [
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

@app.get("/")
def root():
    return {"Hello": "World"}

app.include_router(user_router)
app.include_router(strategy_router)
app.include_router(equity_router)