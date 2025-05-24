"""Base repository implementations."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from datetime import datetime

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from ....domain.repositories.base import (
    BaseRepository,
    FilterType,
    PaginationParams,
    SortDirection,
)

T = TypeVar("T")
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class SQLAlchemyRepository(
    BaseRepository[T], 
    Generic[ModelType, CreateSchemaType, UpdateSchemaType, T]
):
    """Base repository implementation using SQLAlchemy."""
    
    def __init__(
        self, 
        model: Type[ModelType],
        session: AsyncSession,
        schema: Type[T]
    ):
        """Initialize the repository.
        
        Args:
            model: SQLAlchemy model class
            session: SQLAlchemy async session
            schema: Pydantic model for serialization/deserialization
        """
        self.model = model
        self.session = session
        self.schema = schema
    
    def _apply_filters(
        self, 
        stmt: Any, 
        filters: Optional[FilterType] = None
    ) -> Any:
        """Apply filters to a SQLAlchemy statement.
        
        Args:
            stmt: SQLAlchemy select statement
            filters: Dictionary of filters to apply
            
        Returns:
            Modified SQLAlchemy statement with filters applied
        """
        if not filters:
            return stmt
            
        filter_conditions = []
        
        for field, value in filters.items():
            # Handle special filter conditions (__lt, __gt, etc.)
            if "__" in field:
                field_name, op = field.split("__")
                column = getattr(self.model, field_name, None)
                
                if column is None:
                    continue
                    
                if op == "eq":
                    filter_conditions.append(column == value)
                elif op == "ne":
                    filter_conditions.append(column != value)
                elif op == "gt":
                    filter_conditions.append(column > value)
                elif op == "lt":
                    filter_conditions.append(column < value)
                elif op == "ge":
                    filter_conditions.append(column >= value)
                elif op == "le":
                    filter_conditions.append(column <= value)
                elif op == "in":
                    filter_conditions.append(column.in_(value))
                elif op == "not_in":
                    filter_conditions.append(column.notin_(value))
                elif op == "contains":
                    filter_conditions.append(column.contains(value))
                elif op == "icontains":
                    filter_conditions.append(column.ilike(f"%{value}%"))
                elif op == "startswith":
                    filter_conditions.append(column.startswith(value))
                elif op == "endswith":
                    filter_conditions.append(column.endswith(value))
                elif op == "is_null":
                    if value:
                        filter_conditions.append(column.is_(None))
                    else:
                        filter_conditions.append(column.isnot(None))
            else:
                # Default to equality comparison
                column = getattr(self.model, field, None)
                if column is not None:
                    filter_conditions.append(column == value)
        
        if filter_conditions:
            stmt = stmt.where(and_(*filter_conditions))
            
        return stmt
    
    def _apply_sorting(
        self, 
        stmt: Any, 
        sort_by: Optional[str] = None, 
        sort_direction: SortDirection = SortDirection.ASC
    ) -> Any:
        """Apply sorting to a SQLAlchemy statement.
        
        Args:
            stmt: SQLAlchemy select statement
            sort_by: Field to sort by
            sort_direction: Sort direction (ascending or descending)
            
        Returns:
            Modified SQLAlchemy statement with sorting applied
        """
        if not sort_by:
            return stmt
            
        column = getattr(self.model, sort_by, None)
        if column is None:
            return stmt
            
        if sort_direction == SortDirection.DESC:
            return stmt.order_by(column.desc())
        return stmt.order_by(column.asc())
    
    def _apply_pagination(
        self, 
        stmt: Any, 
        pagination: Optional[PaginationParams] = None
    ) -> Any:
        """Apply pagination to a SQLAlchemy statement.
        
        Args:
            stmt: SQLAlchemy select statement
            pagination: Pagination parameters
            
        Returns:
            Modified SQLAlchemy statement with pagination applied
        """
        if not pagination:
            return stmt
            
        offset = (pagination.page - 1) * pagination.size
        return stmt.offset(offset).limit(pagination.size)
    
    async def get_by_id(
        self, 
        id: str, 
        **kwargs
    ) -> Optional[T]:
        """Get a record by ID.
        
        Args:
            id: Record ID
            **kwargs: Additional query parameters
            
        Returns:
            The record if found, None otherwise
        """
        stmt = select(self.model).where(self.model.id == id)
        
        # Apply any additional filtering
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Load relationships if specified
        if "load_relationships" in kwargs:
            for relationship in kwargs["load_relationships"]:
                stmt = stmt.options(selectinload(getattr(self.model, relationship)))
        
        result = await self.session.execute(stmt)
        instance = result.scalars().first()
        
        if not instance:
            return None
            
        return self.schema.from_orm(instance)
    
    async def list(
        self, 
        filters: Optional[FilterType] = None,
        pagination: Optional[PaginationParams] = None,
        sort_by: Optional[str] = None,
        sort_direction: SortDirection = SortDirection.ASC,
        **kwargs
    ) -> List[T]:
        """List records with optional filtering, sorting, and pagination.
        
        Args:
            filters: Dictionary of filters to apply
            pagination: Pagination parameters
            sort_by: Field to sort by
            sort_direction: Sort direction (ascending or descending)
            **kwargs: Additional query parameters
            
        Returns:
            List of records
        """
        stmt = select(self.model)
        
        # Apply filters
        stmt = self._apply_filters(stmt, filters)
        
        # Apply sorting
        stmt = self._apply_sorting(stmt, sort_by, sort_direction)
        
        # Apply pagination
        stmt = self._apply_pagination(stmt, pagination)
        
        # Load relationships if specified
        if "load_relationships" in kwargs:
            for relationship in kwargs["load_relationships"]:
                stmt = stmt.options(selectinload(getattr(self.model, relationship)))
        
        result = await self.session.execute(stmt)
        instances = result.scalars().all()
        
        return [self.schema.from_orm(instance) for instance in instances]
    
    async def create(self, obj_in: CreateSchemaType, **kwargs) -> T:
        """Create a new record.
        
        Args:
            obj_in: Input data for creating the record
            **kwargs: Additional parameters
            
        Returns:
            The created record
        """
        # Convert Pydantic model to dict and exclude unset fields
        obj_in_data = obj_in.dict(exclude_unset=True)
        
        # Create the database model instance
        db_obj = self.model(**obj_in_data)
        
        # Add to session and commit
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        
        # Convert back to Pydantic model
        return self.schema.from_orm(db_obj)
    
    async def update(
        self, 
        id: str, 
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        **kwargs
    ) -> Optional[T]:
        """Update a record.
        
        Args:
            id: Record ID
            obj_in: Input data for updating the record
            **kwargs: Additional parameters
            
        Returns:
            The updated record if found, None otherwise
        """
        # Get the existing record
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        db_obj = result.scalars().first()
        
        if not db_obj:
            return None
        
        # Convert Pydantic model to dict if needed
        if not isinstance(obj_in, dict):
            update_data = obj_in.dict(exclude_unset=True)
        else:
            update_data = obj_in
        
        # Update the database object
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        # Update timestamps
        if hasattr(db_obj, 'updated_at'):
            db_obj.updated_at = datetime.utcnow()
        
        # Commit changes
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        
        # Convert back to Pydantic model
        return self.schema.from_orm(db_obj)
    
    async def delete(self, id: str, **kwargs) -> bool:
        """Delete a record.
        
        Args:
            id: Record ID
            **kwargs: Additional parameters
            
        Returns:
            True if the record was deleted, False otherwise
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        db_obj = result.scalars().first()
        
        if not db_obj:
            return False
        
        await self.session.delete(db_obj)
        await self.session.commit()
        
        return True
    
    async def count(
        self, 
        filters: Optional[FilterType] = None,
        **kwargs
    ) -> int:
        """Count records matching the given filters.
        
        Args:
            filters: Dictionary of filters to apply
            **kwargs: Additional parameters
            
        Returns:
            Number of matching records
        """
        stmt = select([self.model])
        
        # Apply filters
        stmt = self._apply_filters(stmt, filters)
        
        # Count the results
        result = await self.session.execute(select([sqlalchemy.func.count()]).select_from(stmt.alias()))
        return result.scalar_one()
    
    async def exists(
        self, 
        filters: Optional[FilterType] = None,
        **kwargs
    ) -> bool:
        """Check if any records match the given filters.
        
        Args:
            filters: Dictionary of filters to apply
            **kwargs: Additional parameters
            
        Returns:
            True if any matching records exist, False otherwise
        """
        stmt = select([1]).select_from(self.model).limit(1)
        
        # Apply filters
        stmt = self._apply_filters(stmt, filters)
        
        # Execute the query
        result = await self.session.execute(stmt)
        return result.scalar() is not None
