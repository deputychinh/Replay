"""Business flow B4: an event published anywhere reaches the sockets of that organisation only."""

import uuid

import redis
from fastapi.testclient import TestClient

from app.common.constants import EVENTS_CHANNEL
from app.common.enums import EventName, Role
from app.core.security import TokenClaims, create_access_token
from app.main import app
from app.realtime.publisher import event_message


def _token(org: uuid.UUID, role: Role = Role.AGENT) -> str:
    return create_access_token(TokenClaims(uuid.uuid4(), org, role))


def test_events_reach_the_right_organisation() -> None:
    org, other = uuid.uuid4(), uuid.uuid4()
    publisher = redis.Redis.from_url("redis://localhost:6389/1")
    with TestClient(app) as http, http.websocket_connect("/api/v1/ws") as mine, http.websocket_connect("/api/v1/ws") as theirs:
        mine.send_json({"token": _token(org)})
        theirs.send_json({"token": _token(other)})
        assert mine.receive_json()["event"] == "ready" and theirs.receive_json()["event"] == "ready"

        publisher.publish(EVENTS_CHANNEL, event_message(other, EventName.TICKET_UPDATED, {"id": "for-them"}))
        publisher.publish(EVENTS_CHANNEL, event_message(org, EventName.TICKET_CREATED, {"id": "for-me"}))

        assert mine.receive_json() == {"event": "ticket.created", "data": {"id": "for-me"}}
        assert theirs.receive_json() == {"event": "ticket.updated", "data": {"id": "for-them"}}


def test_customers_and_bad_tokens_are_refused() -> None:
    with TestClient(app) as http:
        for token in ("garbage", _token(uuid.uuid4(), Role.CUSTOMER)):
            with http.websocket_connect("/api/v1/ws") as socket:
                socket.send_json({"token": token})
                message = socket.receive()
                assert message["type"] == "websocket.close" and message["code"] == 4401
