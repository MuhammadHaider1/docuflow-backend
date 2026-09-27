"""Shared pytest fixtures and test doubles.

The fake session dispatches on the entity named in each SQLAlchemy statement, so
services receive realistic rows and assertions can check real application
behaviour instead of MagicMock truthiness.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, NamedTuple

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


from src.core.database import get_db
from src.core.security import get_password_hash, is_authenticated
from src.main import app
from src.models.comment import Comment
from src.models.document import Document
from src.models.organization import Membership
from src.models.auth import User
from src.models.rbac import Permission, Role

ALL_PERMISSIONS = (
    "document:create",
    "document:read",
    "document:update",
    "document:delete",
    "folder:create",
    "members:invite",
    "members:manage_roles",
    "members:remove",
    "organization:read",
    "organization:update",
    "organization:manage",
)

LOGIN_PASSWORD = "StrongPassword123!"


class PermissionRow(NamedTuple):
    """Row shape that ``PermissionChecker`` reads out of ``result.all()``."""

    name: str
    role_name: str


class _ScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = list(items)

    def all(self) -> list[Any]:
        return list(self._items)

    def first(self) -> Any | None:
        return self._items[0] if self._items else None

    def one_or_none(self) -> Any | None:
        return self._items[0] if self._items else None


class FakeResult:
    def __init__(
        self,
        *,
        rows: list[Any] | None = None,
        scalars: list[Any] | None = None,
        rowcount: int = 0,
    ) -> None:
        self._rows = list(rows or [])
        self._scalars = list(scalars or [])
        self.rowcount = rowcount

    def all(self) -> list[Any]:
        return list(self._rows)

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._scalars)

    def scalar(self) -> Any | None:
        return self._scalars[0] if self._scalars else None

    def scalar_one(self) -> Any | None:
        return self._scalars[0] if self._scalars else None

    def scalar_one_or_none(self) -> Any | None:
        return self._scalars[0] if self._scalars else None


def _make_user(email: str, full_name: str, hashed_password: str) -> User:
    """A real (transient) ``User`` row so relationship assignment behaves normally."""
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
    )
    return user


class FakeSession:
    """Statement-dispatching stand-in for ``AsyncSession``."""

    def __init__(
        self,
        *,
        user: Any,
        org_id: uuid.UUID,
        role_name: str = "Super Admin",
        permissions: tuple[str, ...] = ALL_PERMISSIONS,
        is_member: bool = True,
        membership: Membership | None = None,
        users: list[User] | None = None,
        documents: list[Any] | None = None,
        notifications: list[Any] | None = None,
        comments: list[Any] | None = None,
        audit_logs: list[Any] | None = None,
    ) -> None:
        self.user = user
        self.users = list(users) if users is not None else [user]
        self.org_id = org_id
        self.role_name = role_name
        self.permissions = tuple(permissions)
        self.is_member = is_member
        self.role = Role(id=uuid.uuid4(), name=role_name, description=role_name)
        self.membership = membership or Membership(
            id=uuid.uuid4(),
            user_id=user.id,
            organization_id=org_id,
            role_id=self.role.id,
        )
        self.documents = list(documents or [])
        self.notifications = list(notifications or [])
        self.comments = list(comments or [])
        self.audit_logs = list(audit_logs or [])
        self.added: list[Any] = []
        self.commits = 0

    @staticmethod
    def _entities(stmt: Any) -> list[str]:
        return [
            d.get("name") for d in getattr(stmt, "column_descriptions", []) or []
        ]

    async def execute(self, stmt: Any) -> FakeResult:
        # UPDATE ... RETURNING notification, as used by mark_as_read
        if type(stmt).__name__.startswith("Update"):
            return self._apply_notification_update(stmt)

        names = self._entities(stmt)

        # PermissionChecker: select(Permission.name, Role.name.label("role_name"))
        if "role_name" in names:
            if not self.is_member:
                return FakeResult(rows=[])
            # Mirrors the LEFT OUTER JOIN in PermissionChecker: a member with no
            # permissions still yields one row whose permission name is NULL.
            rows = [PermissionRow(p, self.role_name) for p in self.permissions]
            if not rows:
                rows = [PermissionRow(None, self.role_name)]
            return FakeResult(rows=rows)

        if any("count" in str(n).lower() for n in names if n):
            return FakeResult(scalars=[len(self.documents)])

        if names == ["User"]:
            return FakeResult(scalars=self._match_users(stmt))
        if names == ["Role"]:
            return FakeResult(scalars=[self.role])
        if names == ["Permission"]:
            return FakeResult(
                scalars=[Permission(id=uuid.uuid4(), name=n) for n in self.permissions]
            )
        if names == ["Membership"]:
            return FakeResult(scalars=[self.membership])
        if names == ["Notification"]:
            return FakeResult(scalars=list(self.notifications))
        if names == ["Comment"]:
            return FakeResult(scalars=list(self.comments))
        if names == ["AuditLog"]:
            return FakeResult(scalars=list(self.audit_logs))
        if names == ["Document"]:
            return FakeResult(scalars=list(self.documents))

        return FakeResult()

    def _apply_notification_update(self, stmt: Any) -> FakeResult:
        """Mimic ``UPDATE notification ... WHERE id=.. AND user_id=.. RETURNING *``."""
        try:
            bound: dict[str, Any] = dict(stmt.compile().params)
        except Exception:  # pragma: no cover - non-compilable statement
            return FakeResult(rowcount=0)

        # Everything that is not part of the WHERE clause is a SET value.
        params = {
            key: value
            for key, value in bound.items()
            if not key.startswith(("id_", "user_id_"))
        }

        target_id = next(
            (v for k, v in bound.items() if k.startswith("id")), None
        )
        target_user = next(
            (v for k, v in bound.items() if k.startswith("user_id")), None
        )
        for note in self.notifications:
            if target_id is not None and note.id != target_id:
                continue
            if target_user is not None and note.user_id != target_user:
                continue
            for field, value in params.items():
                setattr(note, field, value)
            return FakeResult(scalars=[note], rowcount=1)
        return FakeResult(rowcount=0)

    def _match_users(self, stmt: Any) -> list[User]:
        """Honour ``WHERE email = ...`` / ``WHERE id = ...`` the way Postgres would."""
        try:
            params = stmt.compile().params
        except Exception:  # pragma: no cover - non-compilable statement
            return list(self.users)

        for key, value in params.items():
            if key.startswith("email"):
                return [u for u in self.users if u.email == value]
            if key.startswith("id"):
                return [u for u in self.users if u.id == value]
        return list(self.users)

    @staticmethod
    def _backfill(instance: Any) -> None:
        """Supply the column defaults the database would normally populate."""
        now = datetime.now(timezone.utc)
        if getattr(instance, "id", None) is None:
            instance.id = uuid.uuid4()
        if hasattr(instance, "created_at") and getattr(instance, "created_at", None) is None:
            instance.created_at = now
        if hasattr(instance, "updated_at") and getattr(instance, "updated_at", None) is None:
            instance.updated_at = now
        if getattr(instance, "is_active", None) is None:
            instance.is_active = True
        if getattr(instance, "is_superuser", None) is None:
            instance.is_superuser = False

    def add(self, instance: Any) -> None:
        if getattr(instance, "id", None) is None:
            instance.id = uuid.uuid4()
        if getattr(instance, "is_active", None) is None:
            instance.is_active = True
        if getattr(instance, "is_superuser", None) is None:
            instance.is_superuser = False
        self._backfill(instance)
        # Newly created comments become visible to later reads, mirroring a commit.
        if isinstance(instance, User) and instance not in self.users:
            self.users.append(instance)
        if isinstance(instance, Comment) and instance not in self.comments:
            # Timestamps and the eager-loaded author are normally supplied by the
            # database and by selectinload; set them so response validation passes.
            if getattr(instance, "user", None) is None:
                instance.user = self.user
            self.comments.append(instance)
        self.added.append(instance)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def refresh(self, instance: Any, *args: Any, **kwargs: Any) -> None:
        return None

    async def delete(self, instance: Any) -> None:
        return None


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Har test ke baad dependency overrides ko safely clear karein."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def install_session():
    """Return a helper that swaps the mocked session for the current test."""

    def _install(session: FakeSession) -> FakeSession:
        app.dependency_overrides[get_db] = lambda: session
        return session

    return _install


@pytest.fixture
def org_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth_user() -> User:
    return _make_user(
        "testuser@example.com", "Test User", get_password_hash(LOGIN_PASSWORD)
    )


@pytest.fixture
def login_user() -> User:
    return _make_user(
        "loginuser@example.com", "Login User", get_password_hash(LOGIN_PASSWORD)
    )


@pytest.fixture
def sample_document(org_id: uuid.UUID, auth_user: User) -> Document:
    """A document owned by ``org_id``, i.e. visible to the default member."""
    document = Document(
        id=uuid.uuid4(),
        title="Architecture Decision Record",
        description="Why we chose pgvector",
        organization_id=org_id,
        owner_id=auth_user.id,
        processing_status="completed",
        is_archived=False,
        extracted_content="We evaluated FAISS and pgvector.",
    )
    FakeSession._backfill(document)
    return document


@pytest.fixture
def foreign_document(auth_user: User) -> Document:
    """A document owned by a *different* tenant, used to prove isolation."""
    document = Document(
        id=uuid.uuid4(),
        title="Other tenant document",
        organization_id=uuid.uuid4(),
        owner_id=auth_user.id,
        processing_status="completed",
        is_archived=False,
    )
    FakeSession._backfill(document)
    return document


@pytest.fixture
def db_session(
    auth_user: User, org_id: uuid.UUID, sample_document: Document
) -> FakeSession:
    return FakeSession(user=auth_user, org_id=org_id, documents=[sample_document])


@pytest.fixture
def empty_db_session(auth_user: User, org_id: uuid.UUID) -> FakeSession:
    """Session whose tenant owns no documents at all."""
    return FakeSession(user=auth_user, org_id=org_id)


@pytest.fixture
def vacant_db_session(auth_user: User, org_id: uuid.UUID) -> FakeSession:
    """Session in which the email being registered is not taken yet."""
    return FakeSession(user=auth_user, org_id=org_id, users=[])


@pytest.fixture
def login_db_session(login_user: User, org_id: uuid.UUID) -> FakeSession:
    """Session whose only user is the one ``test_auth`` registers before logging in."""
    return FakeSession(user=login_user, org_id=org_id)


@pytest.fixture
def viewer_db_session(auth_user: User, org_id: uuid.UUID) -> FakeSession:
    """A member whose role lacks the permission under test."""
    return FakeSession(
        user=auth_user, org_id=org_id, role_name="Viewer", permissions=()
    )


def _client(db: Any, headers: dict[str, str] | None = None) -> AsyncClient:
    if hasattr(app, "dependency_overrides"):
        app.dependency_overrides[get_db] = lambda: db
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=headers or {},
    )


@pytest_asyncio.fixture
async def client(login_db_session: FakeSession) -> AsyncClient:
    """Unauthenticated client with a mocked DB session."""
    async with _client(login_db_session) as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(db_session: FakeSession, org_id: uuid.UUID) -> AsyncClient:
    """Authenticated client whose membership satisfies every permission check.

    ``FakeSession`` reports the member's role as ``Super Admin``, which the real
    ``PermissionChecker`` short-circuits, so the actual permission logic runs
    here.  Do not bypass it by patching ``PermissionChecker.__call__``: FastAPI
    resolves the sub-dependency signature lazily and would then expose the
    wrapper's ``*args``/``**kwargs`` as required query parameters.
    """
    app.dependency_overrides[is_authenticated] = lambda: db_session.user
    async with _client(
        db_session, headers={"X-Organization-Id": str(org_id)}
    ) as ac:
        yield ac
