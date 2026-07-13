from datetime import datetime
from pydantic import BaseModel, ConfigDict




class AuditLogResponse(BaseModel):
    """Схема ответа для записи аудита."""
    id: int
    user_id: int
    action: str
    entity_type: str
    entity_id: int
    changes: dict | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "user_id": 10,
                    "action": "UPDATE_CARD",
                    "entity_type": "card",
                    "entity_id": 101,
                    "changes": {"title": "old", "new": "new"},
                    "created_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    )


class AuditLogListResponse(BaseModel):
    """Схема для списка записей аудита с пагинацией."""
    items: list[AuditLogResponse]
    next_cursor: str | None = None
    previous_cursor: str | None = None