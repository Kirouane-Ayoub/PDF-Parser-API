from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class ProcessingMetadata(BaseModel):
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    image_dimensions: Optional[tuple[int, int]] = None
    file_size: Optional[int] = None
    additional_data: Optional[Dict[str, Any]] = None


class PageResult(BaseModel):
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    processed_output: Dict[str, Any] = Field(
        ..., description="Response from OpenAI API"
    )
    metadata: Optional[ProcessingMetadata] = None
    error: Optional[str] = None


class PDFProcessResponse(BaseModel):
    success: bool
    total_pages: int
    processed_pages: int
    results: List[PageResult]
    processing_time: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    errors: Optional[List[str]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
