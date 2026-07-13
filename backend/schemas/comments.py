from datetime import datetime
from pydantic import BaseModel, ConfigDict




class SCommentCreate(BaseModel):
    """Схема для создания комментария."""
    text: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": "Это важный комментарий"
                }
            ]
        }
    )


class SCommentUpdate(BaseModel):
    """Схема для обновления комментария."""
    text: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": "Обновлённый текст комментария"
                }
            ]
        }
    )


class CommentResponse(BaseModel):
    """Схема ответа с данными комментария."""
    id: int
    card_id: int
    author_id: int
    text: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "card_id": 101,
                    "author_id": 10,
                    "text": "Это важный комментарий",
                    "created_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    )


class CommentListResponse(BaseModel):
    """Схема для списка комментариев с пагинацией."""
    items: list[CommentResponse]
    next_cursor: str | None = None
    previous_cursor: str | None = None