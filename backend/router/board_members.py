import logging
from fastapi import APIRouter, Depends, HTTPException, status
from models.auth import UserOrm
from repositories.board_members import BoardMemberRepository
from schemas.board_members import (
    SBoardMemberAdd, SBoardMemberUpdate,
    BoardMemberResponse, BoardMemberListResponse
)
from schemas.base import SuccessResponse
from utils.security import get_current_user
from utils.pagination import encode_cursor, decode_cursor




router = APIRouter(
    prefix="/boards/{board_id}/members",
    tags=["Board Members"]
)

logger = logging.getLogger(__name__)



def handle_value_error(e: ValueError):
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
    response_model=BoardMemberResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Доска или пользователь не найдены"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def add_member(
    board_id: int,
    member_data: SBoardMemberAdd,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Добавляет участника в доску. Только владелец доски может добавлять.
    Роль указывается в теле запроса (reader, writer, owner).
    """
    try:
        member = await BoardMemberRepository.add_member(
            board_id=board_id,
            user_id=member_data.user_id,
            role=member_data.role,
            requester_id=current_user.id
        )
        return member
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get(
    "/",
    response_model=BoardMemberListResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_members(
    board_id: int,
    cursor: str | None = None,
    direction: str = "after",
    limit: int = 10,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Возвращает список участников доски с пагинацией.
    Доступно всем участникам доски.
    """
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Лимит должен быть от 1 до 50")
    if direction not in ("after", "before"):
        raise HTTPException(status_code=400, detail="Недопустимое направление")

    cursor_id = decode_cursor(cursor) if cursor else None
    if cursor and cursor_id is None:
        raise HTTPException(status_code=400, detail="Некорректный курсор")

    try:
        role = await BoardMemberRepository.get_member_role(board_id, current_user.id)
        if not role:
            raise ValueError("Недостаточно прав для просмотра участников")

        members, next_id, prev_id = await BoardMemberRepository.get_members(
            board_id=board_id,
            cursor=str(cursor_id) if cursor_id is not None else None,
            direction=direction,
            limit=limit
        )
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    return BoardMemberListResponse(
        items=members,
        next_cursor=encode_cursor(int(next_id)) if next_id else None,
        previous_cursor=encode_cursor(int(prev_id)) if prev_id else None
    )


@router.patch(
    "/{member_id}",
    response_model=BoardMemberResponse,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Запись не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def update_member_role(
    board_id: int,
    member_id: int,
    update_data: SBoardMemberUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Изменяет роль участника доски. Только владелец может изменять роли.
    """
    try:
        member = await BoardMemberRepository.update_member_role(
            board_id=board_id,
            member_id=member_id,
            new_role=update_data.role,
            requester_id=current_user.id
        )
        return member
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete(
    "/{member_id}",
    response_model=SuccessResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Запись не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def remove_member(
    board_id: int,
    member_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Удаляет участника из доски. Только владелец может удалять, кроме самого себя (владельца).
    """
    try:
        await BoardMemberRepository.remove_member(
            board_id=board_id,
            member_id=member_id,
            requester_id=current_user.id
        )
        return SuccessResponse(detail="Участник успешно удалён")
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")