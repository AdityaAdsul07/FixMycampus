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


# ---------------- REQUEST MODELS ----------------

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
    version="1.1.0",
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
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------- CREATE ISSUE ----------------

@app.post("/api/issues", response_model=IssueOut, status_code=201)
def create_issue(
    payload: IssueCreate,
    db: Session = Depends(get_db)
):
    issue = Issue(
        tracking_id=f"FMC-{uuid4().hex[:8].upper()}",
        title=payload.title.strip(),
        description=payload.description.strip(),
        category=payload.category.strip(),
        location=payload.location.strip(),
        reporter_name=payload.reporter_name.strip(),
        priority=payload.priority,
        status=IssueStatus.SUBMITTED.value,
    )

    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


# ---------------- VIEW ALL ISSUES ----------------

@app.get("/api/issues", response_model=list[IssueOut])
def list_issues(db: Session = Depends(get_db)):
    statement = select(Issue).order_by(Issue.id.desc())
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
