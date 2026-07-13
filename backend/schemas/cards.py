from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict




Priority = Literal["low", "medium", "high"]


class SCardCreate(BaseModel):
    """Схема для создания карточки."""
    title: str
    description: str | None = None
    column_id: int
    order: int | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None
    priority: Priority | None = None
    file_id: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Задача 1",
                    "description": "Описание задачи",
                    "column_id": 3,
                    "order": 1,
                    "assignee_id": 5,
                    "due_date": "2025-02-01T10:00:00Z",
                    "priority": "high",
                    "file_id": None
                }
            ]
        }
    )


class SCardUpdate(BaseModel):
    """Схема для обновления карточки (без column_id и order). Требуется версия."""
    title: str | None = None
    description: str | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None
    priority: Priority | None = None
    file_id: int | None = None
    version: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Обновлённая задача",
                    "description": "Новое описание",
                    "priority": "low",
                    "version": 2
                }
            ]
        }
    )


class SCardMove(BaseModel):
    """Схема для перемещения карточки."""
    column_id: int
    order: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "column_id": 4,
                    "order": 2
                }
            ]
        }
    )


class CardResponse(BaseModel):
    """Схема ответа с данными карточки."""
    id: int
    column_id: int
    title: str
    description: str | None = None
    order: int
    author_id: int
    assignee_id: int | None = None
    due_date: datetime | None = None
    priority: Priority | None = None
    file_id: int | None = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 101,
                    "column_id": 3,
                    "title": "Задача 1",
                    "description": "Описание задачи",
                    "order": 1,
                    "author_id": 10,
                    "assignee_id": 5,
                    "due_date": "2025-02-01T10:00:00Z",
                    "priority": "high",
                    "file_id": None,
                    "version": 4,
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    )


class CardListResponse(BaseModel):
    """Схема для списка карточек с пагинацией."""
    items: list[CardResponse]
    next_cursor: str | None = None
    previous_cursor: str | None = None