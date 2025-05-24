"""Base models and interfaces for domain entities."""
from datetime import datetime
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic.generics import GenericModel

# Type variable for generic models
T = TypeVar('T')

class BaseEntity(BaseModel):
    """Base entity with common fields and configuration."""
    
    id: Optional[str] = Field(default=None, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    def model_post_init(self, __context: Any) -> None:
        """Update timestamps on initialization."""
        if not self.updated_at:
            self.updated_at = self.created_at
        return super().model_post_init(__context)
    
    def update(self, **kwargs) -> None:
        """Update entity fields and set updated_at timestamp."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()

class PaginatedResponse(GenericModel, Generic[T]):
    """Generic paginated response model."""
    
    items: list[T] = Field(..., description="List of items in the current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(1, description="Current page number")
    size: int = Field(10, description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
