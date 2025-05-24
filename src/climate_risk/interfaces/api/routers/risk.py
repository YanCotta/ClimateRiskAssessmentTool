"""Risk assessment API endpoints."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....domain.entities.risk import RiskAssessment, RiskType
from ....application.services import RiskAssessmentService
from ..dependencies import get_risk_service

class RiskRouter:
    """Router for risk assessment endpoints."""
    
    def __init__(self):
        """Initialize the risk router."""
        self.router = APIRouter(prefix="/risk-assessments", tags=["risk"])
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Register risk assessment routes."""
        
        @self.router.post(
            "/assess",
            response_model=RiskAssessment,
            status_code=status.HTTP_201_CREATED,
            summary="Assess climate risk for a location"
        )
        async def assess_risk(
            location_id: str,
            time_horizon_days: int = Query(
                7,
                ge=1,
                le=365,
                description="Time horizon for risk assessment in days (1-365)"
            ),
            service: RiskAssessmentService = Depends(get_risk_service)
        ) -> RiskAssessment:
            """
            Perform a climate risk assessment for a specific location.
            
            Args:
                location_id: The ID of the location to assess
                time_horizon_days: Time horizon for the assessment in days
                service: Injected risk assessment service
                
            Returns:
                The risk assessment results
            """
            return await service.assess_location_risk(
                location_id=location_id,
                time_horizon_days=time_horizon_days
            )
        
        @self.router.get(
            "/locations/{location_id}",
            response_model=List[RiskAssessment],
            summary="Get risk assessments for a location"
        )
        async def get_risk_assessments(
            location_id: str,
            start_date: Optional[datetime] = Query(
                None,
                description="Filter assessments after this date"
            ),
            end_date: Optional[datetime] = Query(
                None,
                description="Filter assessments before this date"
            ),
            service: RiskAssessmentService = Depends(get_risk_service)
        ) -> List[RiskAssessment]:
            """
            Get risk assessments for a specific location.
            
            Args:
                location_id: The ID of the location
                start_date: Optional start date filter
                end_date: Optional end date filter
                service: Injected risk assessment service
                
            Returns:
                List of risk assessments for the location
            """
            return await service.get_assessment_history(
                location_id=location_id,
                start_date=start_date,
                end_date=end_date
            )
        
        @self.router.get(
            "/locations/{location_id}/latest",
            response_model=RiskAssessment,
            summary="Get the latest risk assessment for a location"
        )
        async def get_latest_risk_assessment(
            location_id: str,
            service: RiskAssessmentService = Depends(get_risk_service)
        ) -> RiskAssessment:
            """
            Get the most recent risk assessment for a location.
            
            Args:
                location_id: The ID of the location
                service: Injected risk assessment service
                
            Returns:
                The latest risk assessment for the location
                
            Raises:
                HTTPException: If no assessment is found for the location
            """
            assessment = await service.get_latest_assessment(location_id)
            if not assessment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No risk assessment found for location {location_id}"
                )
            return assessment
        
        @self.router.get(
            "/types",
            response_model=List[str],
            summary="Get available risk types"
        )
        async def get_risk_types() -> List[str]:
            """
            Get a list of all available risk types.
            
            Returns:
                List of risk type identifiers
            """
            return [t.value for t in RiskType]

# Create router instance
router = RiskRouter().router
