from sqlalchemy import select, and_, update, func
from database import new_session
from models.cards import CardOrm, Priority
from models.columns import ColumnOrm
from models.board_members import BoardMemberOrm, MemberRole
from models.boards import BoardOrm
from models.auth import UserOrm
from models.audit_log import AuditLogOrm, ActionType, EntityType




class CardRepository:
    """Репозиторий для работы с карточками."""

    @classmethod
    async def get_member_role(cls, board_id: int, user_id: int) -> MemberRole | None:
        """Возвращает роль пользователя в доске."""
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
    async def create_card(cls, column_id: int, title: str, description: str | None, order: int | None,
                          author_id: int, assignee_id: int | None, due_date: str | None,
                          priority: Priority | None, file_id: int | None) -> CardOrm:
        """Создаёт карточку в колонке. Требуется writer/owner."""
        async with new_session() as session:
            column = await session.get(ColumnOrm, column_id)
            if not column:
                raise ValueError("Колонка не найдена")

            role = await cls.get_member_role(column.board_id, author_id)
            if role not in (MemberRole.WRITER, MemberRole.OWNER):
                raise ValueError("Недостаточно прав для создания карточки")

            if assignee_id is not None:
                user = await session.get(UserOrm, assignee_id)
                if not user:
                    raise ValueError("Назначенный пользователь не найден")

            if order is None:
                max_order_query = select(func.max(CardOrm.order)).where(CardOrm.column_id == column_id)
                result = await session.execute(max_order_query)
                max_order = result.scalar_one_or_none()
                order = (max_order or 0) + 1

            card = CardOrm(
                column_id=column_id,
                title=title,
                description=description,
                order=order,
                author_id=author_id,
                assignee_id=assignee_id,
                due_date=due_date,
                priority=priority,
                file_id=file_id
            )
            session.add(card)
            await session.flush()

            # Запись в аудит
            audit = AuditLogOrm(
                user_id=author_id,
                action=ActionType.CREATE,
                entity_type=EntityType.CARD,
                entity_id=card.id,
                changes={
                    "column_id": column_id,
                    "title": title,
                    "description": description,
                    "order": order,
                    "assignee_id": assignee_id,
                    "due_date": due_date,
                    "priority": priority,
                    "file_id": file_id
                }
            )
            session.add(audit)

            await session.commit()
            await session.refresh(card)
            return card


    @classmethod
    async def get_cards(cls, column_id: int, cursor: str | None = None, direction: str = "after", limit: int = 10) -> tuple[list[CardOrm], str | None, str | None]:
        """Возвращает карточки в колонке с пагинацией."""
        async with new_session() as session:
            base_query = select(CardOrm).where(CardOrm.column_id == column_id)

            cursor_id = None
            if cursor:
                try:
                    cursor_id = int(cursor)
                except (ValueError, TypeError):
                    raise ValueError("Некорректный курсор")

            if direction == "after":
                if cursor_id is not None:
                    query = base_query.where(CardOrm.id > cursor_id).order_by(CardOrm.order.asc(), CardOrm.id.asc())
                else:
                    query = base_query.order_by(CardOrm.order.asc(), CardOrm.id.asc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                items = result.scalars().all()
                cards = items[:limit]
                next_id = cards[-1].id if len(items) > limit else None
                prev_id = cards[0].id if cursor_id is not None else None

            elif direction == "before":
                if cursor_id is not None:
                    query = base_query.where(CardOrm.id < cursor_id).order_by(CardOrm.order.desc(), CardOrm.id.desc())
                else:
                    query = base_query.order_by(CardOrm.order.desc(), CardOrm.id.desc())
                query = query.limit(limit + 1)
                result = await session.execute(query)
                desc_items = result.scalars().all()
                has_previous = len(desc_items) > limit
                page_items_desc = desc_items[:limit]
                cards = list(reversed(page_items_desc))
                next_id = cards[-1].id if cards else None
                prev_id = cards[0].id if has_previous else None
            else:
                raise ValueError("Недопустимое направление")

            next_cursor = str(next_id) if next_id is not None else None
            prev_cursor = str(prev_id) if prev_id is not None else None
            return cards, next_cursor, prev_cursor


    @classmethod
    async def get_card_by_id(cls, card_id: int) -> CardOrm | None:
        """Получает карточку по ID."""
        async with new_session() as session:
            query = select(CardOrm).where(CardOrm.id == card_id)
            result = await session.execute(query)
            return result.scalars().first()


    @classmethod
    async def update_card(cls, card_id: int, user_id: int, version: int, update_data: dict) -> CardOrm:
        """Обновляет данные карточки (кроме column_id и order). Требуется writer/owner. Проверяет версию."""
        async with new_session() as session:
            card = await session.get(CardOrm, card_id)
            if not card:
                raise ValueError("Карточка не найдена")

            column = await session.get(ColumnOrm, card.column_id)
            if not column:
                raise ValueError("Колонка не найдена")

            role = await cls.get_member_role(column.board_id, user_id)
            if role not in (MemberRole.WRITER, MemberRole.OWNER):
                raise ValueError("Недостаточно прав для редактирования карточки")

            if card.version != version:
                raise ValueError("Данные карточки были изменены другим пользователем. Обновите страницу и попробуйте снова.")

            old_values = {
                "title": card.title,
                "description": card.description,
                "assignee_id": card.assignee_id,
                "due_date": card.due_date,
                "priority": card.priority,
                "file_id": card.file_id
            }
            changes = {}
            for key, value in update_data.items():
                if hasattr(card, key):
                    old_val = getattr(card, key)
                    if old_val != value:
                        changes[key] = {"old": old_val, "new": value}
                    setattr(card, key, value)

            card.version += 1

            if changes:
                audit = AuditLogOrm(
                    user_id=user_id,
                    action=ActionType.UPDATE,
                    entity_type=EntityType.CARD,
                    entity_id=card_id,
                    changes=changes
                )
                session.add(audit)

            await session.commit()
            await session.refresh(card)
            return card


    @classmethod
    async def delete_card(cls, card_id: int, user_id: int) -> None:
        """Удаляет карточку. Требуется writer/owner."""
        async with new_session() as session:
            card = await session.get(CardOrm, card_id)
            if not card:
                raise ValueError("Карточка не найдена")

            column = await session.get(ColumnOrm, card.column_id)
            if not column:
                raise ValueError("Колонка не найдена")

            role = await cls.get_member_role(column.board_id, user_id)
            if role not in (MemberRole.WRITER, MemberRole.OWNER):
                raise ValueError("Недостаточно прав для удаления карточки")

            # Запись в аудит перед удалением
            audit = AuditLogOrm(
                user_id=user_id,
                action=ActionType.DELETE,
                entity_type=EntityType.CARD,
                entity_id=card_id,
                changes=None
            )
            session.add(audit)

            await session.delete(card)
            await session.commit()


    @classmethod
    async def move_card(cls, card_id: int, target_column_id: int, new_order: int, user_id: int) -> CardOrm:
        """Перемещает карточку в другую колонку и/или изменяет порядок. Требуется writer/owner."""
        async with new_session() as session:
            card = await session.get(CardOrm, card_id)
            if not card:
                raise ValueError("Карточка не найдена")

            source_column = await session.get(ColumnOrm, card.column_id)
            target_column = await session.get(ColumnOrm, target_column_id)
            if not source_column or not target_column:
                raise ValueError("Колонка не найдена")

            if source_column.board_id != target_column.board_id:
                raise ValueError("Нельзя перемещать карточку между разными досками")

            role = await cls.get_member_role(source_column.board_id, user_id)
            if role not in (MemberRole.WRITER, MemberRole.OWNER):
                raise ValueError("Недостаточно прав для перемещения карточки")

            old_column_id = card.column_id
            old_order = card.order

            if old_column_id == target_column_id:
                if card.order == new_order:
                    pass
                else:
                    await cls._shift_orders(session, old_column_id, card.order, None)
                    await cls._shift_orders(session, target_column_id, None, new_order, exclude_id=card.id)
                    card.order = new_order
            else:
                await cls._shift_orders(session, old_column_id, card.order, None)
                await cls._shift_orders(session, target_column_id, None, new_order)
                card.column_id = target_column_id
                card.order = new_order

            # Запись в аудит (MOVE)
            audit_changes = {
                "old_column_id": old_column_id,
                "old_order": old_order,
                "new_column_id": card.column_id,
                "new_order": card.order
            }
            audit = AuditLogOrm(
                user_id=user_id,
                action=ActionType.MOVE,
                entity_type=EntityType.CARD,
                entity_id=card_id,
                changes=audit_changes
            )
            session.add(audit)

            await session.commit()
            await session.refresh(card)
            return card


    @classmethod
    async def _shift_orders(cls, session, column_id: int, from_order: int | None, to_order: int | None, exclude_id: int | None = None):
        """Сдвигает order карточек при вставке/удалении."""
        if from_order is not None:
            stmt = (
                update(CardOrm)
                .where(CardOrm.column_id == column_id, CardOrm.order > from_order)
                .values(order=CardOrm.order - 1)
            )
            if exclude_id:
                stmt = stmt.where(CardOrm.id != exclude_id)
            await session.execute(stmt)

        if to_order is not None:
            stmt = (
                update(CardOrm)
                .where(CardOrm.column_id == column_id, CardOrm.order >= to_order)
                .values(order=CardOrm.order + 1)
            )
            if exclude_id:
                stmt = stmt.where(CardOrm.id != exclude_id)
            await session.execute(stmt)