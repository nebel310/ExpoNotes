from sqlalchemy import select, and_, delete
from database import new_session
from models.board_members import BoardMemberOrm, MemberRole
from models.boards import BoardOrm
from models.audit_log import AuditLogOrm, ActionType, EntityType




class BoardMemberRepository:
    """Репозиторий для управления участниками доски."""

    @classmethod
    async def get_member_role(cls, board_id: int, user_id: int) -> MemberRole | None:
        """Возвращает роль пользователя в доске или None, если не член."""
        async with new_session() as session:
            board = await session.get(BoardOrm, board_id)
            if board and board.owner_id == user_id:
                return MemberRole.OWNER
            query = select(BoardMemberOrm.role).where(
                and_(BoardMemberOrm.board_id == board_id, BoardMemberOrm.user_id == user_id)
            )
            result = await session.execute(query)
            row = result.first()
            return row[0] if row else None


    @classmethod
    async def _check_owner(cls, board_id: int, user_id: int) -> bool:
        """Проверяет, является ли пользователь владельцем доски (сама доска должна существовать)."""
        async with new_session() as session:
            board = await session.get(BoardOrm, board_id)
            if not board:
                raise ValueError("Доска не найдена")
            return board.owner_id == user_id


    @classmethod
    async def add_member(cls, board_id: int, user_id: int, role: MemberRole, requester_id: int) -> BoardMemberOrm:
        """Добавляет участника в доску. Только владелец может добавлять."""
        async with new_session() as session:
            # 1. Проверить существование доски
            board = await session.get(BoardOrm, board_id)
            if not board:
                raise ValueError("Доска не найдена")

            # 2. Проверить права requester'а
            if board.owner_id != requester_id:
                raise ValueError("Только владелец может добавлять участников")

            # 3. Проверить, не состоит ли пользователь уже в доске
            existing = await session.execute(
                select(BoardMemberOrm).where(
                    and_(BoardMemberOrm.board_id == board_id, BoardMemberOrm.user_id == user_id)
                )
            )
            if existing.scalars().first():
                raise ValueError("Пользователь уже является участником доски")

            member = BoardMemberOrm(
                board_id=board_id,
                user_id=user_id,
                role=role
            )
            session.add(member)
            await session.flush()  # чтобы получить member.id

            # Запись в аудит
            audit = AuditLogOrm(
                user_id=requester_id,
                action=ActionType.CREATE,
                entity_type=EntityType.BOARD_MEMBER,
                entity_id=member.id,
                changes={"board_id": board_id, "user_id": user_id, "role": role}
            )
            session.add(audit)

            await session.commit()
            await session.refresh(member)
            return member


    @classmethod
    async def get_members(cls, board_id: int, cursor: str | None = None, direction: str = "after", limit: int = 10):
        async with new_session() as session:
            base_query = select(BoardMemberOrm).where(BoardMemberOrm.board_id == board_id)

            cursor_id = None
            if cursor:
                try:
                    cursor_id = int(cursor)
                except (ValueError, TypeError):
                    raise ValueError("Некорректный курсор")

            if direction == "after":
                if cursor_id is not None:
                    query = base_query.where(BoardMemberOrm.id > cursor_id).order_by(BoardMemberOrm.id.asc())
                else:
                    query = base_query.order_by(BoardMemberOrm.id.asc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                items = result.scalars().all()
                members = items[:limit]
                next_id = members[-1].id if len(items) > limit else None
                prev_id = members[0].id if cursor_id is not None else None

            elif direction == "before":
                if cursor_id is not None:
                    query = base_query.where(BoardMemberOrm.id < cursor_id).order_by(BoardMemberOrm.id.desc())
                else:
                    query = base_query.order_by(BoardMemberOrm.id.desc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                desc_items = result.scalars().all()
                has_previous = len(desc_items) > limit
                page_items_desc = desc_items[:limit]
                members = list(reversed(page_items_desc))
                next_id = members[-1].id if members else None
                prev_id = members[0].id if has_previous else None
            else:
                raise ValueError("Недопустимое направление")

            next_cursor = str(next_id) if next_id is not None else None
            prev_cursor = str(prev_id) if prev_id is not None else None

            return members, next_cursor, prev_cursor


    @classmethod
    async def update_member_role(cls, board_id: int, member_id: int, new_role: MemberRole, requester_id: int) -> BoardMemberOrm:
        """Изменяет роль участника. Только владелец доски."""
        async with new_session() as session:
            # 1. Найти запись участника и проверить, что она относится к указанной доске
            member = await session.get(BoardMemberOrm, member_id)
            if not member:
                raise ValueError("Запись участника не найдена")
            if member.board_id != board_id:
                raise ValueError("Участник не принадлежит указанной доске")

            # 2. Проверить права
            board = await session.get(BoardOrm, board_id)
            if not board:
                raise ValueError("Доска не найдена")
            if board.owner_id != requester_id:
                raise ValueError("Только владелец может изменять роли участников")

            old_role = member.role
            member.role = new_role

            # Запись в аудит
            audit = AuditLogOrm(
                user_id=requester_id,
                action=ActionType.UPDATE,
                entity_type=EntityType.BOARD_MEMBER,
                entity_id=member_id,
                changes={"role": {"old": old_role, "new": new_role}}
            )
            session.add(audit)

            await session.commit()
            await session.refresh(member)
            return member


    @classmethod
    async def remove_member(cls, board_id: int, member_id: int, requester_id: int) -> None:
        """Удаляет участника. Только владелец доски, кроме удаления самого владельца."""
        async with new_session() as session:
            # 1. Найти запись участника и проверить принадлежность доске
            member = await session.get(BoardMemberOrm, member_id)
            if not member:
                raise ValueError("Запись участника не найдена")
            if member.board_id != board_id:
                raise ValueError("Участник не принадлежит указанной доске")

            # 2. Проверить права
            board = await session.get(BoardOrm, board_id)
            if not board:
                raise ValueError("Доска не найдена")
            if board.owner_id != requester_id:
                raise ValueError("Только владелец может удалять участников")

            if member.role == MemberRole.OWNER:
                raise ValueError("Нельзя удалить владельца доски")

            # Запись в аудит перед удалением
            audit = AuditLogOrm(
                user_id=requester_id,
                action=ActionType.DELETE,
                entity_type=EntityType.BOARD_MEMBER,
                entity_id=member_id,
                changes=None
            )
            session.add(audit)

            await session.delete(member)
            await session.commit()