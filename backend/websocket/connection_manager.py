import logging
from typing import Dict, Set

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

from repositories.board_members import BoardMemberRepository




logger = logging.getLogger(__name__)



class ConnectionManager:
    """Менеджер WebSocket-соединений для канбан-досок."""

    def __init__(self):
        # WebSocket -> user_id
        self.connection_users: Dict[WebSocket, int] = {}
        # user_id -> set of WebSocket
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # board_id -> set of WebSocket (подписчики)
        self.board_subscriptions: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        logger.info(f"Пользователь {user_id} подключился по WebSocket")

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id

    def disconnect(self, websocket: WebSocket):
        user_id = self.connection_users.pop(websocket, None)
        if user_id is None:
            return

        logger.info(f"Пользователь {user_id} отключился от WebSocket")
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Удаляем из всех подписок на доски
        for board_id, subscribers in self.board_subscriptions.items():
            subscribers.discard(websocket)

    async def subscribe(self, websocket: WebSocket, board_id: int):
        """Подписать соединение на обновления доски."""
        user_id = self.connection_users.get(websocket)
        if not user_id:
            return

        # Проверяем, что пользователь имеет доступ к доске
        try:
            role = await BoardMemberRepository.get_member_role(board_id, user_id)
            if role is None:
                await websocket.send_json({"type": "error", "detail": "Нет доступа к доске"})
                return
        except Exception as e:
            logger.error(f"Ошибка проверки доступа при подписке: {e}")
            await websocket.send_json({"type": "error", "detail": "Внутренняя ошибка"})
            return

        if board_id not in self.board_subscriptions:
            self.board_subscriptions[board_id] = set()
        self.board_subscriptions[board_id].add(websocket)
        await websocket.send_json({"type": "subscribed", "board_id": board_id})

    async def unsubscribe(self, websocket: WebSocket, board_id: int):
        """Отписаться от обновлений доски."""
        if board_id in self.board_subscriptions:
            self.board_subscriptions[board_id].discard(websocket)
            await websocket.send_json({"type": "unsubscribed", "board_id": board_id})

    async def broadcast_to_board(
        self,
        board_id: int,
        message: dict,
        exclude_websocket: WebSocket | None = None
    ):
        """Отправить сообщение всем подписчикам доски, кроме указанного соединения."""
        subscribers = self.board_subscriptions.get(board_id, set()).copy()
        for ws in subscribers:
            if ws is exclude_websocket:
                continue
            try:
                await ws.send_json(jsonable_encoder(message))
            except Exception as e:
                logger.error(f"Ошибка отправки WebSocket для доски {board_id}: {e}")
                self.disconnect(ws)


manager = ConnectionManager()