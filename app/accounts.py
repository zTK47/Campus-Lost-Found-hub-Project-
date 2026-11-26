from __future__ import annotations

from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.models import User

password_hash = PasswordHash.recommended()


class EmailAlreadyRegisteredError(Exception):
    """Raised when trying to create a user with an email that already exists."""


def get_user_by_email(session: Session, email: str) -> User | None:
    normalized = email.lower().strip()
    return session.exec(select(User).where(User.email == normalized)).first()


def create_user(
    session: Session,
    email: str,
    password: str,
    *,
    role: str = "user",
) -> User:
    normalized = email.lower().strip()
    if get_user_by_email(session, normalized) is not None:
        raise EmailAlreadyRegisteredError(f"Email already registered: {normalized}")

    user = User(
        email=normalized,
        password_hash=password_hash.hash(password),
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def verify_password(session: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(session, email)
    if user is None:
        return None
    if not password_hash.verify(password, user.password_hash):
        return None
    return user


def ensure_demo_user(session: Session) -> User:
    """Create the demo account if it does not exist yet."""
    demo_email = "john.smith@students.fhnw.ch"
    existing = get_user_by_email(session, demo_email)
    if existing is not None:
        return existing
    return create_user(session, demo_email, "1234", role="user")