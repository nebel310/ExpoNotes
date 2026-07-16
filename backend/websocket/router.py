import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from websocket.connection_manager import manager
from utils.security import get_current_user_from_token_ws
from repositories.board_members import BoardMemberRepository




router = APIRouter()
logger = logging.getLogger(__name__)



@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """WebSocket-подключение для real-time обновлений канбан-доски."""
    if not token:
        await websocket.close(code=1008, reason="Токен не предоставлен")
        return

    try:
        user = await get_current_user_from_token_ws(token)
        if not user:
            await websocket.close(code=1008, reason="Неверный токен")
            return
    except Exception as e:
        logger.error(f"Ошибка аутентификации WebSocket: {e}")
        await websocket.close(code=1008, reason="Ошибка аутентификации")
        return

    await manager.connect(websocket, user.id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "subscribe":
                board_id = data.get("board_id")
                if isinstance(board_id, int):
                    await manager.subscribe(websocket, board_id)
                else:
                    await websocket.send_json({"type": "error", "detail": "board_id должен быть целым числом"})

            elif msg_type == "unsubscribe":
                board_id = data.get("board_id")
                if isinstance(board_id, int):
                    await manager.unsubscribe(websocket, board_id)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Неизвестный тип сообщения: {msg_type}"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Ошибка WebSocket: {e}")
        manager.disconnect(websocket)