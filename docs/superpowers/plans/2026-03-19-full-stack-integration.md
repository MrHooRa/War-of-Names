# Full-Stack Integration Plan — War of Names

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform all static/placeholder frontend pages into a real DB-backed full-stack system with working auth, sessions, competition membership, dashboard, leaderboard, attacks, store, quiz, and notifications.

**Architecture:** JWT-based stateless auth (python-jose + bcrypt); token stored in `localStorage`; React Context for current-user state; all score mutations routed through the existing Ledger; competition context resolved server-side via `/api/me/competition-context`. Backend is FastAPI + SQLAlchemy async. Frontend is React + Vite.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, python-jose, passlib[bcrypt], React 19, React Router 7, Vite 6, Tailwind CSS

---

## Gap Analysis (Current State)

### Static / Fake / Missing:
- **Auth**: No login/register/logout endpoints. No JWT. RegisterPage is a visual-only form with a Link instead of form submit. No auth state in frontend.
- **Session**: No current-user concept. `useCompetitionContext` calls a non-existent `/api/competition-context` endpoint.
- **Dashboard**: All numbers (balance, rank, attacks) are hardcoded strings in JSX.
- **Leaderboard**: Now wired to API but the API endpoint exists; however competition_id comes from `useCompetitionContext` which is broken.
- **Attack flow**: `attackerMembershipId` is null because `useCompetitionContext` returns null. Attacks cannot work without a real logged-in user.
- **Store**: `StorePage` is entirely hardcoded. No backend store endpoints.
- **Quiz**: `QuizPage` is entirely hardcoded. No backend quiz endpoints.
- **Notifications**: No backend notification endpoints. No frontend notification UI wired to real data.
- **Seeding**: Only `game_info` is seeded. No competition, seasons, cycles, memberships, items, questions, or notifications.
- **Backend packages**: `python-jose` and `passlib[bcrypt]` not in `pyproject.toml`.

---

## File Map

### New Backend Files
```
backend/app/core/auth.py              — JWT create/verify, password hash/verify, get_current_user dependency
backend/app/core/seed.py              — one-shot seeder: competition, season, cycle, items, questions
backend/app/modules/auth/schemas.py   — RegisterRequest, LoginRequest, TokenResponse, MeResponse
backend/app/modules/auth/router.py    — POST /auth/register, POST /auth/login, GET /auth/me, POST /auth/logout
backend/app/modules/auth/service.py   — register_account, authenticate, get_account_by_id
backend/app/modules/competitions/schemas.py   — JoinRequest, MembershipResponse, CompetitionContextResponse
backend/app/modules/competitions/router.py    — POST /competitions/{id}/join, GET /me/competition-context
backend/app/modules/dashboard/router.py       — GET /me/dashboard
backend/app/modules/store/schemas.py          — StoreListingResponse, PurchaseRequest, InventoryResponse
backend/app/modules/store/router.py           — GET /competitions/{id}/store, POST /competitions/{id}/store/purchase, GET /me/inventory
backend/app/modules/quiz/schemas.py           — SessionResponse, QuestionResponse, AnswerRequest, AnswerResponse
backend/app/modules/quiz/router.py            — GET /competitions/{id}/quiz/session, GET /quiz/sessions/{id}/question, POST /quiz/sessions/{id}/answer
backend/app/modules/notifications/router.py   — GET /me/notifications, POST /me/notifications/{id}/read
```

### Modified Backend Files
```
backend/pyproject.toml               — add python-jose[cryptography], passlib[bcrypt]
backend/app/config.py                — add jwt_secret, jwt_expire_minutes
backend/app/main.py                  — register all new routers, call seed on startup
backend/app/core/models.py           — no change (schema already complete)
```

### New Frontend Files
```
frontend/src/context/AuthContext.jsx           — React context: currentUser, token, login, logout, loading
frontend/src/hooks/useAuth.js                  — convenience hook wrapping AuthContext
frontend/src/hooks/useDashboard.js             — fetches GET /api/me/dashboard
frontend/src/hooks/useNotifications.js         — fetches GET /api/me/notifications
frontend/src/hooks/useStore.js                 — fetches GET /api/competitions/{id}/store
frontend/src/hooks/useInventory.js             — fetches GET /api/me/inventory
frontend/src/hooks/useQuizSession.js           — fetches active quiz session + current question
frontend/src/components/ProtectedRoute.jsx     — redirects to /login if no token
frontend/src/pages/LoginPage.jsx               — login form, POST /api/auth/login
```

### Modified Frontend Files
```
frontend/src/App.jsx                           — add AuthProvider, ProtectedRoute, /login route
frontend/src/pages/RegisterPage.jsx            — wire form to POST /api/auth/register
frontend/src/pages/JoinPage.jsx                — wire form to POST /api/competitions/{id}/join
frontend/src/pages/DashboardPage.jsx           — use useDashboard() hook (real data)
frontend/src/pages/StorePage.jsx               — use useStore() hook (real catalog)
frontend/src/pages/QuizPage.jsx                — use useQuizSession() hook (real questions)
frontend/src/components/AppLayout.jsx          — show real user alias+balance; logout button
frontend/src/hooks/useCompetitionContext.js    — fix to use real /api/me/competition-context with auth token
frontend/src/hooks/useAttackPreview.js         — pass Authorization header
frontend/src/hooks/useAttackExecute.js         — pass Authorization header
frontend/src/hooks/useLeaderboard.js           — pass Authorization header
frontend/src/hooks/usePlayerProfile.js         — pass Authorization header
frontend/src/hooks/useMemberIdentities.js      — pass Authorization header
```

---

## Task 1: Add Auth Dependencies to Backend

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`

- [ ] Add `python-jose[cryptography]>=3.3` and `passlib[bcrypt]>=1.7` to `[project].dependencies` in `pyproject.toml`

```toml
# backend/pyproject.toml — add to dependencies list:
"python-jose[cryptography]>=3.3",
"passlib[bcrypt]>=1.7",
```

- [ ] Add JWT config to `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    jwt_secret: str = "change-me-in-production-please"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    cors_origin: str = "http://localhost:5173"
```

- [ ] Rebuild the API Docker container so new packages are installed:
```bash
docker compose build --no-cache api && docker compose up -d api
```

---

## Task 2: Core Auth Utilities

**Files:**
- Create: `backend/app/core/auth.py`

- [ ] Create the file:

```python
"""JWT creation/verification and password hashing utilities."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from app.config import settings
from app.core.database import async_session
from app.modules.auth.models import Account

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(account_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": account_id, "exp": expire},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


async def get_current_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Account:
    """FastAPI dependency — resolves Bearer token to Account or raises 401."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="يرجى تسجيل الدخول أولاً",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise exc
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        account_id: str | None = payload.get("sub")
        if not account_id:
            raise exc
    except JWTError:
        raise exc

    async with async_session() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        account = result.scalars().first()

    if not account or account.status != "active":
        raise exc
    return account
```

---

## Task 3: Auth Service + Schemas + Router

**Files:**
- Create: `backend/app/modules/auth/schemas.py`
- Create: `backend/app/modules/auth/service.py`
- Create: `backend/app/modules/auth/router.py`

- [ ] Create `backend/app/modules/auth/schemas.py`:

```python
"""Auth request/response Pydantic models."""
from pydantic import BaseModel, field_validator
import re


class RegisterRequest(BaseModel):
    username: str
    real_name: str
    password: str

    @field_validator("username")
    @classmethod
    def username_clean(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", v):
            raise ValueError("اسم المستخدم يجب أن يكون بين 3-30 حرفاً (أحرف إنجليزية وأرقام وشرطة سفلية فقط)")
        return v

    @field_validator("real_name")
    @classmethod
    def real_name_clean(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 100:
            raise ValueError("الاسم الحقيقي يجب أن يكون بين 2-100 حرف")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("كلمة المرور يجب أن تكون 6 أحرف على الأقل")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    account_id: str
    username: str
    real_name: str


class MeResponse(BaseModel):
    account_id: str
    username: str
    real_name: str
```

- [ ] Create `backend/app/modules/auth/service.py`:

```python
"""Account registration and authentication service."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password, verify_password
from app.core.enums import AccountStatus
from app.modules.auth.models import Account


async def register_account(
    session: AsyncSession,
    username: str,
    real_name: str,
    password: str,
) -> Account:
    # Check uniqueness
    existing = await session.execute(
        select(Account).where(Account.username == username)
    )
    if existing.scalars().first():
        raise ValueError("اسم المستخدم مستخدم بالفعل")

    account = Account(
        id=uuid.uuid4(),
        username=username,
        real_name=real_name,
        password_hash=hash_password(password),
        status=AccountStatus.ACTIVE,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


async def authenticate(
    session: AsyncSession,
    username: str,
    password: str,
) -> Account | None:
    result = await session.execute(
        select(Account).where(Account.username == username)
    )
    account = result.scalars().first()
    if not account:
        return None
    if not verify_password(password, account.password_hash):
        return None
    return account
```

- [ ] Create `backend/app/modules/auth/router.py`:

```python
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


@router.post("/register", response_model=dict, status_code=201)
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
        ).model_dump(),
    }


@router.post("/login", response_model=dict)
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
        ).model_dump(),
    }


@router.get("/me", response_model=dict)
async def get_me(account: CurrentAccount):
    return {
        "success": True,
        "data": MeResponse(
            account_id=str(account.id),
            username=account.username,
            real_name=account.real_name,
        ).model_dump(),
    }
```

---

## Task 4: Competition Join + Context Endpoints

**Files:**
- Create: `backend/app/modules/competitions/schemas.py`
- Create: `backend/app/modules/competitions/router.py`

- [ ] Create `backend/app/modules/competitions/schemas.py`:

```python
"""Competition and membership Pydantic models."""
import uuid
from pydantic import BaseModel


class JoinRequest(BaseModel):
    invite_code: str
    alias: str


class MembershipResponse(BaseModel):
    membership_id: str
    competition_id: str
    competition_name: str
    alias: str
    balance: int
    protection: str
    is_bankrupt: bool


class CompetitionContextResponse(BaseModel):
    competition_id: str
    competition_name: str
    season_id: str | None
    cycle_id: str | None
    membership_id: str
    alias: str
    balance: int
    protection: str
    is_bankrupt: bool
    rank: int | None
```

- [ ] Create `backend/app/modules/competitions/router.py`:

```python
"""Competition join + current-user context endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import InviteStatus, MembershipStatus
from app.modules.auth.models import Account
from app.modules.competitions.models import (
    AliasRecord,
    Competition,
    CompetitionInvite,
    Cycle,
    Membership,
    Season,
)
from app.modules.competitions.schemas import CompetitionContextResponse, JoinRequest
from app.modules.scoring.models import LedgerEntry
from app.core.enums import LedgerDirection, LedgerEntryType

router = APIRouter(tags=["competitions"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]

INITIAL_BALANCE = 1000  # points granted on join


@router.post("/api/competitions/{competition_id}/join", response_model=dict)
async def join_competition(
    competition_id: uuid.UUID,
    body: JoinRequest,
    account: CurrentAccount,
):
    async with async_session() as session:
        # Validate invite code
        invite_result = await session.execute(
            select(CompetitionInvite).where(
                CompetitionInvite.competition_id == competition_id,
                CompetitionInvite.code == body.invite_code,
                CompetitionInvite.status == InviteStatus.ACTIVE,
            )
        )
        invite = invite_result.scalars().first()
        if not invite:
            raise HTTPException(status_code=400, detail="رمز الدعوة غير صالح أو منتهي الصلاحية")

        # Check max_uses
        if invite.max_uses and invite.use_count >= invite.max_uses:
            raise HTTPException(status_code=400, detail="رمز الدعوة وصل للحد الأقصى من الاستخدامات")

        # Check not already a member
        existing = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.competition_id == competition_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="أنت مسجل بالفعل في هذه المنافسة")

        # Check alias uniqueness in this competition
        alias_conflict = await session.execute(
            select(Membership).where(
                Membership.competition_id == competition_id,
                Membership.current_alias == body.alias.strip(),
            )
        )
        if alias_conflict.scalars().first():
            raise HTTPException(status_code=400, detail="هذا اللقب مستخدم بالفعل في المنافسة")

        # Create membership
        membership = Membership(
            account_id=account.id,
            competition_id=competition_id,
            status=MembershipStatus.ACTIVE,
            current_alias=body.alias.strip(),
            current_balance=INITIAL_BALANCE,
        )
        session.add(membership)
        await session.flush()

        # Get active season/cycle for ledger context
        season = (await session.execute(
            select(Season).where(Season.competition_id == competition_id, Season.status == "active").limit(1)
        )).scalars().first()
        cycle = None
        if season:
            cycle = (await session.execute(
                select(Cycle).where(Cycle.season_id == season.id, Cycle.status == "active").limit(1)
            )).scalars().first()

        # Grant initial balance via ledger
        ledger_entry = LedgerEntry(
            membership_id=membership.id,
            competition_id=competition_id,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            entry_type=LedgerEntryType.INITIAL_BALANCE,
            amount=INITIAL_BALANCE,
            direction=LedgerDirection.CREDIT,
            balance_before=0,
            balance_after=INITIAL_BALANCE,
            reason="رصيد ابتدائي عند الانضمام",
        )
        session.add(ledger_entry)

        # Create alias record
        alias_record = AliasRecord(
            membership_id=membership.id,
            alias_value=body.alias.strip(),
            is_active=True,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
        )
        session.add(alias_record)

        # Increment invite use count
        invite.use_count += 1

        await session.commit()

    return {
        "success": True,
        "data": {
            "membership_id": str(membership.id),
            "alias": membership.current_alias,
            "balance": membership.current_balance,
        },
        "message": f"أهلاً بك في المنافسة يا {body.alias}! رصيدك الابتدائي: {INITIAL_BALANCE} نقطة",
    }


@router.get("/api/me/competition-context", response_model=dict)
async def get_competition_context(account: CurrentAccount):
    """
    Returns the active competition context for the current user.
    Picks the first active competition the user has a membership in.
    """
    async with async_session() as session:
        # Find user's active membership
        mem_result = await session.execute(
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
                Competition.status == "active",
            )
            .limit(1)
        )
        row = mem_result.first()
        if not row:
            return {"success": True, "data": None}

        membership, competition = row

        # Get active season + cycle
        season = (await session.execute(
            select(Season).where(
                Season.competition_id == competition.id,
                Season.status == "active",
            ).limit(1)
        )).scalars().first()

        cycle = None
        if season:
            cycle = (await session.execute(
                select(Cycle).where(
                    Cycle.season_id == season.id,
                    Cycle.status == "active",
                ).limit(1)
            )).scalars().first()

        # Compute rank (count of members with higher balance)
        rank_result = await session.execute(
            select(func.count()).where(
                Membership.competition_id == competition.id,
                Membership.status == MembershipStatus.ACTIVE,
                Membership.current_balance > membership.current_balance,
            )
        )
        rank = (rank_result.scalar() or 0) + 1

    return {
        "success": True,
        "data": CompetitionContextResponse(
            competition_id=str(competition.id),
            competition_name=competition.name,
            season_id=str(season.id) if season else None,
            cycle_id=str(cycle.id) if cycle else None,
            membership_id=str(membership.id),
            alias=membership.current_alias or account.username,
            balance=membership.current_balance,
            protection=membership.protection,
            is_bankrupt=membership.is_bankrupt,
            rank=rank,
        ).model_dump(),
    }
```

---

## Task 5: Dashboard Endpoint

**Files:**
- Create: `backend/app/modules/dashboard/` directory with `__init__.py` and `router.py`

- [ ] Create `backend/app/modules/dashboard/__init__.py` (empty)

- [ ] Create `backend/app/modules/dashboard/router.py`:

```python
"""Dashboard read-model endpoint — aggregates player stats for the home page."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import AttackOutcome, MembershipStatus
from app.modules.attacks.models import AttackAttempt
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, Membership, Season
from app.modules.notifications.models import Notification
from app.modules.store.models import OwnedItem

router = APIRouter(tags=["dashboard"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/api/me/dashboard")
async def get_dashboard(account: CurrentAccount):
    """
    Returns all data needed to render the player dashboard:
    - membership info (alias, balance, rank, protection)
    - attack stats (attacks sent, won, received)
    - inventory count
    - unread notification count
    - game announcement
    """
    async with async_session() as session:
        # Active membership
        mem_result = await session.execute(
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
                Competition.status == "active",
            )
            .limit(1)
        )
        row = mem_result.first()
        if not row:
            return {"success": True, "data": None}

        membership, competition = row

        # Rank
        rank_result = await session.execute(
            select(func.count()).where(
                Membership.competition_id == competition.id,
                Membership.status == MembershipStatus.ACTIVE,
                Membership.current_balance > membership.current_balance,
            )
        )
        rank = (rank_result.scalar() or 0) + 1

        # Attacks SENT by this member
        attacks_sent = (await session.execute(
            select(func.count()).where(
                AttackAttempt.attacker_id == membership.id,
                AttackAttempt.outcome.in_([AttackOutcome.SUCCEEDED, AttackOutcome.FAILED]),
            )
        )).scalar() or 0

        attacks_won = (await session.execute(
            select(func.count()).where(
                AttackAttempt.attacker_id == membership.id,
                AttackAttempt.outcome == AttackOutcome.SUCCEEDED,
            )
        )).scalar() or 0

        # Attacks RECEIVED by this member
        attacks_received = (await session.execute(
            select(func.count()).where(
                AttackAttempt.target_id == membership.id,
                AttackAttempt.outcome.in_([AttackOutcome.SUCCEEDED, AttackOutcome.FAILED]),
            )
        )).scalar() or 0

        attacks_defended = (await session.execute(
            select(func.count()).where(
                AttackAttempt.target_id == membership.id,
                AttackAttempt.outcome == AttackOutcome.FAILED,
            )
        )).scalar() or 0

        # Inventory count
        inventory_count = (await session.execute(
            select(func.count()).where(
                OwnedItem.membership_id == membership.id,
                OwnedItem.status == "available",
            )
        )).scalar() or 0

        # Unread notifications
        unread_notif = (await session.execute(
            select(func.count()).where(
                Notification.recipient_id == account.id,
                Notification.is_read == False,
            )
        )).scalar() or 0

        # Win rate
        win_rate = round((attacks_won / attacks_sent * 100) if attacks_sent > 0 else 0)

    return {
        "success": True,
        "data": {
            "account_id": str(account.id),
            "username": account.username,
            "real_name": account.real_name,
            "membership_id": str(membership.id),
            "competition_id": str(competition.id),
            "competition_name": competition.name,
            "alias": membership.current_alias or account.username,
            "balance": membership.current_balance,
            "rank": rank,
            "protection": membership.protection,
            "is_bankrupt": membership.is_bankrupt,
            "attacks_sent": attacks_sent,
            "attacks_won": attacks_won,
            "attacks_received": attacks_received,
            "attacks_defended": attacks_defended,
            "win_rate": win_rate,
            "inventory_count": inventory_count,
            "unread_notifications": unread_notif,
        },
    }
```

---

## Task 6: Store Endpoints

**Files:**
- Create: `backend/app/modules/store/schemas.py`
- Create: `backend/app/modules/store/router.py`

- [ ] Create `backend/app/modules/store/schemas.py`:

```python
"""Store request/response models."""
import uuid
from pydantic import BaseModel


class PurchaseRequest(BaseModel):
    listing_id: uuid.UUID
```

- [ ] Create `backend/app/modules/store/router.py`:

```python
"""Store catalog, purchase, and inventory endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import (
    LedgerDirection,
    LedgerEntryType,
    ListingStatus,
    MembershipStatus,
    OwnedItemStatus,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import Cycle, Membership, Season
from app.modules.scoring.models import LedgerEntry
from app.modules.store.models import ItemDefinition, OwnedItem, StoreListing
from app.modules.store.schemas import PurchaseRequest

router = APIRouter(tags=["store"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/api/competitions/{competition_id}/store")
async def get_store(competition_id: uuid.UUID, account: CurrentAccount):
    """Active store listings for the competition."""
    async with async_session() as session:
        result = await session.execute(
            select(StoreListing, ItemDefinition)
            .join(ItemDefinition, StoreListing.item_definition_id == ItemDefinition.id)
            .where(
                StoreListing.competition_id == competition_id,
                StoreListing.status == ListingStatus.ACTIVE,
            )
            .order_by(StoreListing.price)
        )
        rows = result.all()

    items = [
        {
            "listing_id": str(listing.id),
            "item_id": str(item.id),
            "name": item.name,
            "description": item.description,
            "rarity": item.rarity,
            "category": item.category,
            "usage_type": item.usage_type,
            "price": listing.price,
            "max_per_participant": listing.max_per_participant,
            "total_stock": listing.total_stock,
            "sold_count": listing.sold_count,
            "in_stock": listing.total_stock is None or listing.sold_count < listing.total_stock,
        }
        for listing, item in rows
    ]

    return {"success": True, "data": items}


@router.post("/api/competitions/{competition_id}/store/purchase")
async def purchase_item(
    competition_id: uuid.UUID,
    body: PurchaseRequest,
    account: CurrentAccount,
):
    """Purchase a store item — deducts from balance via ledger."""
    async with async_session() as session:
        # Load listing
        listing_result = await session.execute(
            select(StoreListing, ItemDefinition)
            .join(ItemDefinition, StoreListing.item_definition_id == ItemDefinition.id)
            .where(
                StoreListing.id == body.listing_id,
                StoreListing.competition_id == competition_id,
                StoreListing.status == ListingStatus.ACTIVE,
            )
        )
        row = listing_result.first()
        if not row:
            raise HTTPException(status_code=404, detail="العنصر غير موجود في المتجر")

        listing, item_def = row

        # Check stock
        if listing.total_stock and listing.sold_count >= listing.total_stock:
            raise HTTPException(status_code=400, detail="المخزون نفد")

        # Load membership
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.competition_id == competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        membership = mem_result.scalars().first()
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المنافسة")

        # Check balance
        if membership.current_balance < listing.price:
            raise HTTPException(
                status_code=400,
                detail=f"رصيدك غير كافٍ ({membership.current_balance} نقطة، المطلوب: {listing.price})",
            )

        # Check max_per_participant
        if listing.max_per_participant:
            owned_count = (await session.execute(
                select(OwnedItem).where(
                    OwnedItem.membership_id == membership.id,
                    OwnedItem.item_definition_id == item_def.id,
                )
            )).scalars().all()
            if len(owned_count) >= listing.max_per_participant:
                raise HTTPException(status_code=400, detail="وصلت للحد الأقصى من هذا العنصر")

        # Get season/cycle
        season = (await session.execute(
            select(Season).where(
                Season.competition_id == competition_id, Season.status == "active"
            ).limit(1)
        )).scalars().first()
        cycle = None
        if season:
            cycle = (await session.execute(
                select(Cycle).where(
                    Cycle.season_id == season.id, Cycle.status == "active"
                ).limit(1)
            )).scalars().first()

        # Deduct balance
        balance_before = membership.current_balance
        balance_after = balance_before - listing.price
        membership.current_balance = balance_after

        # Ledger entry
        ledger = LedgerEntry(
            membership_id=membership.id,
            competition_id=competition_id,
            season_id=season.id if season else None,
            cycle_id=cycle.id if cycle else None,
            entry_type=LedgerEntryType.ITEM_PURCHASE,
            amount=listing.price,
            direction=LedgerDirection.DEBIT,
            balance_before=balance_before,
            balance_after=balance_after,
            source_type="store_listing",
            source_id=listing.id,
            reason=f"شراء: {item_def.name}",
        )
        session.add(ledger)

        # Create owned item
        owned = OwnedItem(
            membership_id=membership.id,
            item_definition_id=item_def.id,
            source_type="purchase",
            source_id=listing.id,
            quantity=1,
            status=OwnedItemStatus.AVAILABLE,
        )
        session.add(owned)

        # Update stock
        listing.sold_count += 1

        await session.commit()

    return {
        "success": True,
        "data": {
            "owned_item_id": str(owned.id),
            "item_name": item_def.name,
            "price_paid": listing.price,
            "balance_after": balance_after,
        },
        "message": f"تم شراء {item_def.name} بنجاح!",
    }


@router.get("/api/me/inventory")
async def get_inventory(account: CurrentAccount):
    """Returns all owned items for the current user across active competition."""
    async with async_session() as session:
        # Get active membership
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
            ).limit(1)
        )
        membership = mem_result.scalars().first()
        if not membership:
            return {"success": True, "data": []}

        result = await session.execute(
            select(OwnedItem, ItemDefinition)
            .join(ItemDefinition, OwnedItem.item_definition_id == ItemDefinition.id)
            .where(
                OwnedItem.membership_id == membership.id,
                OwnedItem.status.in_(["available", "activated"]),
            )
            .order_by(OwnedItem.acquired_at.desc())
        )
        rows = result.all()

    inventory = [
        {
            "owned_item_id": str(owned.id),
            "item_id": str(item.id),
            "name": item.name,
            "description": item.description,
            "rarity": item.rarity,
            "category": item.category,
            "status": owned.status,
            "quantity": owned.quantity,
            "acquired_at": owned.acquired_at.isoformat(),
        }
        for owned, item in rows
    ]

    return {"success": True, "data": inventory}
```

---

## Task 7: Quiz Endpoints

**Files:**
- Create: `backend/app/modules/quiz/schemas.py`
- Create: `backend/app/modules/quiz/router.py`

- [ ] Create `backend/app/modules/quiz/schemas.py`:

```python
"""Quiz Pydantic models."""
import uuid
from pydantic import BaseModel


class AnswerRequest(BaseModel):
    submitted_answer: dict  # {"answer": "A"} or {"answer": True}
```

- [ ] Create `backend/app/modules/quiz/router.py`:

```python
"""Quiz session and answer submission endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import (
    AnswerEvalStatus,
    LedgerDirection,
    LedgerEntryType,
    MembershipStatus,
    SessionStatus,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import Cycle, Membership, Season
from app.modules.quiz.models import AnswerSubmission, QuizSession, SessionQuestion
from app.modules.quiz.schemas import AnswerRequest
from app.modules.scoring.models import LedgerEntry

router = APIRouter(tags=["quiz"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/api/competitions/{competition_id}/quiz/session")
async def get_active_session(competition_id: uuid.UUID, account: CurrentAccount):
    """Returns the currently open quiz session for this competition, if any."""
    async with async_session() as session:
        result = await session.execute(
            select(QuizSession).where(
                QuizSession.competition_id == competition_id,
                QuizSession.status == SessionStatus.OPEN,
            ).limit(1)
        )
        quiz_session = result.scalars().first()

    if not quiz_session:
        return {"success": True, "data": None, "message": "لا توجد جلسة أسئلة مفتوحة الآن"}

    questions_list = [
        {
            "session_question_id": str(sq.id),
            "delivery_order": sq.delivery_order,
            "prompt": sq.effective_prompt_snapshot,
            "options": sq.effective_options_snapshot,
            "score_value": sq.effective_score_value,
        }
        for sq in sorted(quiz_session.session_questions, key=lambda q: q.delivery_order)
    ]

    return {
        "success": True,
        "data": {
            "session_id": str(quiz_session.id),
            "title": quiz_session.title,
            "status": quiz_session.status,
            "answer_duration_seconds": quiz_session.answer_duration_seconds,
            "questions": questions_list,
            "ends_at": quiz_session.ends_at.isoformat() if quiz_session.ends_at else None,
        },
    }


@router.post("/api/quiz/sessions/{session_id}/answer")
async def submit_answer(
    session_id: uuid.UUID,
    body: AnswerRequest,
    account: CurrentAccount,
):
    """
    Submit an answer for a session question.
    Body must include session_question_id in the submitted_answer dict.
    On correct answer: awards points via ledger.
    """
    session_question_id = body.submitted_answer.get("session_question_id")
    if not session_question_id:
        raise HTTPException(status_code=400, detail="session_question_id مطلوب في الإجابة")

    async with async_session() as session:
        # Load quiz session
        quiz_session = await session.get(QuizSession, session_id)
        if not quiz_session or quiz_session.status != SessionStatus.OPEN:
            raise HTTPException(status_code=400, detail="الجلسة غير مفتوحة")

        # Load session question
        sq_result = await session.execute(
            select(SessionQuestion).where(
                SessionQuestion.id == session_question_id,
                SessionQuestion.session_id == session_id,
            )
        )
        sq = sq_result.scalars().first()
        if not sq:
            raise HTTPException(status_code=404, detail="السؤال غير موجود في هذه الجلسة")

        # Load question (for correct_answer)
        from app.modules.quiz.models import Question
        question = await session.get(Question, sq.question_id)

        # Load membership
        mem_result = await session.execute(
            select(Membership).where(
                Membership.account_id == account.id,
                Membership.competition_id == quiz_session.competition_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        membership = mem_result.scalars().first()
        if not membership:
            raise HTTPException(status_code=403, detail="أنت لست عضواً في هذه المنافسة")

        # Check not already answered
        existing = await session.execute(
            select(AnswerSubmission).where(
                AnswerSubmission.membership_id == membership.id,
                AnswerSubmission.session_question_id == sq.id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="لقد أجبت على هذا السؤال بالفعل")

        # Evaluate correctness
        submitted = body.submitted_answer.get("answer")
        correct_answer = question.correct_answer.get("answer")
        is_correct = str(submitted).strip().lower() == str(correct_answer).strip().lower()
        points = sq.effective_score_value if is_correct else 0

        # Create submission record
        submission = AnswerSubmission(
            membership_id=membership.id,
            session_id=session_id,
            session_question_id=sq.id,
            submitted_answer=body.submitted_answer,
            status=AnswerEvalStatus.EVALUATED,
            is_correct=is_correct,
            points_awarded=points,
            evaluated_at=datetime.now(timezone.utc),
        )
        session.add(submission)

        # Award points via ledger if correct
        if is_correct:
            season = (await session.execute(
                select(Season).where(
                    Season.competition_id == quiz_session.competition_id,
                    Season.status == "active",
                ).limit(1)
            )).scalars().first()
            cycle = None
            if season:
                cycle = (await session.execute(
                    select(Cycle).where(
                        Cycle.season_id == season.id, Cycle.status == "active"
                    ).limit(1)
                )).scalars().first()

            ledger = LedgerEntry(
                membership_id=membership.id,
                competition_id=quiz_session.competition_id,
                season_id=season.id if season else None,
                cycle_id=cycle.id if cycle else None,
                entry_type=LedgerEntryType.QUESTION_REWARD,
                amount=points,
                direction=LedgerDirection.CREDIT,
                balance_before=membership.current_balance,
                balance_after=membership.current_balance + points,
                source_type="answer_submission",
                source_id=submission.id,
                reason=f"إجابة صحيحة — {sq.effective_prompt_snapshot[:50]}",
            )
            session.add(ledger)
            membership.current_balance += points

        await session.commit()

    return {
        "success": True,
        "data": {
            "is_correct": is_correct,
            "points_awarded": points,
            "correct_answer": correct_answer if not is_correct else None,
        },
        "message": "إجابة صحيحة!" if is_correct else "إجابة خاطئة",
    }
```

---

## Task 8: Notifications Endpoint

**Files:**
- Create: `backend/app/modules/notifications/router.py`

- [ ] Create the file:

```python
"""Notification read endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, update

from app.core.auth import get_current_account
from app.core.database import async_session
from app.modules.auth.models import Account
from app.modules.notifications.models import Notification

router = APIRouter(tags=["notifications"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.get("/api/me/notifications")
async def get_notifications(account: CurrentAccount, limit: int = 20):
    async with async_session() as session:
        result = await session.execute(
            select(Notification)
            .where(Notification.recipient_id == account.id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        notifs = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(n.id),
                "type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "priority": n.priority,
                "reference_type": n.reference_type,
                "reference_id": str(n.reference_id) if n.reference_id else None,
                "deep_link": n.deep_link,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifs
        ],
    }


@router.post("/api/me/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: uuid.UUID, account: CurrentAccount):
    async with async_session() as session:
        await session.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_id == account.id,
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await session.commit()

    return {"success": True}
```

---

## Task 9: Seeder — Real DB Bootstrap Data

**Files:**
- Create: `backend/app/core/seed.py`

- [ ] Create the seeder. This must run once on startup and be idempotent:

```python
"""
One-shot seeder: creates minimal real DB records for the game to function.

Idempotent — checks existence before inserting.
Seeded records:
  - 1 active Competition
  - 1 active Season
  - 1 active Cycle
  - 1 CompetitionInvite (code: "WAR2026")
  - 5 ItemDefinitions + StoreListing
  - 1 QuestionGroup + 5 Questions
  - 1 open QuizSession + 5 SessionQuestions
  - GameInfo row (already handled in main.py, skipped here)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    CompetitionStatus,
    CycleStatus,
    InviteStatus,
    InviteType,
    ItemAcquisitionType,
    ItemRarity,
    ItemStatus,
    ItemUsageType,
    ListingStatus,
    MembershipStatus,
    QuestionDifficulty,
    QuestionStatus,
    QuestionType,
    SeasonStatus,
    SessionStatus,
    SessionType,
)
from app.modules.competitions.models import Competition, CompetitionInvite, Cycle, Season
from app.modules.quiz.models import Question, QuestionGroup, QuizSession, SessionQuestion
from app.modules.store.models import ItemDefinition, StoreListing


COMPETITION_NAME = "موسم حرب الأسماء الأول"
INVITE_CODE = "WAR2026"

# A stable seed UUID for the competition so subsequent runs are idempotent
SEED_COMPETITION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SEED_SEASON_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
SEED_CYCLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
SEED_ACCOUNT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")  # system account placeholder


async def seed(session: AsyncSession) -> None:
    """Run all seed operations. Safe to call on every startup."""
    await _seed_competition(session)
    await _seed_items(session)
    await _seed_quiz(session)


async def _seed_competition(session: AsyncSession) -> None:
    # Competition
    existing = await session.get(Competition, SEED_COMPETITION_ID)
    if not existing:
        comp = Competition(
            id=SEED_COMPETITION_ID,
            name=COMPETITION_NAME,
            status=CompetitionStatus.ACTIVE,
            registration_open=True,
            visibility="private",
            created_by=SEED_ACCOUNT_ID,
        )
        session.add(comp)

    # Season
    existing_season = await session.get(Season, SEED_SEASON_ID)
    if not existing_season:
        season = Season(
            id=SEED_SEASON_ID,
            competition_id=SEED_COMPETITION_ID,
            name="الموسم الأول",
            order_index=1,
            status=SeasonStatus.ACTIVE,
            starts_at=datetime.now(timezone.utc),
        )
        session.add(season)

    # Cycle
    existing_cycle = await session.get(Cycle, SEED_CYCLE_ID)
    if not existing_cycle:
        cycle = Cycle(
            id=SEED_CYCLE_ID,
            season_id=SEED_SEASON_ID,
            label="الدورة الأولى",
            order_index=1,
            status=CycleStatus.ACTIVE,
            starts_at=datetime.now(timezone.utc),
        )
        session.add(cycle)

    # Invite
    invite_result = await session.execute(
        select(CompetitionInvite).where(CompetitionInvite.code == INVITE_CODE)
    )
    if not invite_result.scalars().first():
        invite = CompetitionInvite(
            competition_id=SEED_COMPETITION_ID,
            invite_type=InviteType.CODE,
            code=INVITE_CODE,
            status=InviteStatus.ACTIVE,
            max_uses=None,  # unlimited
        )
        session.add(invite)

    await session.commit()


async def _seed_items(session: AsyncSession) -> None:
    # Check if any items exist for this competition
    existing = await session.execute(
        select(StoreListing).where(StoreListing.competition_id == SEED_COMPETITION_ID).limit(1)
    )
    if existing.scalars().first():
        return  # already seeded

    items_data = [
        {
            "name": "درع الحماية",
            "description": "يحميك من هجوم واحد قادم خلال 24 ساعة",
            "rarity": ItemRarity.COMMON,
            "category": "protection",
            "price": 200,
        },
        {
            "name": "كاشف الهوية",
            "description": "يكشف لك لقب حقيقي واحد مختار",
            "rarity": ItemRarity.RARE,
            "category": "intelligence",
            "price": 400,
        },
        {
            "name": "مضاعف النقاط",
            "description": "يضاعف نقاط هجومك التالي بمعدل 1.5×",
            "rarity": ItemRarity.EPIC,
            "category": "boost",
            "price": 600,
        },
        {
            "name": "صندوق الغموض",
            "description": "افتحه لتحصل على جائزة مفاجئة",
            "rarity": ItemRarity.LEGENDARY,
            "category": "box",
            "price": 800,
        },
        {
            "name": "تغيير اللقب",
            "description": "يتيح لك تغيير اسمك المستعار مرة واحدة",
            "rarity": ItemRarity.COMMON,
            "category": "identity",
            "price": 150,
        },
    ]

    for item_data in items_data:
        item = ItemDefinition(
            name=item_data["name"],
            description=item_data["description"],
            rarity=item_data["rarity"],
            status=ItemStatus.ACTIVE,
            category=item_data["category"],
            acquisition_type=ItemAcquisitionType.PURCHASE,
            usage_type=ItemUsageType.CONSUMABLE,
        )
        session.add(item)
        await session.flush()

        listing = StoreListing(
            item_definition_id=item.id,
            competition_id=SEED_COMPETITION_ID,
            season_id=SEED_SEASON_ID,
            cycle_id=SEED_CYCLE_ID,
            status=ListingStatus.ACTIVE,
            price=item_data["price"],
        )
        session.add(listing)

    await session.commit()


async def _seed_quiz(session: AsyncSession) -> None:
    # Check if quiz session exists
    existing_session = await session.execute(
        select(QuizSession).where(
            QuizSession.competition_id == SEED_COMPETITION_ID,
            QuizSession.status == SessionStatus.OPEN,
        ).limit(1)
    )
    if existing_session.scalars().first():
        return  # already seeded

    # Question group
    group = QuestionGroup(
        title="أسئلة الموسم الأول",
        status=QuestionStatus.ACTIVE,
        competition_id=SEED_COMPETITION_ID,
    )
    session.add(group)
    await session.flush()

    questions_data = [
        {
            "prompt": "ما هو أكبر محيط في العالم؟",
            "type": QuestionType.MULTIPLE_CHOICE,
            "options": {"A": "المحيط الأطلسي", "B": "المحيط الهندي", "C": "المحيط الهادئ", "D": "المحيط المتجمد"},
            "correct": "C",
            "score": 100,
            "difficulty": QuestionDifficulty.EASY,
        },
        {
            "prompt": "كم عدد أيام السنة الكبيسة؟",
            "type": QuestionType.MULTIPLE_CHOICE,
            "options": {"A": "364", "B": "365", "C": "366", "D": "367"},
            "correct": "C",
            "score": 100,
            "difficulty": QuestionDifficulty.EASY,
        },
        {
            "prompt": "ما عاصمة المملكة العربية السعودية؟",
            "type": QuestionType.MULTIPLE_CHOICE,
            "options": {"A": "جدة", "B": "الرياض", "C": "مكة", "D": "الدمام"},
            "correct": "B",
            "score": 150,
            "difficulty": QuestionDifficulty.MEDIUM,
        },
        {
            "prompt": "الأرض هي أقرب كوكب إلى الشمس.",
            "type": QuestionType.TRUE_FALSE,
            "options": {"A": "صح", "B": "خطأ"},
            "correct": "B",
            "score": 150,
            "difficulty": QuestionDifficulty.MEDIUM,
        },
        {
            "prompt": "في أي عام أُسِّست الأمم المتحدة؟",
            "type": QuestionType.MULTIPLE_CHOICE,
            "options": {"A": "1945", "B": "1948", "C": "1950", "D": "1939"},
            "correct": "A",
            "score": 200,
            "difficulty": QuestionDifficulty.HARD,
        },
    ]

    # Create quiz session
    quiz_session = QuizSession(
        competition_id=SEED_COMPETITION_ID,
        season_id=SEED_SEASON_ID,
        cycle_id=SEED_CYCLE_ID,
        session_type=SessionType.TIMED_WINDOW,
        title="جلسة الأسئلة — الموسم الأول",
        status=SessionStatus.OPEN,
        answer_duration_seconds=30,
        source_group_id=group.id,
        scoring_rules={},
        visibility_rules={},
        created_by=SEED_ACCOUNT_ID,
    )
    session.add(quiz_session)
    await session.flush()

    for order, qdata in enumerate(questions_data):
        q = Question(
            group_id=group.id,
            question_type=qdata["type"],
            prompt=qdata["prompt"],
            options=qdata["options"],
            correct_answer={"answer": qdata["correct"]},
            score_value=qdata["score"],
            difficulty=qdata["difficulty"],
            status=QuestionStatus.ACTIVE,
            display_order=order,
        )
        session.add(q)
        await session.flush()

        sq = SessionQuestion(
            session_id=quiz_session.id,
            question_id=q.id,
            delivery_order=order,
            effective_score_value=qdata["score"],
            effective_prompt_snapshot=qdata["prompt"],
            effective_options_snapshot=qdata["options"],
        )
        session.add(sq)

    await session.commit()
```

---

## Task 10: Register All Routers + Seeder in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] Update `main.py` to import and register all new routers, and run seed on startup:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.core.database import async_session, check_db_connection, engine
from app.core.models import Base, GameInfo
from app.core.seed import seed

from app.modules.auth.router import router as auth_router
from app.modules.competitions.router import router as competitions_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.store.router import router as store_router
from app.modules.quiz.router import router as quiz_router
from app.modules.notifications.router import router as notifications_router
from app.modules.attacks.router import router as attacks_router
from app.modules.leaderboard.router import router as leaderboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Seed game_info
        result = await session.execute(select(GameInfo))
        if not result.scalars().first():
            session.add(GameInfo(
                title="حرب الأسماء",
                subtitle="من سيكشف الأقنعة أولاً؟",
                current_season="الموسم الأول",
                status="active",
                announcement="مرحباً! الموسم الأول بدأ — انضم الآن برمز WAR2026",
            ))
            await session.commit()

        # Run seeder
        await seed(session)

    yield
    await engine.dispose()


app = FastAPI(
    title="War of Names API",
    description="حرب الأسماء — Seasonal alias-based competition platform",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(competitions_router)
app.include_router(dashboard_router)
app.include_router(store_router)
app.include_router(quiz_router)
app.include_router(notifications_router)
app.include_router(attacks_router)
app.include_router(leaderboard_router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health/db")
async def health_db():
    connected = await check_db_connection()
    if connected:
        return {"status": "ok", "database": "connected"}
    return JSONResponse(status_code=503, content={"status": "error", "database": "unreachable"})


@app.get("/api/game-info")
async def get_game_info():
    async with async_session() as session:
        result = await session.execute(select(GameInfo).limit(1))
        info = result.scalars().first()
    if not info:
        return JSONResponse(status_code=404, content={"success": False, "message": "not found"})
    return {
        "success": True,
        "data": {
            "title": info.title,
            "subtitle": info.subtitle,
            "current_season": info.current_season,
            "status": info.status,
            "announcement": info.announcement,
        },
    }
```

---

## Task 11: Frontend — Auth Context + Token Management

**Files:**
- Create: `frontend/src/context/AuthContext.jsx`
- Create: `frontend/src/hooks/useAuth.js`

- [ ] Create `frontend/src/context/AuthContext.jsx`:

```jsx
/**
 * AuthContext — global auth state.
 *
 * Stores JWT token in localStorage.
 * Provides: currentUser, token, login(tokenData), logout(), loading
 *
 * currentUser shape: { account_id, username, real_name }
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react'

export const AuthContext = createContext(null)

const TOKEN_KEY = 'won_token'
const USER_KEY = 'won_user'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem(USER_KEY)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(false)

  const login = useCallback((tokenData) => {
    // tokenData: { token, account_id, username, real_name }
    localStorage.setItem(TOKEN_KEY, tokenData.token)
    localStorage.setItem(USER_KEY, JSON.stringify({
      account_id: tokenData.account_id,
      username: tokenData.username,
      real_name: tokenData.real_name,
    }))
    setToken(tokenData.token)
    setCurrentUser({
      account_id: tokenData.account_id,
      username: tokenData.username,
      real_name: tokenData.real_name,
    })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setCurrentUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, currentUser, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuthContext must be used inside AuthProvider')
  return ctx
}
```

- [ ] Create `frontend/src/hooks/useAuth.js`:

```js
/**
 * Convenience hook — wraps AuthContext.
 * Returns { token, currentUser, login, logout, loading, isAuthenticated }
 */
import { useAuthContext } from '../context/AuthContext'

export default function useAuth() {
  const ctx = useAuthContext()
  return {
    ...ctx,
    isAuthenticated: !!ctx.token,
  }
}
```

---

## Task 12: Frontend — Authenticated API Helper

**Files:**
- Create: `frontend/src/lib/api.js`

- [ ] Create a simple fetch wrapper that injects the Bearer token:

```js
/**
 * Authenticated fetch wrapper.
 * Reads token from localStorage and injects Authorization header.
 * Throws on non-2xx responses with the backend's error detail.
 */

const TOKEN_KEY = 'won_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export async function apiFetch(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const res = await fetch(path, { ...options, headers })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const err = await res.json()
      detail = err.detail || err.message || detail
    } catch {}
    throw new Error(detail)
  }

  return res.json()
}
```

---

## Task 13: Frontend — Protected Route + Login Page

**Files:**
- Create: `frontend/src/components/ProtectedRoute.jsx`
- Create: `frontend/src/pages/LoginPage.jsx`

- [ ] Create `frontend/src/components/ProtectedRoute.jsx`:

```jsx
import { Navigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}
```

- [ ] Create `frontend/src/pages/LoginPage.jsx`:

```jsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import { apiFetch } from '../lib/api'
import AuthLayout from '../components/AuthLayout'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const json = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      login(json.data)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <div className="w-full max-w-md">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-3xl shadow-xl p-8 md:p-10">
          <h1 className="font-display text-3xl font-black text-gray-800 dark:text-white mb-2">تسجيل الدخول</h1>
          <p className="text-gray-500 dark:text-gray-400 font-medium mb-8">ادخل إلى ساحة المعركة</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300">اسم المستخدم</label>
              <input
                type="text"
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                placeholder="warrior_2024"
                required
                className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3.5 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal smooth-transition text-gray-800 dark:text-white"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300">كلمة المرور</label>
              <input
                type="password"
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                placeholder="••••••••"
                required
                className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3.5 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal smooth-transition text-gray-800 dark:text-white"
              />
            </div>

            {error && (
              <p className="text-brand-danger text-sm font-bold text-center py-2 bg-red-50 dark:bg-red-900/10 rounded-xl">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-press w-full bg-brand-teal hover:bg-brand-teal-hover text-white py-4 rounded-xl font-heading font-black text-lg shadow-lg shadow-brand-teal/20 smooth-transition flex items-center justify-center gap-3 disabled:opacity-60"
            >
              {loading ? (
                <><iconify-icon icon="lucide:loader-2" class="text-xl animate-spin"></iconify-icon> جارٍ الدخول...</>
              ) : (
                <><iconify-icon icon="lucide:log-in" class="text-xl"></iconify-icon> دخول</>
              )}
            </button>

            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              ليس لديك حساب؟{' '}
              <Link to="/register" className="text-brand-teal dark:text-brand-slate font-bold hover:underline">سجل الآن</Link>
            </p>
          </form>
        </div>
      </div>
    </AuthLayout>
  )
}
```

---

## Task 14: Wire RegisterPage + JoinPage to Real API

**Files:**
- Modify: `frontend/src/pages/RegisterPage.jsx`
- Modify: `frontend/src/pages/JoinPage.jsx`

- [ ] Rewrite `RegisterPage.jsx` to submit to `/api/auth/register`:

The key change: convert the `<Link>` submit button to a real `<form onSubmit>` that calls `POST /api/auth/register`, stores the token via `login()`, then navigates to `/join`.

Key structural changes:
- Import `useState`, `useNavigate`, `useAuth`, `apiFetch`
- Add `value` + `onChange` to all inputs (controlled)
- Replace `<Link to="/join">` button with `<button type="submit">`
- On success: call `login(json.data)` then `navigate('/join')`
- Show error if any

- [ ] Rewrite `JoinPage.jsx` to submit to `/api/competitions/{id}/join`:

The key change: the form must POST with `{ invite_code, alias }` to the seeded competition. The competition_id is resolved from `useCompetitionContext` — but since the user may not have a membership yet, we can hardcode the seed competition ID in the join call (or fetch it from a public `/api/competitions/active` endpoint).

Simplest approach: create `GET /api/competitions/active` that returns the first active competition (public, no auth) and use that ID for the join call. After joining, call `useCompetitionContext` to refresh.

---

## Task 15: Wire All Frontend Hooks to Use Auth

**Files:**
- Modify: `frontend/src/hooks/useCompetitionContext.js`
- Modify: `frontend/src/hooks/useLeaderboard.js`
- Modify: `frontend/src/hooks/usePlayerProfile.js`
- Modify: `frontend/src/hooks/useMemberIdentities.js`
- Modify: `frontend/src/hooks/useAttackPreview.js`
- Modify: `frontend/src/hooks/useAttackExecute.js`
- Create: `frontend/src/hooks/useDashboard.js`
- Create: `frontend/src/hooks/useNotifications.js`
- Create: `frontend/src/hooks/useStore.js`
- Create: `frontend/src/hooks/useInventory.js`
- Create: `frontend/src/hooks/useQuizSession.js`

Replace all raw `fetch()` calls with `apiFetch()` from `../lib/api` so the Bearer token is automatically injected.

Fix `useCompetitionContext` to call `/api/me/competition-context` (the real endpoint).

---

## Task 16: Wire DashboardPage to Real Data

**Files:**
- Create: `frontend/src/hooks/useDashboard.js`
- Modify: `frontend/src/pages/DashboardPage.jsx`

- [ ] Create `useDashboard.js`:
```js
import { useState, useEffect } from 'react'
import { apiFetch } from '../lib/api'

export default function useDashboard() {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  useEffect(() => {
    apiFetch('/api/me/dashboard')
      .then(json => setState({ data: json.data, loading: false, error: null }))
      .catch(err => setState({ data: null, loading: false, error: err.message }))
  }, [])
  return state
}
```

- [ ] Update `DashboardPage.jsx` to use `useDashboard()` and display real values:
  - Replace hardcoded `"المحارب الذهبي"` with `data.alias`
  - Replace `"8,450 نقطة"` with `data.balance`
  - Replace `"المركز 14"` with `data.rank`
  - Replace `124`, `68%`, `42`, `12` with `data.attacks_sent`, `data.win_rate`, `data.attacks_defended`, `data.attacks_received`

---

## Task 17: Wire StorePage to Real Data

**Files:**
- Create: `frontend/src/hooks/useStore.js`
- Create: `frontend/src/hooks/useInventory.js`
- Modify: `frontend/src/pages/StorePage.jsx`

Wire StorePage to fetch from `/api/competitions/{id}/store` and display real items. Purchase button calls `POST .../store/purchase`.

---

## Task 18: Wire QuizPage to Real Data

**Files:**
- Create: `frontend/src/hooks/useQuizSession.js`
- Modify: `frontend/src/pages/QuizPage.jsx`

Wire QuizPage to fetch from `/api/competitions/{id}/quiz/session` and submit answers via `POST /api/quiz/sessions/{id}/answer`.

---

## Task 19: Wire AppLayout to Real User Data + Logout

**Files:**
- Modify: `frontend/src/components/AppLayout.jsx`

Replace hardcoded `"المحارب الذهبي"` and `"8,450 نقطة"` in the header with data from `useCompetitionContext`. Add a logout button.

---

## Task 20: Update App.jsx — Routes + Auth

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] Wrap everything in `<AuthProvider>`, add `/login` route, wrap game routes in `<ProtectedRoute>`.

---

## Task 21: Rebuild Docker + Verify

- [ ] Rebuild API container (new packages):
```bash
docker compose build --no-cache api && docker compose up -d
```

- [ ] Verify DB tables created:
```bash
docker exec warofnames-db-1 psql -U postgres -d war_of_names -c "\dt"
```

- [ ] Test auth:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","real_name":"اختبار","password":"test123"}'
```

- [ ] Test join:
```bash
curl -X POST http://localhost:8000/api/competitions/00000000-0000-0000-0000-000000000001/join \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"invite_code":"WAR2026","alias":"المحارب الخفي"}'
```

- [ ] Visit `http://localhost:5173/register` in browser, register, verify redirect to `/join`
- [ ] Join with code `WAR2026`, verify redirect to `/dashboard` with real balance showing
- [ ] Visit `/leaderboard` — verify real player rows appear
- [ ] Visit `/store` — verify 5 seeded items appear
- [ ] Purchase an item — verify balance deducted
- [ ] Visit `/quiz` — verify 5 questions appear
- [ ] Answer a question correctly — verify balance increases

---

## Acceptance Checklist

- [ ] `POST /api/auth/register` creates a real Account row in DB
- [ ] `POST /api/auth/login` returns a valid JWT token
- [ ] `GET /api/auth/me` returns real account data when authenticated
- [ ] `POST /api/competitions/{id}/join` creates a Membership + LedgerEntry
- [ ] `GET /api/me/competition-context` returns membership with real balance
- [ ] `GET /api/me/dashboard` returns real attack stats + rank
- [ ] `GET /api/competitions/{id}/leaderboard` returns real ranked members
- [ ] `POST /api/competitions/{id}/attacks/preview` works with real user context
- [ ] `POST /api/competitions/{id}/attacks/execute` writes real LedgerEntry rows
- [ ] `GET /api/competitions/{id}/store` returns 5 seeded items
- [ ] `POST /api/competitions/{id}/store/purchase` creates OwnedItem + LedgerEntry
- [ ] `GET /api/me/inventory` returns purchased items
- [ ] `GET /api/competitions/{id}/quiz/session` returns 5 seeded questions
- [ ] `POST /api/quiz/sessions/{id}/answer` evaluates and awards points
- [ ] `GET /api/me/notifications` returns notifications array
- [ ] `/register` page submits real form and creates account
- [ ] `/join` page submits real form and creates membership
- [ ] `/dashboard` shows real alias, balance, rank, attack stats
- [ ] `/leaderboard` shows real DB players (not hardcoded)
- [ ] `/store` shows real DB items (not hardcoded)
- [ ] `/quiz` shows real DB questions (not hardcoded)
- [ ] AppLayout header shows real user alias + balance
- [ ] Logout clears token and redirects to `/login`
- [ ] Protected routes redirect to `/login` when unauthenticated
- [ ] No hardcoded numbers remain on any wired page
