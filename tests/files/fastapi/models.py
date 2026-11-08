from pydantic import BaseModel


class User(BaseModel):
    name: str
    email: str


class UnusedModel(BaseModel):
    value: int
