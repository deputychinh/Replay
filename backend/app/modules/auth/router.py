from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response

from app.common.constants import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH, REFRESH_TOKEN_TTL_DAYS
from app.common.schemas import ERROR_RESPONSES
from app.core.config import get_settings
from app.core.deps import CurrentActor, Uow
from app.core.errors import UnauthorizedError
from app.modules.auth.schemas import LoginIn, RegisterIn, SessionOut
from app.modules.auth.service import AuthService, IssuedSession
from app.modules.organizations.repository import OrganizationRepository
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]


def _respond(session: IssuedSession, response: Response) -> SessionOut:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        session.refresh_token,
        max_age=REFRESH_TOKEN_TTL_DAYS * 86400,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )
    return SessionOut(
        access_token=session.access_token, user=UserOut.model_validate(session.user), organization_slug=session.organization.slug
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=SessionOut)
async def login(body: LoginIn, request: Request, response: Response, uow: Uow) -> SessionOut:
    return _respond(await AuthService(uow).login(body, _client_ip(request)), response)


@router.post("/register", response_model=SessionOut, status_code=201)
async def register(body: RegisterIn, response: Response, uow: Uow) -> SessionOut:
    return _respond(await AuthService(uow).register_customer(body), response)


@router.post("/refresh", response_model=SessionOut)
async def refresh(response: Response, uow: Uow, refresh_token: RefreshCookie = None) -> SessionOut:
    return _respond(await AuthService(uow).refresh(refresh_token), response)


@router.post("/logout", status_code=204)
async def logout(response: Response, uow: Uow, refresh_token: RefreshCookie = None) -> None:
    await AuthService(uow).logout(refresh_token)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=SessionOut)
async def me(actor: CurrentActor, uow: Uow, request: Request) -> SessionOut:
    """The signed-in user, re-issuing nothing: the access token is echoed back."""
    user = await UserRepository(uow.session, actor.org_id).find(actor.user_id)
    org = await OrganizationRepository(uow.session).by_id(actor.org_id)
    if user is None or org is None:
        raise UnauthorizedError()
    token = request.headers.get("authorization", "")[7:]
    return SessionOut(access_token=token, user=UserOut.model_validate(user), organization_slug=org.slug)
