import logging
from fastapi import APIRouter, Depends, HTTPException, status
from models.auth import UserOrm
from repositories.audit_log import AuditLogRepository
from schemas.audit_log import AuditLogResponse, AuditLogListResponse
from utils.security import get_current_user
from utils.pagination import encode_cursor, decode_cursor




router = APIRouter(
    prefix="/audit-log",
    tags=["Audit Log"]
)

logger = logging.getLogger(__name__)



def handle_value_error(e: ValueError):
    msg = str(e)
    if "не найден" in msg:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=status_code, detail=msg)


@router.get(
    "/",
    response_model=AuditLogListResponse,
    responses={
        401: {"description": "Не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    cursor: str | None = None,
    direction: str = "after",
    limit: int = 10,
    current_user: UserOrm = Depends(get_current_user)
):
    """
    Возвращает список записей аудита с фильтрацией и пагинацией.
    Параметры entity_type и entity_id опциональны.
    """
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Лимит должен быть от 1 до 50")
    if direction not in ("after", "before"):
        raise HTTPException(status_code=400, detail="Недопустимое направление")

    if entity_type and entity_type not in ("board", "column", "card", "comment", "file", "board_member"):
        raise HTTPException(status_code=400, detail="Недопустимый тип сущности")

    cursor_id = decode_cursor(cursor) if cursor else None
    if cursor and cursor_id is None:
        raise HTTPException(status_code=400, detail="Некорректный курсор")

    try:
        logs, next_id, prev_id = await AuditLogRepository.get_logs(
            entity_type=entity_type,
            entity_id=entity_id,
            cursor=str(cursor_id) if cursor_id is not None else None,
            direction=direction,
            limit=limit
        )
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    return AuditLogListResponse(
        items=logs,
        next_cursor=encode_cursor(int(next_id)) if next_id else None,
        previous_cursor=encode_cursor(int(prev_id)) if prev_id else None
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    responses={
        401: {"description": "Не авторизован"},
        404: {"description": "Запись не найдена"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_audit_log(
    log_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Возвращает запись аудита по её ID."""
    try:
        log = await AuditLogRepository.get_log_by_id(log_id)
        if not log:
            raise ValueError("Запись аудита не найдена")
        return log
    except ValueError as e:
        handle_value_error(e)
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")