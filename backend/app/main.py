from app.routes.user_routes import user_router
from app.db.database import engine
from app.db.database import Base
from fastapi import FastAPI

from app.db.models import *

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def root():
    return {"Hello": "World"}

app.include_router(user_router)