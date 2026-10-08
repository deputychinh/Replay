"""WebSocket endpoint for the console. The browser sends the access token as the first message
(tokens never go in URLs, which end up in logs)."""

import asyncio
import contextlib
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.common.constants import WS_HEARTBEAT_SECONDS
from app.common.enums import EventName
from app.core.deps import actor_from_token
from app.core.errors import UnauthorizedError
from app.realtime.hub import Connection, hub
from app.realtime.publisher import publish

router = APIRouter()
AUTH_TIMEOUT_SECONDS = 5
CLOSE_UNAUTHORIZED = 4401


@router.websocket("/ws")
async def events(socket: WebSocket) -> None:
    await socket.accept()
    try:
        first = await asyncio.wait_for(socket.receive_json(), timeout=AUTH_TIMEOUT_SECONDS)
        actor = actor_from_token(first.get("token"))
        if not actor.is_staff:
            raise UnauthorizedError()
    except (TimeoutError, UnauthorizedError, ValueError, KeyError, AttributeError):
        await socket.close(code=CLOSE_UNAUTHORIZED)
        return

    connection = Connection(socket, actor.user_id)
    hub.add(actor.org_id, connection)
    await socket.send_text(json.dumps({"event": "ready", "data": {}}))
    try:
        while True:
            try:
                message = await asyncio.wait_for(socket.receive_json(), timeout=WS_HEARTBEAT_SECONDS)
            except TimeoutError:
                await socket.send_text(json.dumps({"event": "ping", "data": {}}))
                continue
            if message.get("event") == EventName.AGENT_TYPING and message.get("ticket_id"):
                await publish(actor.org_id, EventName.AGENT_TYPING, {"ticket_id": message["ticket_id"], "user_id": actor.user_id})
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(actor.org_id, connection)
        with contextlib.suppress(Exception):
            await socket.close()
