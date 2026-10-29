"""FixMyCampus - Campus issue reporting & resolution API (FastAPI + SQLAlchemy + SQLite)."""
import os
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from datetime import timedelta
from enum import Enum
from pathlib import Path
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, func, select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

BASE_DIR = Path(__file__).resolve().parent


def utcnow() -> datetime:
    """Current UTC time as a naive datetime (SQLite stores naive values)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------- SECURITY CONFIGURATION ----------------

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").strip().lower()


def load_jwt_secret() -> str:
    """Use JWT_SECRET from the environment.
    In production mode, a secret of at least 32 characters is strictly required.
    In development mode, a secure 64-hex-character secret is generated and stored locally."""
    from_env = os.environ.get("JWT_SECRET", "").strip()
    if from_env:
        if len(from_env) < 32 and ENVIRONMENT == "production":
            raise RuntimeError("JWT_SECRET must be at least 32 characters long in production mode.")
        return from_env

    if ENVIRONMENT == "production":
        raise RuntimeError(
            "JWT_SECRET environment variable is missing. "
            "A secure secret (minimum 32 characters) must be configured in production mode."
        )

    secret_file = BASE_DIR / ".jwt_secret"
    if secret_file.exists():
        secret = secret_file.read_text().strip()
        if len(secret) >= 32:
            return secret

    secret = secrets.token_hex(32)  # 64 hex characters (256 bits)
    try:
        secret_file.write_text(secret)
    except Exception:
        pass
    return secret


JWT_SECRET = load_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security_bearer = HTTPBearer(auto_error=False)

# Simple in-memory brute-force protection for /login: 5 failures per 5 minutes.
MAX_LOGIN_FAILURES = 5
LOGIN_WINDOW_SECONDS = 300
FAILED_LOGINS: dict[str, deque] = defaultdict(deque)


def _prune(key: str) -> deque:
    attempts = FAILED_LOGINS[key]
    cutoff = time.monotonic() - LOGIN_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: int, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


# ---------------- DATABASE ----------------

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'fixmycampus.db'}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"


STAFF_ROLES = (UserRole.STAFF.value, UserRole.ADMIN.value)


class IssueStatus(str, Enum):
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REJECTED = "Rejected"


CLOSED_STATUSES = (
    IssueStatus.RESOLVED.value, IssueStatus.CLOSED.value, IssueStatus.REJECTED.value,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.STUDENT.value)
    department: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracking_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    location: Mapped[str] = mapped_column(String(120))
    reporter_name: Mapped[str] = mapped_column(String(80))
    priority: Mapped[str] = mapped_column(String(20), default="Normal")
    status: Mapped[str] = mapped_column(String(30), default="Submitted")
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_to_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_staff_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class IssueEvent(Base):
    """One entry in an issue's activity timeline (created, status change, assignment)."""
    __tablename__ = "issue_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    actor: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def upgrade_db_schema():
    """Create missing tables and add columns that older databases don't have yet."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        columns = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(issues)").fetchall()]
        if "user_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE issues ADD COLUMN user_id INTEGER DEFAULT NULL")
        if "assigned_to_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE issues ADD COLUMN assigned_to_id INTEGER DEFAULT NULL")
        if "assigned_staff_name" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE issues ADD COLUMN assigned_staff_name VARCHAR(100) DEFAULT NULL"
            )
        if "resolution_notes" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE issues ADD COLUMN resolution_notes VARCHAR(500) DEFAULT NULL"
            )


ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@fixmycampus.edu").strip().lower()


def seed_default_admin():
    """Create the initial admin user safely.
    In production mode, ADMIN_PASSWORD is required.
    In development mode, a secure password is generated and displayed on first run."""
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.role == UserRole.ADMIN.value)) is not None:
            return
        password = os.environ.get("ADMIN_PASSWORD")
        if ENVIRONMENT == "production" and not password:
            raise RuntimeError("ADMIN_PASSWORD environment variable must be set in production mode.")
        generated = password is None
        if generated:
            password = secrets.token_urlsafe(12)
        else:
            if len(password) < 8 or not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
                raise ValueError("ADMIN_PASSWORD must be at least 8 characters long and contain both letters and numbers.")
        db.add(User(
            email=ADMIN_EMAIL,
            full_name="Campus Administrator",
            hashed_password=hash_password(password),
            role=UserRole.ADMIN.value,
            department="Campus Administration",
        ))
        db.commit()
    if generated:
        print("=" * 60)
        print(f" First-run admin created:  {ADMIN_EMAIL}")
        print(f" Generated password:       {password}")
        print(" (shown once - set ADMIN_PASSWORD to choose your own)")
        print("=" * 60)


# ---------------- AUTH DEPENDENCIES ----------------

def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_from_credentials(credentials: HTTPAuthorizationCredentials | None, db: Session):
    if not credentials or not credentials.credentials:
        return None, "Authentication required. Please log in."
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None, "Invalid or expired token. Please log in again."
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None, "Malformed authentication token."
    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        return None, "User account not found or disabled."
    return user, None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> User:
    user, error = _user_from_credentials(credentials, db)
    if user is None:
        raise _unauthorized(error)
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    user, _ = _user_from_credentials(credentials, db)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied: Administrator privileges required.")
    return user


def require_staff_or_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in STAFF_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied: Staff or Administrator privileges required.")
    return user


# ---------------- REQUEST / RESPONSE SCHEMAS ----------------

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _strip_strings(value):
    return value.strip() if isinstance(value, str) else value


def _check_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_PATTERN.match(value):
        raise ValueError("Enter a valid email address.")
    return value


def _check_password(value: str) -> str:
    if not (re.search(r"[A-Za-z]", value) and re.search(r"\d", value)):
        raise ValueError("Password must contain at least one letter and one number.")
    return value


def iso_utc(value: datetime) -> str:
    """Serialise naive UTC datetimes with a 'Z' so browsers convert them to local time."""
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", check_fields=False)
    def _serialize_dates(self, value: datetime):
        return iso_utc(value)


class UserRegister(BaseModel):
    """Public sign-up. Always creates a student - the role can't be chosen by the caller."""
    email: str = Field(min_length=5, max_length=120)
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    department: str | None = Field(default=None, max_length=60)

    _strip = field_validator("email", "full_name", "department", mode="before")(_strip_strings)
    _email = field_validator("email")(_check_email)
    _password = field_validator("password")(_check_password)


class StaffCreate(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    department: str | None = Field(default=None, max_length=60)

    _strip = field_validator("email", "full_name", "department", mode="before")(_strip_strings)
    _email = field_validator("email")(_check_email)
    _password = field_validator("password")(_check_password)


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: str
    department: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class IssueCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=10, max_length=3000)
    category: str = Field(min_length=2, max_length=40)
    location: str = Field(min_length=2, max_length=120)
    reporter_name: str = Field(min_length=2, max_length=80)
    priority: str = Field(default="Normal", pattern="^(Low|Normal|High|Urgent)$")

    _strip = field_validator(
        "title", "description", "category", "location", "reporter_name", mode="before"
    )(_strip_strings)


class StatusUpdate(BaseModel):
    status: IssueStatus
    note: str | None = Field(default=None, max_length=300)
    assigned_staff_name: str | None = Field(default=None, max_length=100)
    resolution_notes: str | None = Field(default=None, max_length=500)

    _strip = field_validator("note", "assigned_staff_name", "resolution_notes", mode="before")(_strip_strings)


class IssueAssign(BaseModel):
    assigned_to_id: int
    note: str | None = Field(default=None, max_length=300)

    _strip = field_validator("note", mode="before")(_strip_strings)


class IssueOut(ORMModel):
    id: int
    tracking_id: str
    title: str
    description: str
    category: str
    location: str
    reporter_name: str
    priority: str
    status: str
    user_id: int | None = None
    assigned_to_id: int | None = None
    assigned_staff_name: str | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class IssueEventOut(ORMModel):
    id: int
    status: str
    note: str | None = None
    actor: str
    created_at: datetime


# ---------------- HELPERS ----------------

def is_staff(user: User | None) -> bool:
    return user is not None and user.role in STAFF_ROLES


def issue_view(issue: Issue, viewer: User | None) -> IssueOut:
    """Staff and the reporter see everything; the public never sees who reported it."""
    data = IssueOut.model_validate(issue)
    if not is_staff(viewer) and not (viewer and issue.user_id == viewer.id):
        data.reporter_name = "Anonymous"
        data.user_id = None
        data.assigned_to_id = None
    return data


def find_issue(db: Session, tracking_id: str) -> Issue:
    issue = db.scalar(select(Issue).where(Issue.tracking_id == tracking_id.strip().upper()))
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    return issue


def add_event(db: Session, issue: Issue, actor: str, note: str | None = None):
    db.add(IssueEvent(issue_id=issue.id, status=issue.status, note=note or None, actor=actor))


# Allowed status progression for campus issues
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    IssueStatus.SUBMITTED.value: {
        IssueStatus.UNDER_REVIEW.value,
        IssueStatus.ASSIGNED.value,
        IssueStatus.IN_PROGRESS.value,
        IssueStatus.RESOLVED.value,
        IssueStatus.REJECTED.value,
    },
    IssueStatus.UNDER_REVIEW.value: {
        IssueStatus.ASSIGNED.value,
        IssueStatus.IN_PROGRESS.value,
        IssueStatus.RESOLVED.value,
        IssueStatus.REJECTED.value,
    },
    IssueStatus.ASSIGNED.value: {
        IssueStatus.IN_PROGRESS.value,
        IssueStatus.UNDER_REVIEW.value,
        IssueStatus.RESOLVED.value,
        IssueStatus.REJECTED.value,
    },
    IssueStatus.IN_PROGRESS.value: {
        IssueStatus.RESOLVED.value,
        IssueStatus.ASSIGNED.value,
        IssueStatus.UNDER_REVIEW.value,
        IssueStatus.REJECTED.value,
    },
    IssueStatus.RESOLVED.value: {
        IssueStatus.CLOSED.value,
        IssueStatus.IN_PROGRESS.value,
    },
    IssueStatus.CLOSED.value: {
        IssueStatus.IN_PROGRESS.value,
    },
    IssueStatus.REJECTED.value: {
        IssueStatus.UNDER_REVIEW.value,
    },
}


# ---------------- APPLICATION ----------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    upgrade_db_schema()
    seed_default_admin()
    yield


app = FastAPI(
    title="FixMyCampus",
    description="Campus Issue Reporting and Resolution System",
    version="2.0.0",
    lifespan=lifespan,
)

# Authentication uses a Bearer token (not cookies), so CORS isn't what protects the API.
# Origins are still restricted by default; override with CORS_ORIGINS="https://a.com,https://b.com".
def get_allowed_origins() -> list[str]:
    origins_env = os.environ.get("CORS_ORIGINS", "").strip()
    if origins_env:
        if origins_env == "*":
            return ["*"]
        return [o.strip() for o in origins_env.split(",") if o.strip()]
    if ENVIRONMENT == "production":
        return []
    # In development, allow all origins by default for seamless local testing
    return ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"app": "FixMyCampus", "message": "Campus issue reporting API is running!",
            "version": app.version, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------- AUTHENTICATION ----------------

@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A user with this email address is already registered.")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.STUDENT.value,
        department=payload.department,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id, user.email, user.role), user=user)


@app.post("/api/auth/login", response_model=TokenResponse)
def login_user(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    limiter_key = f"{request.client.host if request.client else 'unknown'}:{email}"
    if len(_prune(limiter_key)) >= MAX_LOGIN_FAILURES:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again in a few minutes.")

    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.hashed_password):
        FAILED_LOGINS[limiter_key].append(time.monotonic())
        raise _unauthorized("Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled. Please contact the administrator.")

    FAILED_LOGINS.pop(limiter_key, None)
    return TokenResponse(access_token=create_access_token(user.id, user.email, user.role), user=user)


@app.get("/api/auth/me", response_model=UserOut)
def get_current_user_profile(user: User = Depends(get_current_user)):
    return user


# ---------------- STAFF MANAGEMENT (admin only) ----------------

@app.post("/api/admin/staff", response_model=UserOut, status_code=201)
def create_staff_member(payload: StaffCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A user with this email address is already registered.")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.STAFF.value,
        department=payload.department,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/api/staff", response_model=list[UserOut])
def list_staff_members(_: User = Depends(require_staff_or_admin), db: Session = Depends(get_db)):
    statement = select(User).where(User.role.in_(STAFF_ROLES), User.is_active.is_(True)).order_by(User.full_name.asc())
    return db.scalars(statement).all()


# ---------------- ISSUES ----------------

@app.post("/api/issues", response_model=IssueOut, status_code=201)
def create_issue(
    payload: IssueCreate,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    issue = Issue(
        tracking_id=f"FMC-{uuid4().hex[:8].upper()}",
        title=payload.title,
        description=payload.description,
        category=payload.category,
        location=payload.location,
        reporter_name=payload.reporter_name,
        priority=payload.priority,
        status=IssueStatus.SUBMITTED.value,
        user_id=current_user.id if current_user else None,
    )
    db.add(issue)
    db.flush()
    add_event(db, issue, actor="Reporter", note="Issue reported")
    db.commit()
    db.refresh(issue)
    return issue_view(issue, current_user)


@app.get("/api/issues", response_model=list[IssueOut])
def list_issues(
    my_reports: bool = False,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    statement = select(Issue).order_by(Issue.id.desc())
    if my_reports:
        if current_user is None:
            raise _unauthorized("Log in to see your own reports.")
        statement = statement.where(Issue.user_id == current_user.id)
    return [issue_view(i, current_user) for i in db.scalars(statement).all()]


@app.get("/api/issues/{tracking_id}", response_model=IssueOut)
def get_issue(
    tracking_id: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    return issue_view(find_issue(db, tracking_id), current_user)


@app.get("/api/issues/{tracking_id}/history", response_model=list[IssueEventOut])
def get_issue_history(
    tracking_id: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    issue = find_issue(db, tracking_id)
    events = db.scalars(
        select(IssueEvent).where(IssueEvent.issue_id == issue.id).order_by(IssueEvent.id.asc())
    ).all()
    result = [IssueEventOut.model_validate(e) for e in events]
    if not is_staff(current_user):
        for event in result:  # don't expose staff names to the public
            event.actor = "Reporter" if event.actor == "Reporter" else "Campus team"
    return result


@app.patch("/api/issues/{tracking_id}/status", response_model=IssueOut)
def update_status(
    tracking_id: str,
    payload: StatusUpdate,
    actor: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    issue = find_issue(db, tracking_id)
    new_status = payload.status.value
    changed = issue.status != new_status

    if changed:
        allowed = ALLOWED_TRANSITIONS.get(issue.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Cannot transition issue from '{issue.status}' to '{new_status}'. Allowed: {sorted(list(allowed))}",
            )
        issue.status = new_status

    if payload.assigned_staff_name is not None:
        issue.assigned_staff_name = payload.assigned_staff_name

    if payload.resolution_notes is not None:
        issue.resolution_notes = payload.resolution_notes
    elif payload.note and new_status in (IssueStatus.RESOLVED.value, IssueStatus.CLOSED.value, IssueStatus.REJECTED.value):
        issue.resolution_notes = payload.note

    issue.updated_at = utcnow()
    if changed or payload.note or payload.resolution_notes:
        event_note = payload.resolution_notes or payload.note or f"Status changed to {new_status}"
        add_event(db, issue, actor=actor.full_name, note=event_note)

    db.commit()
    db.refresh(issue)
    return issue_view(issue, actor)


@app.patch("/api/issues/{tracking_id}/assign", response_model=IssueOut)
def assign_issue(
    tracking_id: str,
    payload: IssueAssign,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    issue = find_issue(db, tracking_id)
    staff_user = db.scalar(select(User).where(User.id == payload.assigned_to_id))
    if staff_user is None or staff_user.role not in STAFF_ROLES or not staff_user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose an active staff member to assign.")

    issue.assigned_to_id = staff_user.id
    issue.assigned_staff_name = staff_user.full_name
    if issue.status in (IssueStatus.SUBMITTED.value, IssueStatus.UNDER_REVIEW.value):
        issue.status = IssueStatus.ASSIGNED.value
    issue.updated_at = utcnow()
    add_event(db, issue, actor=actor.full_name, note=payload.note or f"Assigned to {staff_user.full_name}")
    db.commit()
    db.refresh(issue)
    return issue_view(issue, actor)


# ---------------- DASHBOARD STATISTICS ----------------

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    all_issues = db.scalars(select(Issue)).all()
    by_status = {s.value: 0 for s in IssueStatus}
    by_priority = defaultdict(int)
    by_category = defaultdict(int)

    for item in all_issues:
        st = item.status or "Submitted"
        matched_status = None
        for s in IssueStatus:
            if s.value.lower() == st.lower() or s.value.lower().replace(" ", "-") == st.lower().replace(" ", "-"):
                matched_status = s.value
                break
        if matched_status:
            by_status[matched_status] = by_status.get(matched_status, 0) + 1
        else:
            by_status[st] = by_status.get(st, 0) + 1

        if item.priority:
            by_priority[item.priority] += 1
        if item.category:
            by_category[item.category] += 1

    total = len(all_issues)
    open_count = sum(c for s, c in by_status.items() if s not in CLOSED_STATUSES)

    return {
        "total": total,
        "open": open_count,
        "submitted": by_status.get(IssueStatus.SUBMITTED.value, 0),
        "under_review": by_status.get(IssueStatus.UNDER_REVIEW.value, 0),
        "assigned": by_status.get(IssueStatus.ASSIGNED.value, 0),
        "in_progress": by_status.get(IssueStatus.IN_PROGRESS.value, 0),
        "resolved": by_status.get(IssueStatus.RESOLVED.value, 0),
        "closed": by_status.get(IssueStatus.CLOSED.value, 0),
        "rejected": by_status.get(IssueStatus.REJECTED.value, 0),
        "by_status": by_status,
        "by_priority": dict(by_priority),
        "by_category": dict(by_category),
    }
