from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.database import Base
from platform_core.models import new_id, utcnow


class WebsiteDesignSystem(Base):
    __tablename__ = "website_design_systems"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    source_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    tokens: Mapped[dict] = mapped_column(JSON, default=dict)
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    guidelines: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WebsiteSection(Base):
    __tablename__ = "website_sections"
    __table_args__ = (UniqueConstraint("project_id", "section_id", name="uq_website_section_project_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    section_id: Mapped[str] = mapped_column(String(120))
    page: Mapped[str] = mapped_column(String(300), default="/")
    name: Mapped[str] = mapped_column(String(200))
    anchor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    selector: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WebsiteAsset(Base):
    __tablename__ = "website_assets"
    __table_args__ = (UniqueConstraint("project_id", "asset_id", name="uq_website_asset_project_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    asset_id: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(64), default="image")
    name: Mapped[str] = mapped_column(String(300))
    path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    usage: Mapped[str | None] = mapped_column(String(500), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WebsiteVisualSnapshot(Base):
    __tablename__ = "website_visual_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    viewport: Mapped[str | None] = mapped_column(String(120), nullable=True)
    visual_hash: Mapped[str] = mapped_column(String(128))
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diff_score: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WebsiteIteration(Base):
    __tablename__ = "website_iterations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    parent_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[str] = mapped_column(String(120), index=True)
    instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
