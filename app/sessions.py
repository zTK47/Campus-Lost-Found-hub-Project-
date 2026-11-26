import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

SESSION_COOKIE = "lostfound_session"
SESSION_TTL = timedelta(hours=8)

@dataclass
class SessionData:
    email: str
    expires: datetime

_sessions: dict[str, SessionData] = {}

def create_session(email: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = SessionData(
        email=email.lower(),
        expires=datetime.now(timezone.utc) + SESSION_TTL,
    )
    return token

def get_session(token: str | None) -> SessionData | None:
    if not token:
        return None
    data = _sessions.get(token)
    if not data:
        return None
    if data.expires < datetime.now(timezone.utc):
        _sessions.pop(token, None)
        return None
    return data

def delete_session(token: str | None) -> None:
    if token:
        _sessions.pop(token, None)