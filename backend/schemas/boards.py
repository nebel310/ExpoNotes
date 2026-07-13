from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict




class SBoardCreate(BaseModel):
    """Схема для создания доски."""
    title: str
    description: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Моя доска",
                    "description": "Описание доски"
                }
            ]
        }
    )


class SBoardUpdate(BaseModel):
    """Схема для обновления доски. Требуется версия для защиты от коллизий."""
    title: str | None = None
    description: str | None = None
    version: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Новое название доски",
                    "description": "Обновлённое описание",
                    "version": 2
                }
            ]
        }
    )


class BoardResponse(BaseModel):
    """Схема ответа с данными доски."""
    id: int
    title: str
    description: str | None = None
    owner_id: int
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "title": "Моя доска",
                    "description": "Описание доски",
                    "owner_id": 10,
                    "version": 2,
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    )


class BoardListResponse(BaseModel):
    """Схема для списка досок с пагинацией."""
    items: list[BoardResponse]
    next_cursor: str | None = None
    previous_cursor: str | None = None