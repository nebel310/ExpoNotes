from sqlalchemy import select, or_, and_, delete, update
from database import new_session
from models.boards import BoardOrm
from models.board_members import BoardMemberOrm, MemberRole




class BoardRepository:
    """Репозиторий для работы с досками."""
    
    @classmethod
    async def create_board(cls, user_id: int, title: str, description: str | None = None) -> BoardOrm:
        """
        Создаёт новую доску и автоматически добавляет создателя как владельца.
        Возвращает объект доски.
        """
        async with new_session() as session:
            board = BoardOrm(
                title=title,
                description=description,
                owner_id=user_id
            )
            session.add(board)
            await session.flush()  # чтобы получить board.id
            
            # Добавляем владельца в члены доски
            member = BoardMemberOrm(
                board_id=board.id,
                user_id=user_id,
                role=MemberRole.OWNER
            )
            session.add(member)
            await session.commit()
            await session.refresh(board)
            return board


    @classmethod
    async def get_boards_for_user(
        cls,
        user_id: int,
        cursor: str | None = None,
        direction: str = "after",
        limit: int = 10
    ) -> tuple[list[BoardOrm], str | None, str | None]:
        """
        Возвращает доски, доступные пользователю (где он член), с курсорной пагинацией.
        direction: "after" (id > cursor) или "before" (id < cursor).
        Возвращает (список досок, next_cursor, previous_cursor).
        """
        async with new_session() as session:
            # Базовый запрос: доски, где пользователь owner или член
            base_query = (
                select(BoardOrm)
                .outerjoin(BoardMemberOrm, BoardOrm.id == BoardMemberOrm.board_id)
                .where(
                    or_(
                        BoardOrm.owner_id == user_id,
                        BoardMemberOrm.user_id == user_id
                    )
                )
                .distinct()
            )

            cursor_id = None
            if cursor:
                try:
                    cursor_id = int(cursor)  # будем передавать уже декодированный int
                except (ValueError, TypeError):
                    raise ValueError("Некорректный курсор")

            if direction == "after":
                if cursor_id is not None:
                    query = base_query.where(BoardOrm.id > cursor_id).order_by(BoardOrm.id.asc())
                else:
                    query = base_query.order_by(BoardOrm.id.asc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                items = result.scalars().all()
                boards = items[:limit]
                next_id = boards[-1].id if len(items) > limit else None
                prev_id = boards[0].id if cursor_id is not None else None

            elif direction == "before":
                if cursor_id is not None:
                    query = base_query.where(BoardOrm.id < cursor_id).order_by(BoardOrm.id.desc())
                else:
                    query = base_query.order_by(BoardOrm.id.desc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                items = result.scalars().all()
                items.reverse()
                boards = items[:limit]
                next_id = boards[-1].id if cursor_id is not None and len(items) > limit else None
                prev_id = boards[0].id if len(items) > limit else None
            else:
                raise ValueError("Недопустимое направление (должно быть 'after' или 'before')")

            next_cursor = str(next_id) if next_id is not None else None
            prev_cursor = str(prev_id) if prev_id is not None else None

            return boards, next_cursor, prev_cursor


    @classmethod
    async def get_board_by_id(cls, board_id: int) -> BoardOrm | None:
        """Получает доску по ID или None, если не найдена."""
        async with new_session() as session:
            query = select(BoardOrm).where(BoardOrm.id == board_id)
            result = await session.execute(query)
            return result.scalars().first()


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
    async def update_board(cls, board_id: int, user_id: int, version: int, update_data: dict) -> BoardOrm:
        """
        Обновляет доску. Только владелец может обновлять.
        Проверяет переданную версию для защиты от коллизий.
        update_data — словарь с полями title и/или description.
        Возвращает обновлённую доску.
        """
        if not await cls._check_owner(board_id, user_id):
            raise ValueError("Только владелец может редактировать доску")

        async with new_session() as session:
            board = await session.get(BoardOrm, board_id)
            if not board:
                raise ValueError("Доска не найдена")

            if board.version != version:
                raise ValueError("Данные были изменены другим пользователем. Обновите страницу и попробуйте снова.")

            for key, value in update_data.items():
                if hasattr(board, key):
                    setattr(board, key, value)

            board.version += 1
            await session.commit()
            await session.refresh(board)
            return board


    @classmethod
    async def delete_board(cls, board_id: int, user_id: int) -> None:
        """
        Удаляет доску. Только владелец может удалить.
        """
        if not await cls._check_owner(board_id, user_id):
            raise ValueError("Только владелец может удалить доску")

        async with new_session() as session:
            board = await session.get(BoardOrm, board_id)
            if not board:
                raise ValueError("Доска не найдена")
            await session.delete(board)
            await session.commit()