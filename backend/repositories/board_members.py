from sqlalchemy import select, and_, delete
from database import new_session
from models.board_members import BoardMemberOrm, MemberRole
from models.boards import BoardOrm




class BoardMemberRepository:
    """Репозиторий для управления участниками доски."""

    @classmethod
    async def _check_owner(cls, board_id: int, user_id: int) -> bool:
        """Проверяет, является ли пользователь владельцем доски."""
        async with new_session() as session:
            query = select(BoardOrm).where(
                and_(BoardOrm.id == board_id, BoardOrm.owner_id == user_id)
            )
            result = await session.execute(query)
            return result.scalars().first() is not None


    @classmethod
    async def add_member(cls, board_id: int, user_id: int, role: MemberRole, requester_id: int) -> BoardMemberOrm:
        """
        Добавляет участника в доску. Только владелец может добавлять.
        Возвращает запись BoardMemberOrm.
        """
        if not await cls._check_owner(board_id, requester_id):
            raise ValueError("Только владелец может добавлять участников")

        async with new_session() as session:
            # Проверка существования доски
            board = await session.get(BoardOrm, board_id)
            if not board:
                raise ValueError("Доска не найдена")

            # Проверка, что пользователь ещё не член доски
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
            await session.commit()
            await session.refresh(member)
            return member


    @classmethod
    async def get_members(
        cls,
        board_id: int,
        cursor: str | None = None,
        direction: str = "after",
        limit: int = 10
    ) -> tuple[list[BoardMemberOrm], str | None, str | None]:
        """
        Возвращает участников доски с пагинацией.
        """
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
                items = result.scalars().all()
                items.reverse()
                members = items[:limit]
                next_id = members[-1].id if cursor_id is not None and len(items) > limit else None
                prev_id = members[0].id if len(items) > limit else None
            else:
                raise ValueError("Недопустимое направление")

            next_cursor = str(next_id) if next_id is not None else None
            prev_cursor = str(prev_id) if prev_id is not None else None

            return members, next_cursor, prev_cursor


    @classmethod
    async def update_member_role(cls, member_id: int, new_role: MemberRole, requester_id: int) -> BoardMemberOrm:
        """
        Изменяет роль участника. Только владелец доски может менять роли.
        """
        async with new_session() as session:
            member = await session.get(BoardMemberOrm, member_id)
            if not member:
                raise ValueError("Запись участника не найдена")

            # Проверка, что requester является владельцем доски
            if not await cls._check_owner(member.board_id, requester_id):
                raise ValueError("Только владелец может изменять роли участников")

            member.role = new_role
            await session.commit()
            await session.refresh(member)
            return member


    @classmethod
    async def remove_member(cls, member_id: int, requester_id: int) -> None:
        """
        Удаляет участника из доски. Только владелец доски может удалять.
        """
        async with new_session() as session:
            member = await session.get(BoardMemberOrm, member_id)
            if not member:
                raise ValueError("Запись участника не найдена")

            if not await cls._check_owner(member.board_id, requester_id):
                raise ValueError("Только владелец может удалять участников")

            if member.role == MemberRole.OWNER:
                raise ValueError("Нельзя удалить владельца доски")

            await session.delete(member)
            await session.commit()