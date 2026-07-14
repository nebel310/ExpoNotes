import logging
from fastapi import APIRouter, Depends, HTTPException, status
from models.auth import UserOrm
from repositories.search import SearchRepository
from schemas.search import SearchCardResponse, SearchCardItem
from schemas.cards import CardResponse
from utils.security import get_current_user
from utils.pagination import encode_cursor, decode_cursor




router = APIRouter(
    prefix="/search",
    tags=["Search"]
)

logger = logging.getLogger(__name__)



def handle_value_error(e: ValueError):
    msg = str(e)
    if "Некорректный курсор" in msg:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=status_code, detail=msg)


@router.get(
    "/cards",
    response_model=SearchCardResponse,
    responses={
        400: {"description": "Параметр q обязателен"},
        401: {"description": "Не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def search_cards(
    q: str,
    cursor: str | None = None,
    direction: str = "after",
    limit: int = 10,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Поиск карточек по тексту (title, description) во всех доступных досках.
    Параметр q обязателен и не может быть пустым.
    В ответе каждая карточка содержит board_id.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Параметр q обязателен и не может быть пустым")

    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Лимит должен быть от 1 до 50")
    if direction not in ("after", "before"):
        raise HTTPException(status_code=400, detail="Недопустимое направление")

    cursor_id = decode_cursor(cursor) if cursor else None
    if cursor and cursor_id is None:
        raise HTTPException(status_code=400, detail="Некорректный курсор")

    try:
        cards_with_board, next_id, prev_id = await SearchRepository.search_cards(
            user_id=current_user.id,
            query_text=q,
            cursor=str(cursor_id) if cursor_id is not None else None,
            direction=direction,
            limit=limit
        )
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    items = []
    for card, board_id in cards_with_board:
        card_data = CardResponse.model_validate(card).model_dump()
        card_data["board_id"] = board_id
        items.append(SearchCardItem(**card_data))

    return SearchCardResponse(
        items=items,
        next_cursor=encode_cursor(int(next_id)) if next_id else None,
        previous_cursor=encode_cursor(int(prev_id)) if prev_id else None
    )