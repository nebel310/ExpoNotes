from sqlalchemy import select, or_, and_, delete, update
from database import new_session
from models.boards import BoardOrm
from models.board_members import BoardMemberOrm, MemberRole
from models.audit_log import AuditLogOrm, ActionType, EntityType




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

            # Запись в аудит
            audit = AuditLogOrm(
                user_id=user_id,
                action=ActionType.CREATE,
                entity_type=EntityType.BOARD,
                entity_id=board.id,
                changes={"title": title, "description": description}
            )
            session.add(audit)

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
                    cursor_id = int(cursor)
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
                desc_items = result.scalars().all()
                has_previous = len(desc_items) > limit
                page_items_desc = desc_items[:limit]
                boards = list(reversed(page_items_desc))
                next_id = boards[-1].id if boards else None
                prev_id = boards[0].id if has_previous else None
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

            if board.owner_id != user_id:
                raise ValueError("Только владелец может редактировать доску")

            if board.version != version:
                raise ValueError("Данные были изменены другим пользователем. Обновите страницу и попробуйте снова.")

            # Сохраняем старые значения для аудита
            old_values = {"title": board.title, "description": board.description}
            changes = {}
            for key, value in update_data.items():
                if hasattr(board, key):
                    old_val = getattr(board, key)
                    if old_val != value:
                        changes[key] = {"old": old_val, "new": value}
                    setattr(board, key, value)

            board.version += 1

            if changes:
                audit = AuditLogOrm(
                    user_id=user_id,
                    action=ActionType.UPDATE,
                    entity_type=EntityType.BOARD,
                    entity_id=board_id,
                    changes=changes
                )
                session.add(audit)

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

            if board.owner_id != user_id:
                raise ValueError("Только владелец может удалить доску")

            # Запись в аудит перед удалением
            audit = AuditLogOrm(
                user_id=user_id,
                action=ActionType.DELETE,
                entity_type=EntityType.BOARD,
                entity_id=board_id,
                changes=None
            )
            session.add(audit)

            await session.delete(board)
            await session.commit()