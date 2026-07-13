import logging
from fastapi import APIRouter, Depends, HTTPException, status
from models.auth import UserOrm
from repositories.comments import CommentRepository
from repositories.cards import CardRepository
from repositories.columns import ColumnRepository
from repositories.board_members import BoardMemberRepository
from schemas.comments import SCommentCreate, SCommentUpdate, CommentResponse, CommentListResponse
from schemas.base import SuccessResponse
from utils.security import get_current_user
from utils.pagination import encode_cursor, decode_cursor




card_comments_router = APIRouter(
    prefix="/cards/{card_id}/comments",
    tags=["Comments"]
)

comments_router = APIRouter(
    prefix="/comments",
    tags=["Comments"]
)

logger = logging.getLogger(__name__)



def handle_value_error(e: ValueError):
    msg = str(e)
    if "Недостаточно прав" in msg:
        status_code = status.HTTP_403_FORBIDDEN
    elif "не найден" in msg or "не найдена" in msg:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=status_code, detail=msg)


@card_comments_router.post(
    "/",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Карточка не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def add_comment(
    card_id: int,
    comment_data: SCommentCreate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Добавляет комментарий к карточке. Доступно любому участнику доски."""
    try:
        comment = await CommentRepository.create_comment(
            card_id=card_id,
            author_id=current_user.id,
            text=comment_data.text
        )
        return comment
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@card_comments_router.get(
    "/",
    response_model=CommentListResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_comments(
    card_id: int,
    cursor: str | None = None,
    direction: str = "after",
    limit: int = 10,
    current_user: UserOrm = Depends(get_current_user)
):
    """Возвращает комментарии к карточке с пагинацией. Доступно участникам."""
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Лимит должен быть от 1 до 50")
    if direction not in ("after", "before"):
        raise HTTPException(status_code=400, detail="Недопустимое направление")

    cursor_id = decode_cursor(cursor) if cursor else None
    if cursor and cursor_id is None:
        raise HTTPException(status_code=400, detail="Некорректный курсор")

    try:
        card = await CardRepository.get_card_by_id(card_id)
        if not card:
            raise ValueError("Карточка не найдена")
        column = await ColumnRepository.get_column_by_id(card.column_id)
        if not column:
            raise ValueError("Колонка не найдена")
        role = await BoardMemberRepository.get_member_role(column.board_id, current_user.id)
        if not role:
            raise ValueError("Недостаточно прав для просмотра комментариев")

        comments, next_id, prev_id = await CommentRepository.get_comments(
            card_id=card_id,
            cursor=str(cursor_id) if cursor_id is not None else None,
            direction=direction,
            limit=limit
        )
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    return CommentListResponse(
        items=comments,
        next_cursor=encode_cursor(int(next_id)) if next_id else None,
        previous_cursor=encode_cursor(int(prev_id)) if prev_id else None
    )


@comments_router.get(
    "/{comment_id}",
    response_model=CommentResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Комментарий не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_comment(
    comment_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Возвращает комментарий по ID. Требуется доступ к карточке."""
    try:
        comment = await CommentRepository.get_comment_by_id(comment_id)
        if not comment:
            raise ValueError("Комментарий не найден")
        card = await CardRepository.get_card_by_id(comment.card_id)
        if not card:
            raise ValueError("Карточка не найдена")
        column = await ColumnRepository.get_column_by_id(card.column_id)
        if not column:
            raise ValueError("Колонка не найдена")
        role = await BoardMemberRepository.get_member_role(column.board_id, current_user.id)
        if not role:
            raise ValueError("Недостаточно прав для просмотра комментария")
        return comment
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@comments_router.patch(
    "/{comment_id}",
    response_model=CommentResponse,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён (не автор)"},
        404: {"description": "Комментарий не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def update_comment(
    comment_id: int,
    update_data: SCommentUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Обновляет комментарий. Только автор может редактировать."""
    try:
        comment = await CommentRepository.update_comment(
            comment_id=comment_id,
            author_id=current_user.id,
            text=update_data.text
        )
        return comment
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@comments_router.delete(
    "/{comment_id}",
    response_model=SuccessResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Комментарий не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def delete_comment(
    comment_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Удаляет комментарий. Может удалить автор или владелец доски."""
    try:
        await CommentRepository.delete_comment(comment_id, current_user.id)
        return SuccessResponse(detail="Комментарий успешно удалён")
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")