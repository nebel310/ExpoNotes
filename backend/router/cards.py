from fastapi import APIRouter, Depends, HTTPException, status
from models.auth import UserOrm
from repositories.cards import CardRepository
from repositories.columns import ColumnRepository
from repositories.board_members import BoardMemberRepository
from schemas.cards import (
    SCardCreate, SCardUpdate, SCardMove,
    CardResponse, CardListResponse
)
from schemas.base import SuccessResponse
from utils.security import get_current_user
from utils.pagination import encode_cursor, decode_cursor




columns_cards_router = APIRouter(
    prefix="/columns/{column_id}/cards",
    tags=["Cards"]
)

cards_router = APIRouter(
    prefix="/cards",
    tags=["Cards"]
)



def handle_value_error(e: ValueError):
    msg = str(e)
    if "Недостаточно прав" in msg:
        status_code = status.HTTP_403_FORBIDDEN
    elif "не найден" in msg or "не найдена" in msg:
        status_code = status.HTTP_404_NOT_FOUND
    elif "изменены другим" in msg:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=status_code, detail=msg)


@columns_cards_router.post(
    "/",
    response_model=CardResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Колонка не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def create_card(
    column_id: int,
    card_data: SCardCreate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Создаёт карточку в указанной колонке. Требуется writer/owner."""
    try:
        card = await CardRepository.create_card(
            column_id=column_id,
            title=card_data.title,
            description=card_data.description,
            order=card_data.order,
            author_id=current_user.id,
            assignee_id=card_data.assignee_id,
            due_date=card_data.due_date,
            priority=card_data.priority,
            file_id=card_data.file_id
        )
        return card
    except ValueError as e:
        handle_value_error(e)
    except Exception:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@columns_cards_router.get(
    "/",
    response_model=CardListResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_cards_in_column(
    column_id: int,
    cursor: str | None = None,
    direction: str = "after",
    limit: int = 10,
    current_user: UserOrm = Depends(get_current_user)
):
    """Возвращает список карточек в колонке с пагинацией. Доступно участникам доски."""
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Лимит должен быть от 1 до 50")
    if direction not in ("after", "before"):
        raise HTTPException(status_code=400, detail="Недопустимое направление")

    cursor_id = decode_cursor(cursor) if cursor else None
    if cursor and cursor_id is None:
        raise HTTPException(status_code=400, detail="Некорректный курсор")

    try:
        column = await ColumnRepository.get_column_by_id(column_id)
        if not column:
            raise ValueError("Колонка не найдена")
        role = await BoardMemberRepository.get_member_role(column.board_id, current_user.id)
        if not role:
            raise ValueError("Недостаточно прав для просмотра карточек")

        cards, next_id, prev_id = await CardRepository.get_cards(
            column_id=column_id,
            cursor=str(cursor_id) if cursor_id is not None else None,
            direction=direction,
            limit=limit
        )
    except ValueError as e:
        handle_value_error(e)
    except Exception:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    return CardListResponse(
        items=cards,
        next_cursor=encode_cursor(int(next_id)) if next_id else None,
        previous_cursor=encode_cursor(int(prev_id)) if prev_id else None
    )


@cards_router.get(
    "/{card_id}",
    response_model=CardResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Карточка не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_card(
    card_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Возвращает карточку по её ID. Требуется доступ к доске."""
    try:
        card = await CardRepository.get_card_by_id(card_id)
        if not card:
            raise ValueError("Карточка не найдена")
        column = await ColumnRepository.get_column_by_id(card.column_id)
        if not column:
            raise ValueError("Колонка не найдена")
        role = await BoardMemberRepository.get_member_role(column.board_id, current_user.id)
        if not role:
            raise ValueError("Недостаточно прав для просмотра карточки")
        return card
    except ValueError as e:
        handle_value_error(e)
    except Exception:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@cards_router.patch(
    "/{card_id}",
    response_model=CardResponse,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Карточка не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def update_card(
    card_id: int,
    update_data: SCardUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Обновляет данные карточки (без изменения колонки и порядка).
    Требуется writer/owner. Версия обязательна.
    """
    try:
        card = await CardRepository.update_card(
            card_id=card_id,
            user_id=current_user.id,
            version=update_data.version,
            update_data=update_data.model_dump(exclude_none=True, exclude={"version"})
        )
        return card
    except ValueError as e:
        handle_value_error(e)
    except Exception:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@cards_router.delete(
    "/{card_id}",
    response_model=SuccessResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Карточка не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def delete_card(
    card_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Удаляет карточку. Требуется writer/owner."""
    try:
        await CardRepository.delete_card(card_id, current_user.id)
        return SuccessResponse(detail="Карточка успешно удалена")
    except ValueError as e:
        handle_value_error(e)
    except Exception:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@cards_router.post(
    "/{card_id}/move",
    response_model=CardResponse,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Карточка или колонка не найдены"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def move_card(
    card_id: int,
    move_data: SCardMove,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Перемещает карточку в другую колонку и/или изменяет порядок.
    Требуется writer/owner. Колонки должны быть в одной доске.
    """
    try:
        card = await CardRepository.move_card(
            card_id=card_id,
            target_column_id=move_data.column_id,
            new_order=move_data.order,
            user_id=current_user.id
        )
        return card
    except ValueError as e:
        handle_value_error(e)
    except Exception:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")