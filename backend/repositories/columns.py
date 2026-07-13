from sqlalchemy import select, and_, delete
from database import new_session
from models.columns import ColumnOrm
from models.board_members import BoardMemberOrm, MemberRole
from models.boards import BoardOrm




class ColumnRepository:
    """Репозиторий для работы с колонками."""

    @classmethod
    async def get_member_role(cls, board_id: int, user_id: int) -> MemberRole | None:
        """Возвращает роль пользователя в доске или None, если не член."""
        async with new_session() as session:
            # Сначала проверяем владельца
            board = await session.get(BoardOrm, board_id)
            if board and board.owner_id == user_id:
                return MemberRole.OWNER
            
            # Ищем в участниках
            query = select(BoardMemberOrm.role).where(
                and_(BoardMemberOrm.board_id == board_id, BoardMemberOrm.user_id == user_id)
            )
            result = await session.execute(query)
            row = result.first()
            return row[0] if row else None


    @classmethod
    async def create_column(cls, board_id: int, title: str, order: int | None, user_id: int) -> ColumnOrm:
        """
        Создаёт колонку в доске. Требуется роль writer или owner.
        """
        role = await cls.get_member_role(board_id, user_id)
        if role not in (MemberRole.WRITER, MemberRole.OWNER):
            raise ValueError("Недостаточно прав для создания колонки")

        async with new_session() as session:
            # Если order не задан, ставим максимальный + 1
            if order is None:
                max_order_query = select(ColumnOrm.order).where(ColumnOrm.board_id == board_id).order_by(ColumnOrm.order.desc()).limit(1)
                result = await session.execute(max_order_query)
                max_order = result.scalar_one_or_none()
                order = (max_order or 0) + 1

            column = ColumnOrm(
                board_id=board_id,
                title=title,
                order=order
            )
            session.add(column)
            await session.commit()
            await session.refresh(column)
            return column


    @classmethod
    async def get_columns(
        cls,
        board_id: int,
        cursor: str | None = None,
        direction: str = "after",
        limit: int = 10
    ) -> tuple[list[ColumnOrm], str | None, str | None]:
        """Возвращает колонки доски с пагинацией."""
        async with new_session() as session:
            base_query = select(ColumnOrm).where(ColumnOrm.board_id == board_id)

            cursor_id = None
            if cursor:
                try:
                    cursor_id = int(cursor)
                except (ValueError, TypeError):
                    raise ValueError("Некорректный курсор")

            if direction == "after":
                if cursor_id is not None:
                    query = base_query.where(ColumnOrm.id > cursor_id).order_by(ColumnOrm.order.asc(), ColumnOrm.id.asc())
                else:
                    query = base_query.order_by(ColumnOrm.order.asc(), ColumnOrm.id.asc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                items = result.scalars().all()
                columns = items[:limit]
                next_id = columns[-1].id if len(items) > limit else None
                prev_id = columns[0].id if cursor_id is not None else None

            elif direction == "before":
                if cursor_id is not None:
                    query = base_query.where(ColumnOrm.id < cursor_id).order_by(ColumnOrm.order.desc(), ColumnOrm.id.desc())
                else:
                    query = base_query.order_by(ColumnOrm.order.desc(), ColumnOrm.id.desc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                desc_items = result.scalars().all()
                has_previous = len(desc_items) > limit
                page_items_desc = desc_items[:limit]
                columns = list(reversed(page_items_desc))
                next_id = columns[-1].id if columns else None
                prev_id = columns[0].id if has_previous else None
            else:
                raise ValueError("Недопустимое направление")

            next_cursor = str(next_id) if next_id is not None else None
            prev_cursor = str(prev_id) if prev_id is not None else None
            return columns, next_cursor, prev_cursor


    @classmethod
    async def get_column_by_id(cls, column_id: int) -> ColumnOrm | None:
        """Получает колонку по ID."""
        async with new_session() as session:
            query = select(ColumnOrm).where(ColumnOrm.id == column_id)
            result = await session.execute(query)
            return result.scalars().first()


    @classmethod
    async def update_column(cls, column_id: int, user_id: int, version: int, update_data: dict) -> ColumnOrm:
        """
        Обновляет колонку. Требуется writer/owner.
        Проверяет версию для защиты от коллизий.
        """
        async with new_session() as session:
            column = await session.get(ColumnOrm, column_id)
            if not column:
                raise ValueError("Колонка не найдена")

            role = await cls.get_member_role(column.board_id, user_id)
            if role not in (MemberRole.WRITER, MemberRole.OWNER):
                raise ValueError("Недостаточно прав для редактирования колонки")

            if column.version != version:
                raise ValueError("Данные колонки были изменены другим пользователем. Обновите страницу и попробуйте снова.")

            for key, value in update_data.items():
                if hasattr(column, key):
                    setattr(column, key, value)

            column.version += 1
            await session.commit()
            await session.refresh(column)
            return column


    @classmethod
    async def delete_column(cls, column_id: int, user_id: int) -> None:
        """
        Удаляет колонку со всеми карточками. Требуется writer/owner.
        """
        async with new_session() as session:
            column = await session.get(ColumnOrm, column_id)
            if not column:
                raise ValueError("Колонка не найдена")

            role = await cls.get_member_role(column.board_id, user_id)
            if role not in (MemberRole.WRITER, MemberRole.OWNER):
                raise ValueError("Недостаточно прав для удаления колонки")

            await session.delete(column)
            await session.commit()