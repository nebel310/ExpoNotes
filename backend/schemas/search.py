from pydantic import BaseModel, ConfigDict
from schemas.cards import CardResponse




class SearchCardItem(CardResponse):
    """Карточка с идентификатором доски для результатов поиска."""
    board_id: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [{
                "id": 101,
                "column_id": 3,
                "title": "Задача 1",
                "description": "Описание",
                "order": 1,
                "author_id": 10,
                "assignee_id": 5,
                "due_date": "2025-02-01T10:00:00Z",
                "priority": "high",
                "file_id": None,
                "version": 4,
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
                "board_id": 1
            }]
        }
    )

class SearchCardResponse(BaseModel):
    """Схема ответа для результатов поиска карточек с board_id."""
    items: list[SearchCardItem]
    next_cursor: str | None = None
    previous_cursor: str | None = None