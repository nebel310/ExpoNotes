from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict




class SColumnCreate(BaseModel):
    """Схема для создания колонки."""
    title: str
    order: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "В работе",
                    "order": 1
                }
            ]
        }
    )


class SColumnUpdate(BaseModel):
    """Схема для обновления колонки. Требуется версия."""
    title: str | None = None
    order: int | None = None
    version: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Новое название",
                    "version": 1
                }
            ]
        }
    )


class ColumnResponse(BaseModel):
    """Схема ответа с данными колонки."""
    id: int
    board_id: int
    title: str
    order: int
    version: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "board_id": 1,
                    "title": "В работе",
                    "order": 1,
                    "version": 3,
                    "created_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    )


class ColumnListResponse(BaseModel):
    """Схема для списка колонок с пагинацией."""
    items: list[ColumnResponse]
    next_cursor: str | None = None
    previous_cursor: str | None = None