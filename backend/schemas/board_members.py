from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict




MemberRole = Literal["reader", "writer", "owner"]


class SBoardMemberAdd(BaseModel):
    """Схема для добавления участника."""
    user_id: int
    role: MemberRole

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": 5,
                    "role": "writer"
                }
            ]
        }
    )


class SBoardMemberUpdate(BaseModel):
    """Схема для изменения роли участника."""
    role: MemberRole

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "role": "owner"
                }
            ]
        }
    )


class BoardMemberResponse(BaseModel):
    """Схема ответа с данными об участнике доски."""
    id: int
    board_id: int
    user_id: int
    role: MemberRole
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "board_id": 1,
                    "user_id": 5,
                    "role": "writer",
                    "created_at": "2025-01-01T12:00:00Z"
                }
            ]
        }
    )


class BoardMemberListResponse(BaseModel):
    """Схема для списка участников с пагинацией."""
    items: list[BoardMemberResponse]
    next_cursor: str | None = None
    previous_cursor: str | None = None