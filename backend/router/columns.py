import logging
from fastapi import APIRouter, Depends, HTTPException, status
from models.auth import UserOrm
from repositories.columns import ColumnRepository
from repositories.board_members import BoardMemberRepository
from schemas.columns import SColumnCreate, SColumnUpdate, ColumnResponse, ColumnListResponse
from schemas.base import SuccessResponse
from utils.security import get_current_user
from utils.pagination import encode_cursor, decode_cursor




board_columns_router = APIRouter(
    prefix="/boards/{board_id}/columns",
    tags=["Columns"]
)

column_router = APIRouter(
    prefix="/columns",
    tags=["Columns"]
)

logger = logging.getLogger(__name__)



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


@board_columns_router.post(
    "/",
    response_model=ColumnResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён (недостаточно прав)"},
        404: {"description": "Доска не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def create_column(
    board_id: int,
    column_data: SColumnCreate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Создаёт колонку в указанной доске. Требуется роль writer или owner."""
    try:
        column = await ColumnRepository.create_column(
            board_id=board_id,
            title=column_data.title,
            order=column_data.order,
            user_id=current_user.id
        )
        return column
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@board_columns_router.get(
    "/",
    response_model=ColumnListResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_columns(
    board_id: int,
    cursor: str | None = None,
    direction: str = "after",
    limit: int = 10,
    current_user: UserOrm = Depends(get_current_user)
):
    """Возвращает список колонок доски с пагинацией. Доступно всем участникам."""
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
            raise ValueError("Недостаточно прав для просмотра колонок")

        columns, next_id, prev_id = await ColumnRepository.get_columns(
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

    return ColumnListResponse(
        items=columns,
        next_cursor=encode_cursor(int(next_id)) if next_id else None,
        previous_cursor=encode_cursor(int(prev_id)) if prev_id else None
    )


@column_router.get(
    "/{column_id}",
    response_model=ColumnResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Колонка не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_column(
    column_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Возвращает колонку по её ID. Требуется доступ к доске."""
    try:
        column = await ColumnRepository.get_column_by_id(column_id)
        if not column:
            raise ValueError("Колонка не найдена")
        role = await BoardMemberRepository.get_member_role(column.board_id, current_user.id)
        if not role:
            raise ValueError("Недостаточно прав для просмотра колонки")
        return column
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@column_router.patch(
    "/{column_id}",
    response_model=ColumnResponse,
    responses={
        400: {"description": "Ошибка валидации"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Колонка не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def update_column(
    column_id: int,
    update_data: SColumnUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Обновляет колонку. Требуется writer/owner.
    Версия (version) обязательна для предотвращения коллизий.
    """
    try:
        column = await ColumnRepository.update_column(
            column_id=column_id,
            user_id=current_user.id,
            version=update_data.version,
            update_data=update_data.model_dump(exclude_none=True, exclude={"version"})
        )
        return column
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@column_router.delete(
    "/{column_id}",
    response_model=SuccessResponse,
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Колонка не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def delete_column(
    column_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Удаляет колонку вместе с карточками. Требуется writer/owner."""
    try:
        await ColumnRepository.delete_column(column_id, current_user.id)
        return SuccessResponse(detail="Колонка успешно удалена")
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")