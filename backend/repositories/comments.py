from sqlalchemy import select, and_
from database import new_session
from models.comments import CommentOrm
from models.cards import CardOrm
from models.columns import ColumnOrm
from models.board_members import BoardMemberOrm, MemberRole
from models.boards import BoardOrm
from models.audit_log import AuditLogOrm, ActionType, EntityType




class CommentRepository:
    """Репозиторий для работы с комментариями."""

    @classmethod
    async def _get_board_id_by_card(cls, card_id: int) -> int | None:
        """Возвращает board_id, к которой принадлежит карточка."""
        async with new_session() as session:
            card = await session.get(CardOrm, card_id)
            if not card:
                return None
            column = await session.get(ColumnOrm, card.column_id)
            return column.board_id if column else None


    @classmethod
    async def get_member_role(cls, board_id: int, user_id: int) -> MemberRole | None:
        """Возвращает роль пользователя в доске или None."""
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
    async def create_comment(cls, card_id: int, author_id: int, text: str) -> CommentOrm:
        """Добавляет комментарий к карточке. Доступно любому участнику доски."""
        board_id = await cls._get_board_id_by_card(card_id)
        if not board_id:
            raise ValueError("Карточка не найдена")

        role = await cls.get_member_role(board_id, author_id)
        if not role:
            raise ValueError("Недостаточно прав для комментирования")

        async with new_session() as session:
            comment = CommentOrm(
                card_id=card_id,
                author_id=author_id,
                text=text
            )
            session.add(comment)
            await session.flush()  # чтобы получить comment.id

            # Запись в аудит
            audit = AuditLogOrm(
                user_id=author_id,
                action=ActionType.CREATE,
                entity_type=EntityType.COMMENT,
                entity_id=comment.id,
                changes={"card_id": card_id, "text": text}
            )
            session.add(audit)

            await session.commit()
            await session.refresh(comment)
            return comment


    @classmethod
    async def get_comments(
        cls,
        card_id: int,
        cursor: str | None = None,
        direction: str = "after",
        limit: int = 10
    ) -> tuple[list[CommentOrm], str | None, str | None]:
        """Возвращает комментарии карточки с пагинацией."""
        async with new_session() as session:
            base_query = select(CommentOrm).where(CommentOrm.card_id == card_id)

            cursor_id = None
            if cursor:
                try:
                    cursor_id = int(cursor)
                except (ValueError, TypeError):
                    raise ValueError("Некорректный курсор")

            if direction == "after":
                if cursor_id is not None:
                    query = base_query.where(CommentOrm.id > cursor_id).order_by(CommentOrm.id.asc())
                else:
                    query = base_query.order_by(CommentOrm.id.asc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                items = result.scalars().all()
                comments = items[:limit]
                next_id = comments[-1].id if len(items) > limit else None
                prev_id = comments[0].id if cursor_id is not None else None

            elif direction == "before":
                if cursor_id is not None:
                    query = base_query.where(CommentOrm.id < cursor_id).order_by(CommentOrm.id.desc())
                else:
                    query = base_query.order_by(CommentOrm.id.desc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                desc_items = result.scalars().all()
                has_previous = len(desc_items) > limit
                page_items_desc = desc_items[:limit]
                comments = list(reversed(page_items_desc))
                next_id = comments[-1].id if comments else None
                prev_id = comments[0].id if has_previous else None
            else:
                raise ValueError("Недопустимое направление")

            next_cursor = str(next_id) if next_id is not None else None
            prev_cursor = str(prev_id) if prev_id is not None else None
            return comments, next_cursor, prev_cursor


    @classmethod
    async def get_comment_by_id(cls, comment_id: int) -> CommentOrm | None:
        """Получает комментарий по ID."""
        async with new_session() as session:
            query = select(CommentOrm).where(CommentOrm.id == comment_id)
            result = await session.execute(query)
            return result.scalars().first()


    @classmethod
    async def update_comment(cls, comment_id: int, author_id: int, text: str) -> CommentOrm:
        """Обновляет комментарий. Только автор может редактировать."""
        async with new_session() as session:
            comment = await session.get(CommentOrm, comment_id)
            if not comment:
                raise ValueError("Комментарий не найден")

            if comment.author_id != author_id:
                raise ValueError("Только автор может редактировать комментарий")

            old_text = comment.text
            comment.text = text

            # Запись в аудит
            audit = AuditLogOrm(
                user_id=author_id,
                action=ActionType.UPDATE,
                entity_type=EntityType.COMMENT,
                entity_id=comment_id,
                changes={"text": {"old": old_text, "new": text}}
            )
            session.add(audit)

            await session.commit()
            await session.refresh(comment)
            return comment


    @classmethod
    async def delete_comment(cls, comment_id: int, user_id: int) -> None:
        """Удаляет комментарий. Может удалить автор или владелец доски."""
        async with new_session() as session:
            comment = await session.get(CommentOrm, comment_id)
            if not comment:
                raise ValueError("Комментарий не найден")

            card = await session.get(CardOrm, comment.card_id)
            if not card:
                raise ValueError("Карточка не найдена")
            column = await session.get(ColumnOrm, card.column_id)
            if not column:
                raise ValueError("Колонка не найдена")
            board_id = column.board_id

            is_author = comment.author_id == user_id
            is_owner = False
            board = await session.get(BoardOrm, board_id)
            if board and board.owner_id == user_id:
                is_owner = True

            if not (is_author or is_owner):
                raise ValueError("Недостаточно прав для удаления комментария")

            # Запись в аудит перед удалением
            audit = AuditLogOrm(
                user_id=user_id,
                action=ActionType.DELETE,
                entity_type=EntityType.COMMENT,
                entity_id=comment_id,
                changes=None
            )
            session.add(audit)

            await session.delete(comment)
            await session.commit()