"""Risk assessment repository implementation."""
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, or_, between, desc
from sqlalchemy.orm import selectinload, joinedload, contains_eager

from ....domain.entities.risk import RiskAssessment, RiskScore, RiskLevel, RiskType
from ....domain.entities.location import GeoPoint
from ....domain.repositories import RiskAssessmentRepository
from ....domain.repositories.base import FilterType, PaginationParams, SortDirection
from ..database.models import RiskAssessmentModel, RiskScoreModel, LocationModel
from .base import SQLAlchemyRepository

class RiskAssessmentRepositoryImpl(
    SQLAlchemyRepository[RiskAssessmentModel, RiskAssessment, RiskAssessment],
    RiskAssessmentRepository
):
    """Risk assessment repository implementation using SQLAlchemy."""
    
    def __init__(self, session):
        """Initialize the repository."""
        super().__init__(RiskAssessmentModel, session, RiskAssessment)
    
    async def get_for_location(
        self, 
        location_id: str, 
        valid_at: Optional[datetime] = None,
        **kwargs
    ) -> List[RiskAssessment]:
        """Get risk assessments for a specific location.
        
        Args:
            location_id: Location ID
            valid_at: Optional timestamp to filter valid assessments
            **kwargs: Additional query parameters
            
        Returns:
            List of risk assessments
        """
        # Start with base query
        stmt = select(self.model).where(
            self.model.location_id == location_id
        )
        
        # Filter by validity period if provided
        if valid_at is not None:
            stmt = stmt.where(
                and_(
                    self.model.valid_from <= valid_at,
                    self.model.valid_to >= valid_at
                )
            )
        
        # Apply additional filters if provided
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Default to sorting by timestamp descending (newest first)
        sort_by = kwargs.get("sort_by", "timestamp")
        sort_direction = kwargs.get("sort_direction", SortDirection.DESC)
        stmt = self._apply_sorting(stmt, sort_by, sort_direction)
        
        # Apply pagination if provided
        if "pagination" in kwargs:
            stmt = self._apply_pagination(stmt, kwargs["pagination"])
        
        # Eager load risk scores
        stmt = stmt.options(selectinload(self.model.risk_scores))
        
        # Execute query
        result = await self.session.execute(stmt)
        assessments = result.scalars().all()
        
        # Convert to domain models
        return [self._map_to_domain(a) for a in assessments]
    
    async def get_latest_for_location(
        self, 
        location_id: str,
        **kwargs
    ) -> Optional[RiskAssessment]:
        """Get the latest risk assessment for a location.
        
        Args:
            location_id: Location ID
            **kwargs: Additional query parameters
            
        Returns:
            Latest risk assessment if found, None otherwise
        """
        # Get the most recent assessment for the location
        stmt = select(self.model).where(
            self.model.location_id == location_id
        ).order_by(
            self.model.timestamp.desc()
        ).limit(1)
        
        # Eager load risk scores
        stmt = stmt.options(selectinload(self.model.risk_scores))
        
        # Execute query
        result = await self.session.execute(stmt)
        assessment = result.scalars().first()
        
        if not assessment:
            return None
            
        return self._map_to_domain(assessment)
    
    async def get_by_risk_level(
        self, 
        risk_level: RiskLevel,
        valid_at: Optional[datetime] = None,
        **kwargs
    ) -> List[RiskAssessment]:
        """Get risk assessments by risk level.
        
        Args:
            risk_level: Risk level to filter by
            valid_at: Optional timestamp to filter valid assessments
            **kwargs: Additional query parameters
            
        Returns:
            List of risk assessments with the specified risk level
        """
        # Start with base query
        stmt = select(self.model).where(
            self.model.overall_level == risk_level
        )
        
        # Filter by validity period if provided
        if valid_at is not None:
            stmt = stmt.where(
                and_(
                    self.model.valid_from <= valid_at,
                    self.model.valid_to >= valid_at
                )
            )
        
        # Apply additional filters if provided
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Default to sorting by timestamp descending (newest first)
        sort_by = kwargs.get("sort_by", "timestamp")
        sort_direction = kwargs.get("sort_direction", SortDirection.DESC)
        stmt = self._apply_sorting(stmt, sort_by, sort_direction)
        
        # Apply pagination if provided
        if "pagination" in kwargs:
            stmt = self._apply_pagination(stmt, kwargs["pagination"])
        
        # Eager load risk scores and location
        stmt = stmt.options(
            selectinload(self.model.risk_scores),
            joinedload(self.model.location)
        )
        
        # Execute query
        result = await self.session.execute(stmt)
        assessments = result.unique().scalars().all()
        
        # Convert to domain models
        return [self._map_to_domain(a) for a in assessments]
    
    async def get_risk_history(
        self, 
        location_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[RiskAssessment]:
        """Get risk assessment history for a location.
        
        Args:
            location_id: Location ID
            start_date: Start date for history
            end_date: Optional end date (defaults to now)
            **kwargs: Additional query parameters
            
        Returns:
            List of historical risk assessments
        """
        # Set default end date to now if not provided
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Create base query
        stmt = select(self.model).where(
            and_(
                self.model.location_id == location_id,
                self.model.timestamp >= start_date,
                self.model.timestamp <= end_date
            )
        )
        
        # Apply additional filters if provided
        if "filters" in kwargs:
            stmt = self._apply_filters(stmt, kwargs["filters"])
        
        # Default to sorting by timestamp ascending (oldest first)
        sort_by = kwargs.get("sort_by", "timestamp")
        sort_direction = kwargs.get("sort_direction", SortDirection.ASC)
        stmt = self._apply_sorting(stmt, sort_by, sort_direction)
        
        # Apply pagination if provided
        if "pagination" in kwargs:
            stmt = self._apply_pagination(stmt, kwargs["pagination"])
        
        # Eager load risk scores
        stmt = stmt.options(selectinload(self.model.risk_scores))
        
        # Execute query
        result = await self.session.execute(stmt)
        assessments = result.scalars().all()
        
        # Convert to domain models
        return [self._map_to_domain(a) for a in assessments]
    
    async def create(self, obj_in: RiskAssessment, **kwargs) -> RiskAssessment:
        """Create a new risk assessment with its risk scores.
        
        Args:
            obj_in: Risk assessment data
            **kwargs: Additional parameters
            
        Returns:
            The created risk assessment
        """
        # Start a transaction
        async with self.session.begin_nested():
            # Convert to dict and prepare data
            obj_in_data = obj_in.dict(exclude_unset=True, exclude={"risk_scores"})
            
            # Create the risk assessment
            db_obj = self.model(**obj_in_data)
            self.session.add(db_obj)
            
            # Create risk scores
            for score_data in obj_in.risk_scores.values():
                score_dict = score_data.dict(exclude_unset=True)
                score_db = RiskScoreModel(**score_dict, assessment_id=db_obj.id)
                self.session.add(score_db)
            
            # Commit the transaction
            await self.session.commit()
            
            # Refresh the object to get the generated ID
            await self.session.refresh(db_obj)
            
            # Eager load risk scores for the response
            await self.session.refresh(db_obj, ["risk_scores"])
            
            return self._map_to_domain(db_obj)
    
    async def get_stats(
        self,
        location_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get risk assessment statistics.
        
        Args:
            location_id: Optional location ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing risk assessment statistics
        """
        # Create base query
        stmt = select([
            func.avg(self.model.overall_risk).label("avg_risk"),
            func.max(self.model.overall_risk).label("max_risk"),
            func.min(self.model.overall_risk).label("min_risk"),
            func.count(self.model.id).label("assessment_count"),
            self.model.overall_level.label("risk_level"),
            func.count(self.model.overall_level).label("level_count")
        ])
        
        # Apply filters
        conditions = []
        if location_id:
            conditions.append(self.model.location_id == location_id)
            
        if start_date:
            conditions.append(self.model.timestamp >= start_date)
            
        if end_date:
            conditions.append(self.model.timestamp <= end_date)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Group by risk level for distribution
        stmt = stmt.group_by(self.model.overall_level)
        
        # Execute query
        result = await self.session.execute(stmt)
        rows = result.all()
        
        # Calculate overall stats
        total_assessments = sum(row.assessment_count for row in rows) if rows else 0
        
        # Calculate risk level distribution
        level_distribution = {
            row.risk_level.value: {
                "count": row.level_count,
                "percentage": (row.level_count / total_assessments * 100) if total_assessments > 0 else 0
            }
            for row in rows
        }
        
        # Get overall stats
        overall_stats = {
            "total_assessments": total_assessments,
            "avg_risk": float(rows[0].avg_risk) if rows else 0.0,
            "max_risk": float(rows[0].max_risk) if rows else 0.0,
            "min_risk": float(rows[0].min_risk) if rows else 0.0,
            "risk_level_distribution": level_distribution,
            "start_date": start_date,
            "end_date": end_date,
            "location_id": location_id
        }
        
        return overall_stats
    
    def _map_to_domain(self, db_obj: Any) -> RiskAssessment:
        """Map a database model to a domain model.
        
        Args:
            db_obj: Database model instance
            
        Returns:
            Domain model instance
        """
        if not db_obj:
            return None
            
        # Convert to dict
        data = {c.name: getattr(db_obj, c.name) for c in db_obj.__table__.columns}
        
        # Handle risk scores
        risk_scores = {}
        if hasattr(db_obj, 'risk_scores') and db_obj.risk_scores:
            for score in db_obj.risk_scores:
                risk_scores[score.risk_type] = RiskScore(
                    **{c.name: getattr(score, c.name) for c in score.__table__.columns}
                )
        
        data["risk_scores"] = risk_scores
        
        return RiskAssessment(**data)
