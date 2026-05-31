from pydantic import BaseModel

class ReponseModel(BaseModel):
    message: str
    success: bool
