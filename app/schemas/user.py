from datetime import datetime
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}

    # from client to FastAPI
    # (Router to Pydantic schema veification, 
    # User(id="abc", username="alice", ...) → {"id": "abc", "username": "alice", ...}
    # now FastAPI serizlize a User ORM object into UserResponse
