import logging
from fastapi import APIRouter, Depends, HTTPException, status
from models.auth import UserOrm
from repositories.boards import BoardRepository
from repositories.board_members import BoardMemberRepository
from schemas.boards import SBoardCreate, SBoardUpdate, BoardResponse, BoardListResponse
from schemas.base import SuccessResponse
from utils.security import get_current_user
from utils.pagination import encode_cursor, decode_cursor




router = APIRouter(
    prefix="/boards",
    tags=["Boards"]
)

logger = logging.getLogger(__name__)



def handle_value_error(e: ValueError):
    """Преобразует ValueError в HTTPException с соответствующим статусом."""
    msg = str(e)
    if "Недостаточно прав" in msg or "Только владелец" in msg:
        status_code = status.HTTP_403_FORBIDDEN
    elif "не найден" in msg or "не найдена" in msg:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=status_code, detail=msg)



@router.post(
    "/",
    response_model=BoardResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def create_board(
    board_data: SBoardCreate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Создаёт новую доску. Создатель автоматически становится владельцем."""
    try:
        board = await BoardRepository.create_board(
            user_id=current_user.id,
            title=board_data.title,
            description=board_data.description
        )
        return board
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get(
    "/",
    response_model=BoardListResponse,
    responses={
        401: {"description": "Не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_boards(
    cursor: str | None = None,
    direction: str = "after",
    limit: int = 10,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Возвращает список досок, доступных пользователю, с курсорной пагинацией.
    Параметр direction может быть 'after' или 'before'.
    """
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Лимит должен быть от 1 до 50")
    if direction not in ("after", "before"):
        raise HTTPException(status_code=400, detail="Недопустимое направление (должно быть 'after' или 'before')")

    cursor_id = decode_cursor(cursor) if cursor else None
    if cursor and cursor_id is None:
        raise HTTPException(status_code=400, detail="Некорректный курсор")

    try:
        boards, next_id, prev_id = await BoardRepository.get_boards_for_user(
            user_id=current_user.id,
            cursor=str(cursor_id) if cursor_id is not None else None,
            direction=direction,
            limit=limit
        )
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    return BoardListResponse(
        items=boards,
        next_cursor=encode_cursor(int(next_id)) if next_id else None,
        previous_cursor=encode_cursor(int(prev_id)) if prev_id else None
    )


@router.get(
    "/{board_id}",
    response_model=BoardResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Доска не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_board(
    board_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Возвращает данные доски по её ID. Доступна всем участникам доски."""
    try:
        board = await BoardRepository.get_board_by_id(board_id)
        if not board:
            raise ValueError("Доска не найдена")
        role = await BoardMemberRepository.get_member_role(board_id, current_user.id)
        if not role:
            raise ValueError("Недостаточно прав для просмотра доски")
        return board
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch(
    "/{board_id}",
    response_model=BoardResponse,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён (не владелец)"},
        404: {"description": "Доска не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def update_board(
    board_id: int,
    update_data: SBoardUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Обновляет данные доски. Только владелец может редактировать.
    Требуется передача текущей версии доски (version) для защиты от коллизий.
    """
    try:
        board = await BoardRepository.update_board(
            board_id=board_id,
            user_id=current_user.id,
            version=update_data.version,
            update_data=update_data.model_dump(exclude_none=True, exclude={"version"})
        )
        return board
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete(
    "/{board_id}",
    response_model=SuccessResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Доска не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def delete_board(
    board_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Удаляет доску. Только владелец может удалить доску."""
    try:
        await BoardRepository.delete_board(board_id, current_user.id)
        return SuccessResponse(detail="Доска успешно удалена")
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")