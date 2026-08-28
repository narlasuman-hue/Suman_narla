"""Database models for the metadata catalog."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class AssetStatus(str, enum.Enum):
    """Asset lifecycle status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    DECOMMISSIONED = "decommissioned"


class AssetTier(str, enum.Enum):
    """Data tier classification."""
    TIER_1 = "tier_1"  # Critical production
    TIER_2 = "tier_2"  # Production
    TIER_3 = "tier_3"  # Non-production


class Database(Base):
    """Database entity."""
    __tablename__ = "databases"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    owner = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    description = Column(Text)
    status = Column(Enum(AssetStatus), default=AssetStatus.ACTIVE)
    last_synced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tables = relationship("Table", back_populates="database", cascade="all, delete-orphan")
    views = relationship("View", back_populates="database", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Database(name={self.name}, owner={self.owner})>"


class Table(Base):
    """Table entity."""
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True)
    db_id = Column(Integer, ForeignKey("databases.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    table_type = Column(String(50))  # PERMANENT, VOLATILE, GLOBAL TEMP
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime)
    last_modified = Column(DateTime)
    row_count = Column(Integer)
    size_mb = Column(Float)
    status = Column(Enum(AssetStatus), default=AssetStatus.ACTIVE)
    description = Column(Text)
    last_synced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    database = relationship("Database", back_populates="tables")
    columns = relationship("TableColumn", back_populates="table", cascade="all, delete-orphan")
    lifecycle = relationship("AssetLifecycle", back_populates="table", cascade="all, delete-orphan", uselist=False)
    usage = relationship("UsageMetrics", back_populates="table", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<Table(name={self.name}, db_id={self.db_id})>"


class TableColumn(Base):
    """Column entity."""
    __tablename__ = "columns"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    data_type = Column(String(100))
    nullable = Column(Boolean, default=True)
    sensitive_flag = Column(Boolean, default=False)
    description = Column(Text)
    position = Column(Integer)  # Column order in table
    last_synced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    table = relationship("Table", back_populates="columns")

    def __repr__(self):
        return f"<TableColumn(name={self.name}, table_id={self.table_id})>"


class View(Base):
    """View entity."""
    __tablename__ = "views"

    id = Column(Integer, primary_key=True)
    db_id = Column(Integer, ForeignKey("databases.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    view_type = Column(String(50))  # STANDARD, MATERIALIZED
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime)
    definition = Column(Text)
    status = Column(Enum(AssetStatus), default=AssetStatus.ACTIVE)
    description = Column(Text)
    last_synced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    database = relationship("Database", back_populates="views")

    def __repr__(self):
        return f"<View(name={self.name}, db_id={self.db_id})>"


class Job(Base):
    """ETL/Batch Job entity."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    owner = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    schedule = Column(String(100))  # Cron expression
    frequency = Column(String(50))  # DAILY, HOURLY, WEEKLY, etc.
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    status = Column(Enum(AssetStatus), default=AssetStatus.ACTIVE)
    description = Column(Text)
    execution_timeout_seconds = Column(Integer)
    last_synced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Source system this job originates from (TERADATA, MAINFRAME)
    source_system = Column(String(50), default="TERADATA", index=True)
    # Mainframe-specific fields
    job_class = Column(String(10))  # JES job class, e.g. A, B
    scheduler_system = Column(String(50))  # e.g. CA-7, Control-M, OPC/TWS
    schedule_name = Column(String(100), index=True)  # Scheduler-side schedule/application name

    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")
    lifecycle = relationship("AssetLifecycle", back_populates="job", cascade="all, delete-orphan", uselist=False)
    files = relationship("JobFile", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(name={self.name}, owner={self.owner})>"


class JobFile(Base):
    """File/dataset used by a job (DD statement for mainframe jobs)."""
    __tablename__ = "job_files"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    dd_name = Column(String(20))  # DD statement name (mainframe) or logical file alias
    dataset_name = Column(String(255), nullable=False)
    disposition = Column(String(20))  # NEW, OLD, SHR, MOD, CATLG, DELETE
    direction = Column(String(10))  # INPUT, OUTPUT, INOUT
    dataset_type = Column(String(20))  # PS, PDS, VSAM, GDG, etc.
    volume_serial = Column(String(20))
    description = Column(Text)
    last_synced = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("Job", back_populates="files")

    def __repr__(self):
        return f"<JobFile(job_id={self.job_id}, dataset_name={self.dataset_name})>"


class JobExecution(Base):
    """Job execution history."""
    __tablename__ = "job_executions"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(50))  # SUCCESS, FAILED, RUNNING
    duration_seconds = Column(Integer)
    error_message = Column(Text)
    rows_processed = Column(Integer)

    job = relationship("Job", back_populates="executions")

    def __repr__(self):
        return f"<JobExecution(job_id={self.job_id}, status={self.status})>"


class Lineage(Base):
    """Data lineage tracking."""
    __tablename__ = "lineage"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, nullable=False)
    source_type = Column(String(50))  # TABLE, VIEW, JOB
    target_id = Column(Integer, nullable=False)
    target_type = Column(String(50))  # TABLE, VIEW, JOB
    job_id = Column(Integer, ForeignKey("jobs.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)

    job = relationship("Job")

    def __repr__(self):
        return f"<Lineage(source={self.source_type}:{self.source_id}, target={self.target_type}:{self.target_id})>"


class AssetLifecycle(Base):
    """Asset lifecycle tracking."""
    __tablename__ = "asset_lifecycle"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey("tables.id"), unique=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), unique=True)
    asset_type = Column(String(50), nullable=False)  # TABLE, VIEW, JOB
    created_date = Column(DateTime, nullable=False)
    decommissioned_date = Column(DateTime)
    decommissioning_reason = Column(Text)
    status = Column(Enum(AssetStatus), default=AssetStatus.ACTIVE)
    owner = Column(String(255))
    tier = Column(Enum(AssetTier), default=AssetTier.TIER_2)
    last_reviewed = Column(DateTime)
    review_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    table = relationship("Table", back_populates="lifecycle")
    job = relationship("Job", back_populates="lifecycle")

    def __repr__(self):
        return f"<AssetLifecycle(asset_type={self.asset_type}, status={self.status})>"


class UsageMetrics(Base):
    """Asset usage metrics."""
    __tablename__ = "usage_metrics"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey("tables.id"), unique=True)
    last_accessed = Column(DateTime)
    access_count_7d = Column(Integer, default=0)
    access_count_30d = Column(Integer, default=0)
    access_count_90d = Column(Integer, default=0)
    total_access_count = Column(Integer, default=0)
    average_query_time_ms = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    table = relationship("Table", back_populates="usage")

    def __repr__(self):
        return f"<UsageMetrics(table_id={self.table_id}, access_7d={self.access_count_7d})>"


class AssetTag(Base):
    """Asset tags and classifications."""
    __tablename__ = "asset_tags"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey("tables.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    asset_type = Column(String(50), nullable=False)  # TABLE, VIEW, JOB
    tag_key = Column(String(100), nullable=False)
    tag_value = Column(String(255))
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    table = relationship("Table")
    job = relationship("Job")

    def __repr__(self):
        return f"<AssetTag(key={self.tag_key}, value={self.tag_value})>"
