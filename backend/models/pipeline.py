from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ProductStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    MATCHING = "matching"
    EXTRACTING = "extracting"
    MERGING = "merging"
    COPYWRITING = "copywriting"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    ERROR = "error"


class JobStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class ProductProgress(BaseModel):
    product_id: str
    title: str = ""
    status: ProductStatus = ProductStatus.PENDING
    current_agent: str = ""
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Job(BaseModel):
    id: str
    filename: str
    total_products: int = 0
    completed_products: int = 0
    failed_products: int = 0
    status: JobStatus = JobStatus.CREATED
    llm_provider: str = "deepseek"
    workers: int = 10
    products: list[ProductProgress] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_file: str | None = None
    job_folder: str | None = None
