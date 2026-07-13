from sqlalchemy import select
from database import new_session
from models.audit_log import AuditLogOrm




class AuditLogRepository:
    """Репозиторий для работы с логами аудита."""

    @classmethod
    async def get_logs(
        cls,
        entity_type: str | None = None,
        entity_id: int | None = None,
        cursor: str | None = None,
        direction: str = "after",
        limit: int = 10
    ) -> tuple[list[AuditLogOrm], str | None, str | None]:
        """
        Возвращает список записей аудита с фильтрацией и пагинацией.
        entity_type: 'board', 'column', 'card', 'comment', 'file', 'board_member'
        entity_id: ID конкретной сущности.
        """
        async with new_session() as session:
            base_query = select(AuditLogOrm)

            if entity_type:
                base_query = base_query.where(AuditLogOrm.entity_type == entity_type)
            if entity_id is not None:
                base_query = base_query.where(AuditLogOrm.entity_id == entity_id)

            cursor_id = None
            if cursor:
                try:
                    cursor_id = int(cursor)
                except (ValueError, TypeError):
                    raise ValueError("Некорректный курсор")

            if direction == "after":
                if cursor_id is not None:
                    query = base_query.where(AuditLogOrm.id > cursor_id).order_by(AuditLogOrm.id.asc())
                else:
                    query = base_query.order_by(AuditLogOrm.id.asc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                items = result.scalars().all()
                logs = items[:limit]
                next_id = logs[-1].id if len(items) > limit else None
                prev_id = logs[0].id if cursor_id is not None else None

            elif direction == "before":
                if cursor_id is not None:
                    query = base_query.where(AuditLogOrm.id < cursor_id).order_by(AuditLogOrm.id.desc())
                else:
                    query = base_query.order_by(AuditLogOrm.id.desc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                desc_items = result.scalars().all()
                has_previous = len(desc_items) > limit
                page_items_desc = desc_items[:limit]
                logs = list(reversed(page_items_desc))
                next_id = logs[-1].id if logs else None
                prev_id = logs[0].id if has_previous else None
            else:
                raise ValueError("Недопустимое направление")

            next_cursor = str(next_id) if next_id is not None else None
            prev_cursor = str(prev_id) if prev_id is not None else None
            return logs, next_cursor, prev_cursor


    @classmethod
    async def get_log_by_id(cls, log_id: int) -> AuditLogOrm | None:
        """Получает запись аудита по ID."""
        async with new_session() as session:
            query = select(AuditLogOrm).where(AuditLogOrm.id == log_id)
            result = await session.execute(query)
            return result.scalars().first()