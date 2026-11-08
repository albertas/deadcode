from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    BOOKS = 'books'
    MOVIES = 'movies'


class Dimensions(BaseModel):
    width: float
    height: float


class Item(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    price: float
    tax: float | None = None
    category: Category = Category.BOOKS
    dimensions: Dimensions | None = None

    @field_validator('name')
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        return value.strip()


class ItemCreate(BaseModel):
    name: str
    price: float


class UnusedModel(BaseModel):
    value: int
