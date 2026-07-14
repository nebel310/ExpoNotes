from sqlalchemy import select, or_, and_
from database import new_session
from models.cards import CardOrm
from models.columns import ColumnOrm
from models.board_members import BoardMemberOrm
from models.boards import BoardOrm




class SearchRepository:
    """Репозиторий для поиска карточек."""

    @classmethod
    async def search_cards(
        cls,
        user_id: int,
        query_text: str,
        cursor: str | None = None,
        direction: str = "after",
        limit: int = 10
    ) -> tuple[list[tuple[CardOrm, int]], str | None, str | None]:
        """
        Ищет карточки по тексту в title и description во всех досках,
        к которым пользователь имеет доступ.
        Возвращает карточки и соответствующий board_id для каждой.
        """
        async with new_session() as session:
            accessible_boards = (
                select(BoardOrm.id)
                .outerjoin(BoardMemberOrm, BoardOrm.id == BoardMemberOrm.board_id)
                .where(
                    or_(
                        BoardOrm.owner_id == user_id,
                        BoardMemberOrm.user_id == user_id
                    )
                )
                .distinct()
                .subquery()
            )

            accessible_columns = (
                select(ColumnOrm.id)
                .where(ColumnOrm.board_id.in_(select(accessible_boards)))
                .subquery()
            )

            like_pattern = f"%{query_text}%"
            base_query = (
                select(CardOrm, ColumnOrm.board_id)
                .join(ColumnOrm, CardOrm.column_id == ColumnOrm.id)
                .where(
                    and_(
                        CardOrm.column_id.in_(select(accessible_columns)),
                        or_(
                            CardOrm.title.ilike(like_pattern),
                            CardOrm.description.ilike(like_pattern)
                        )
                    )
                )
            )

            cursor_id = None
            if cursor:
                try:
                    cursor_id = int(cursor)
                except (ValueError, TypeError):
                    raise ValueError("Некорректный курсор")

            if direction == "after":
                if cursor_id is not None:
                    query = base_query.where(CardOrm.id > cursor_id).order_by(CardOrm.id.asc())
                else:
                    query = base_query.order_by(CardOrm.id.asc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                items = result.all()
                cards_with_board = [(row[0], row[1]) for row in items[:limit]]
                next_id = items[limit - 1][0].id if len(items) > limit else None
                prev_id = items[0][0].id if cursor_id is not None else None

            elif direction == "before":
                if cursor_id is not None:
                    query = base_query.where(CardOrm.id < cursor_id).order_by(CardOrm.id.desc())
                else:
                    query = base_query.order_by(CardOrm.id.desc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                desc_items = result.all()
                has_previous = len(desc_items) > limit
                page_items_desc = desc_items[:limit]
                cards_with_board = [(row[0], row[1]) for row in reversed(page_items_desc)]
                next_id = cards_with_board[-1][0].id if cards_with_board else None
                prev_id = cards_with_board[0][0].id if has_previous else None
            else:
                raise ValueError("Недопустимое направление")

            next_cursor = str(next_id) if next_id is not None else None
            prev_cursor = str(prev_id) if prev_id is not None else None
            return cards_with_board, next_cursor, prev_cursor