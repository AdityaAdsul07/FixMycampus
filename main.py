
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, select, String, Text, Integer, DateTime
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
)

# ---------------- DATABASE ----------------

engine = create_engine(
    "sqlite:///./fixmycampus.db",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


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


# ---------------- REQUEST MODELS ----------------

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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------- APPLICATION ----------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="FixMyCampus",
    description="Campus Issue Reporting and Resolution System",
    version="1.0.0",
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
