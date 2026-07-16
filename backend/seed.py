import asyncio
import logging
from database import new_session, create_tables
from repositories.auth import UserRepository
from repositories.boards import BoardRepository
from repositories.columns import ColumnRepository
from repositories.cards import CardRepository
from repositories.comments import CommentRepository
from schemas.auth import SUserRegister




EMAIL = "user@user.com"
PASSWORD = "123456"


async def seed():
    try:
        user_id = await UserRepository.register_user(
            SUserRegister(
                username="User",
                email=EMAIL,
                password=PASSWORD,
                password_confirm=PASSWORD
            )
        )
    except ValueError as e:
        user = await UserRepository.get_user_by_email(EMAIL)
        user_id = user.id

    board_ids = []
    for i in range(1, 4):
        board = await BoardRepository.create_board(
            user_id=user_id,
            title=f"Доска {i}",
            description=f"Описание доски {i}"
        )
        board_ids.append(board.id)

    all_columns = []
    for board_id in board_ids:
        for j in range(1, 4):
            col = await ColumnRepository.create_column(
                board_id=board_id,
                title=f"Колонка {j} (доска {board_id})",
                order=j,
                user_id=user_id
            )
            all_columns.append(col)

    all_cards = []
    for col in all_columns:
        for k in range(1, 4):
            card = await CardRepository.create_card(
                column_id=col.id,
                title=f"Карточка {k} (колонка {col.id})",
                description=f"Описание карточки {k}",
                order=k,
                author_id=user_id,
                assignee_id=None,
                due_date=None,
                priority=None,
                file_id=None
            )
            all_cards.append(card)

    for idx, card in enumerate(all_cards[:3]):
        await CommentRepository.create_comment(
            card_id=card.id,
            author_id=user_id,
            text=f"Комментарий {idx+1} к карточке {card.id}"
        )