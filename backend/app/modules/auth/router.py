"""Auth endpoints: register, login, me."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import create_access_token, get_current_account
from app.core.database import async_session
from app.modules.auth.models import Account
from app.modules.auth.schemas import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.modules.auth.service import authenticate, register_account

router = APIRouter(prefix="/api/auth", tags=["auth"])

CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    async with async_session() as session:
        try:
            account = await register_account(
                session,
                username=body.username,
                real_name=body.real_name,
                password=body.password,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    token = create_access_token(str(account.id))
    return {
        "success": True,
        "data": TokenResponse(
            token=token,
            account_id=str(account.id),
            username=account.username,
            real_name=account.real_name,
            is_admin=account.is_admin,
        ).model_dump(),
    }


@router.post("/login")
async def login(body: LoginRequest):
    async with async_session() as session:
        account = await authenticate(session, body.username, body.password)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة المرور غير صحيحة",
        )

    token = create_access_token(str(account.id))
    return {
        "success": True,
        "data": TokenResponse(
            token=token,
            account_id=str(account.id),
            username=account.username,
            real_name=account.real_name,
            is_admin=account.is_admin,
        ).model_dump(),
    }


@router.get("/me")
async def get_me(account: CurrentAccount):
    return {
        "success": True,
        "data": MeResponse(
            account_id=str(account.id),
            username=account.username,
            real_name=account.real_name,
            is_admin=account.is_admin,
        ).model_dump(),
    }
