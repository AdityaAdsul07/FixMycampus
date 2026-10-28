import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, select, String, Text, Integer, DateTime, Boolean
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
)

# ---------------- SECURITY CONFIGURATION ----------------

JWT_SECRET = os.environ.get("JWT_SECRET", "fixmycampus-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(user_id: int, email: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


# ---------------- DATABASE ----------------

engine = create_engine(
    "sqlite:///./fixmycampus.db",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.STUDENT.value)
    department: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IssueStatus(str, Enum):
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REJECTED = "Rejected"


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracking_id: Mapped[str] = mapped_column(
        String(20), unique=True, index=True
    )
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def upgrade_db_schema():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info(issues)")
        columns = [row[1] for row in result.fetchall()]
        if "user_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE issues ADD COLUMN user_id INTEGER DEFAULT NULL")
        if "assigned_to_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE issues ADD COLUMN assigned_to_id INTEGER DEFAULT NULL")
        if "assigned_staff_name" not in columns:
            conn.exec_driver_sql("ALTER TABLE issues ADD COLUMN assigned_staff_name VARCHAR(100) DEFAULT NULL")


def seed_default_admin():
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN.value))
        if admin is None:
            default_admin = User(
                email="admin@fixmycampus.edu",
                full_name="Campus Administrator",
                hashed_password=hash_password("Admin@123"),
                role=UserRole.ADMIN.value,
                department="Campus Administration"
            )
            db.add(default_admin)
            db.commit()


# ---------------- AUTH DEPENDENCIES ----------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or disabled.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User | None:
    if not credentials or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = int(payload["sub"])
        user = db.scalar(select(User).where(User.id == user_id))
        return user if (user and user.is_active) else None
    except Exception:
        return None


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrator privileges required."
        )
    return user


def require_staff_or_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Staff or Administrator privileges required."
        )
    return user


# ---------------- REQUEST / RESPONSE SCHEMAS ----------------

class UserRegister(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.STUDENT
    department: str | None = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    department: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


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
    priority: str = Field(
        default="Normal",
        pattern="^(Low|Normal|High|Urgent)$"
    )


class StatusUpdate(BaseModel):
    status: IssueStatus
    assigned_staff_name: str | None = None


class IssueAssign(BaseModel):
    assigned_to_id: int | None = None
    assigned_staff_name: str | None = None


class IssueOut(BaseModel):
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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------- APPLICATION ----------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    upgrade_db_schema()
    seed_default_admin()
    yield


app = FastAPI(
    title="FixMyCampus",
    description="Campus Issue Reporting and Resolution System",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "app": "FixMyCampus",
        "message": "Campus issue reporting API is running!",
        "version": "1.2.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------- AUTHENTICATION ENDPOINTS ----------------

@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    clean_email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == clean_email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered."
        )

    user = User(
        email=clean_email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=payload.role.value,
        department=payload.department.strip() if payload.department else None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email, user.role)
    return TokenResponse(access_token=token, token_type="bearer", user=user)


@app.post("/api/auth/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    clean_email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == clean_email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Please contact the administrator."
        )

    token = create_access_token(user.id, user.email, user.role)
    return TokenResponse(access_token=token, token_type="bearer", user=user)


@app.get("/api/auth/me", response_model=UserOut)
def get_current_user_profile(user: User = Depends(get_current_user)):
    return user


@app.get("/api/staff", response_model=list[UserOut])
def list_staff_members(db: Session = Depends(get_db)):
    statement = (
        select(User)
        .where(User.role.in_([UserRole.STAFF.value, UserRole.ADMIN.value]))
        .order_by(User.full_name.asc())
    )
    return db.scalars(statement).all()


# ---------------- CREATE ISSUE ----------------

@app.post("/api/issues", response_model=IssueOut, status_code=201)
def create_issue(
    payload: IssueCreate,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    reporter = payload.reporter_name.strip()
    user_id = None
    if current_user:
        user_id = current_user.id
        if not reporter:
            reporter = current_user.full_name

    issue = Issue(
        tracking_id=f"FMC-{uuid4().hex[:8].upper()}",
        title=payload.title.strip(),
        description=payload.description.strip(),
        category=payload.category.strip(),
        location=payload.location.strip(),
        reporter_name=reporter,
        priority=payload.priority,
        status=IssueStatus.SUBMITTED.value,
        user_id=user_id,
    )

    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


# ---------------- VIEW ALL ISSUES ----------------

@app.get("/api/issues", response_model=list[IssueOut])
def list_issues(
    my_reports: bool = False,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    statement = select(Issue).order_by(Issue.id.desc())
    if my_reports and current_user:
        statement = statement.where(Issue.user_id == current_user.id)
    return db.scalars(statement).all()


# ---------------- TRACK ONE ISSUE ----------------

@app.get("/api/issues/{tracking_id}", response_model=IssueOut)
def get_issue(
    tracking_id: str,
    db: Session = Depends(get_db)
):
    issue = db.scalar(
        select(Issue).where(
            Issue.tracking_id == tracking_id.upper()
        )
    )

    if issue is None:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    return issue


# ---------------- UPDATE ISSUE STATUS ----------------

@app.patch(
    "/api/issues/{tracking_id}/status",
    response_model=IssueOut
)
def update_status(
    tracking_id: str,
    payload: StatusUpdate,
    db: Session = Depends(get_db)
):
    issue = db.scalar(
        select(Issue).where(
            Issue.tracking_id == tracking_id.upper()
        )
    )

    if issue is None:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    issue.status = payload.status.value
    if payload.assigned_staff_name is not None:
        issue.assigned_staff_name = payload.assigned_staff_name
    issue.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(issue)
    return issue


# ---------------- ASSIGN ISSUE TO STAFF ----------------

@app.patch(
    "/api/issues/{tracking_id}/assign",
    response_model=IssueOut
)
def assign_issue(
    tracking_id: str,
    payload: IssueAssign,
    db: Session = Depends(get_db)
):
    issue = db.scalar(
        select(Issue).where(
            Issue.tracking_id == tracking_id.upper()
        )
    )

    if issue is None:
        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    if payload.assigned_to_id is not None:
        staff_user = db.scalar(select(User).where(User.id == payload.assigned_to_id))
        if staff_user:
            issue.assigned_to_id = staff_user.id
            issue.assigned_staff_name = staff_user.full_name
        else:
            issue.assigned_to_id = payload.assigned_to_id
    if payload.assigned_staff_name is not None:
        issue.assigned_staff_name = payload.assigned_staff_name

    if issue.status == IssueStatus.SUBMITTED.value:
        issue.status = IssueStatus.ASSIGNED.value

    issue.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(issue)
    return issue


# ---------------- DASHBOARD STATISTICS ----------------

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    issues = db.scalars(select(Issue)).all()

    counts = {
        status.value: 0 for status in IssueStatus
    }

    for issue in issues:
        counts[issue.status] += 1

    return {
        "total": len(issues),
        "open": sum(
            issue.status not in ("Resolved", "Closed", "Rejected")
            for issue in issues
        ),
        "by_status": counts,
    }
