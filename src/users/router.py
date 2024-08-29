from fastapi import APIRouter, HTTPException, status, Response, Request

from src.users.schemas import SUserCreate
from src.users.dao import UserDAO
from src.users.utils import hash_password, authenticate_user
from src.users.auth import AuthenticationService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register")
async def user_register(body: SUserCreate):
    user = await UserDAO.get_one(email=body.email)

    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email, already exists",
        )

    hashed_password = hash_password(body.password)

    await UserDAO.add(email=body.email, password=hashed_password)


@router.post("/login")
async def user_login(request: Request, response: Response, body: SUserCreate):
    user = await authenticate_user(body.email, body.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if request.cookies.get("access_token") or request.cookies.get("refresh_token"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already logged in",
        )
    data = {"sub": user.id}
    tokens = await AuthenticationService.login(data)

    response.set_cookie("access_token", tokens.get("access"), httponly=True)
    response.set_cookie("refresh_token", tokens.get("refresh"), httponly=True)

    return tokens


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    new_tokens = await AuthenticationService.refresh_tokens(
        request.cookies.get("refresh_token")
    )

    response.set_cookie("access_token", new_tokens.get("access"), httponly=True)
    response.set_cookie("refresh_token", new_tokens.get("refresh"), httponly=True)

    return new_tokens


@router.post("/logout")
async def user_logout(request: Request, response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    await AuthenticationService.logout(request.cookies.get("refresh_token"))
