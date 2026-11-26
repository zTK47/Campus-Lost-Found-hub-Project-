#This file defines the authentication and ownership logic for the application.
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.accounts import get_user_by_email
from app import database as db
from app.sessions import SESSION_COOKIE, get_session

class BrowserUser:
    def __init__(self, email: str, role: str = "user"):
        self.email = email
        self.role = role

def current_user(request: Request) -> BrowserUser | None:
    token = request.cookies.get(SESSION_COOKIE)
    cookie_session = get_session(token)
    if not cookie_session:
        return None

    with Session(db.engine) as session:
        user = get_user_by_email(session, cookie_session.email)
        if not user:
            return None
        return BrowserUser(email=user.email, role=user.role)


def require_login(user: BrowserUser | None = Depends(current_user)) -> BrowserUser:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


def require_finder_of_item(item, user: BrowserUser) -> None:
    if item.finder_contact.lower() != user.email.lower():
        raise HTTPException(
            status_code=403,
            detail="Only the original finder may perform this action",
        )


LoggedIn = Annotated[BrowserUser, Depends(require_login)]