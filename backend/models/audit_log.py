from datetime import datetime, timezone
from sqlalchemy import ForeignKey, DateTime, Text, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database import Model
import enum




class ActionType(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    ASSIGN = "assign"


class EntityType(str, enum.Enum):
    BOARD = "board"
    COLUMN = "column"
    CARD = "card"
    COMMENT = "comment"
    FILE = "file"
    BOARD_MEMBER = "board_member"



class AuditLogOrm(Model):
    __tablename__ = "audit_log"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[ActionType] = mapped_column(Enum(ActionType), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), nullable=False)
    entity_id: Mapped[int] = mapped_column(nullable=False)
    changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # опционально, что изменилось
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )