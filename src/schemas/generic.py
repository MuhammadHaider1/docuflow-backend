from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "total": 3,
                "page": 1,
                "page_size": 10,
                "total_pages": 1,
            }
        }
    }
