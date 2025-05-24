"""Risk assessment service implementation."""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import numpy as np
from enum import Enum

from ....domain.entities.risk import (
    RiskAssessment, 
    RiskScore, 
    RiskLevel, 
    RiskType
)
from ....domain.entities.weather import WeatherData
from ....domain.entities.location import Location
from ....domain.repositories import (
    RiskAssessmentRepository, 
    WeatherDataRepository,
    LocationRepository
)
from ..services.base import BaseService, ServiceError
from ....config.settings import settings

logger = logging.getLogger(__name__)

class RiskAssessmentService(BaseService[RiskAssessment]):
    """Service for risk assessment operations."""
    
    def __init__(
        self, 
        repository: RiskAssessmentRepository,
        weather_repository: WeatherDataRepository,
        location_repository: LocationRepository
    ):
        super().__init__(repository)
        self.weather_repository = weather_repository
        self.location_repository = location_repository
        
        # Risk model parameters (these would typically be loaded from config)
        self.risk_weights = {
            RiskType.FLOOD: 0.3,
            RiskType.HEATWAVE: 0.25,
            RiskType.HURRICANE: 0.2,
            RiskType.DROUGHT: 0.15,
            RiskType.WILDFIRE: 0.1
        }
        
        # Risk thresholds
        self.risk_thresholds = {
            RiskLevel.LOW: 0.3,
            RiskLevel.MODERATE: 0.5,
            RiskLevel.HIGH: 0.7,
            RiskLevel.EXTREME: 0.9
        }
    
    async def assess_location_risk(
        self,
        location_id: str,
        time_horizon_days: int = 7,
        **kwargs
    ) -> RiskAssessment:
        """Assess climate risk for a location."""
        try:
            # Get location
            location = await self.location_repository.get_by_id(location_id)
            if not location:
                raise ServiceError(
                    f"Location with ID {location_id} not found",
                    code="location_not_found"
                )
            
            # Get weather data for the time horizon
            end_date = datetime.utcnow() + timedelta(days=time_horizon_days)
            weather_data = await self.weather_repository.get_for_location(
                location_id=location_id,
                start_date=datetime.utcnow(),
                end_date=end_date,
                **kwargs
            )
            
            if not weather_data:
                raise ServiceError(
                    f"No weather data available for location {location_id}",
                    code="no_weather_data"
                )
            
            # Calculate risk scores for each risk type
            risk_scores = {}
            
            # Calculate flood risk (simplified example)
            flood_risk = self._calculate_flood_risk(weather_data, location)
            risk_scores[RiskType.FLOOD] = RiskScore(
                location_id=location_id,
                risk_type=RiskType.FLOOD,
                score=flood_risk,
                confidence=0.8,  # This would be calculated based on data quality
                level=self._determine_risk_level(flood_risk),
                valid_from=datetime.utcnow(),
                valid_to=end_date,
                metadata={"model_version": "1.0.0"}
            )
            
            # Calculate heatwave risk (simplified example)
            heatwave_risk = self._calculate_heatwave_risk(weather_data, location)
            risk_scores[RiskType.HEATWAVE] = RiskScore(
                location_id=location_id,
                risk_type=RiskType.HEATWAVE,
                score=heatwave_risk,
                confidence=0.85,
                level=self._determine_risk_level(heatwave_risk),
                valid_from=datetime.utcnow(),
                valid_to=end_date,
                metadata={"model_version": "1.0.0"}
            )
            
            # Calculate overall risk score (weighted average)
            overall_risk = self._calculate_overall_risk(risk_scores)
            
            # Create risk assessment
            assessment = RiskAssessment(
                location_id=location_id,
                timestamp=datetime.utcnow(),
                risk_scores=risk_scores,
                overall_risk=overall_risk,
                overall_level=self._determine_risk_level(overall_risk),
                valid_from=datetime.utcnow(),
                valid_to=end_date,
                metadata={
                    "time_horizon_days": time_horizon_days,
                    "model_version": "1.0.0"
                }
            )
            
            # Save assessment
            return await self.create(assessment, **kwargs)
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to assess risk for location {location_id}: {e}", exc_info=True)
            raise ServiceError(
                message=f"Failed to assess risk for location {location_id}",
                code="risk_assessment_failed",
                details=str(e)
            )
    
    def _calculate_flood_risk(
        self, 
        weather_data: List[WeatherData],
        location: Location
    ) -> float:
        """Calculate flood risk based on precipitation and other factors."""
        try:
            # Simple flood risk calculation based on precipitation
            total_precip = sum(w.precipitation for w in weather_data if w.precipitation)
            avg_precip = total_precip / len(weather_data) if weather_data else 0
            
            # Adjust based on location factors (elevation, proximity to water, etc.)
            elevation_factor = 1.0
            if location.elevation is not None:
                elevation_factor = max(0.1, 1.0 - (location.elevation / 1000.0))  # Lower elevation = higher risk
            
            # Simple flood risk score (0-1)
            flood_risk = min(1.0, (avg_precip / 50.0) * elevation_factor)
            
            return round(flood_risk, 4)
            
        except Exception as e:
            logger.error(f"Error calculating flood risk: {e}")
            return 0.0
    
    def _calculate_heatwave_risk(
        self, 
        weather_data: List[WeatherData],
        location: Location
    ) -> float:
        """Calculate heatwave risk based on temperature and other factors."""
        try:
            # Simple heatwave risk calculation based on temperature
            temps = [w.temperature for w in weather_data if w.temperature is not None]
            avg_temp = sum(temps) / len(temps) if temps else 0
            
            # Simple heatwave risk score (0-1)
            # Assuming 30°C is the threshold for heatwave conditions
            heatwave_risk = min(1.0, max(0, (avg_temp - 25) / 15.0))
            
            return round(heatwave_risk, 4)
            
        except Exception as e:
            logger.error(f"Error calculating heatwave risk: {e}")
            return 0.0
    
    def _calculate_overall_risk(
        self, 
        risk_scores: Dict[RiskType, RiskScore]
    ) -> float:
        """Calculate overall risk score as a weighted average of individual risks."""
        total_weight = 0.0
        weighted_sum = 0.0
        
        for risk_type, risk_score in risk_scores.items():
            weight = self.risk_weights.get(risk_type, 0.1)  # Default weight if not specified
            weighted_sum += risk_score.score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
            
        return round(weighted_sum / total_weight, 4)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level based on score."""
        if score >= self.risk_thresholds[RiskLevel.EXTREME]:
            return RiskLevel.EXTREME
        elif score >= self.risk_thresholds[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        elif score >= self.risk_thresholds[RiskLevel.MODERATE]:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    async def get_latest_assessment(
        self,
        location_id: str,
        **kwargs
    ) -> Optional[RiskAssessment]:
        """Get the most recent risk assessment for a location."""
        try:
            return await self.repository.get_latest_for_location(
                location_id=location_id,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to get latest assessment for location {location_id}: {e}")
            raise ServiceError(
                message=f"Failed to get latest assessment for location {location_id}",
                code="get_latest_assessment_failed",
                details=str(e)
            )
    
    async def get_assessment_history(
        self,
        location_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[RiskAssessment]:
        """Get risk assessment history for a location."""
        try:
            return await self.repository.get_for_location(
                location_id=location_id,
                valid_at=end_date or datetime.utcnow(),
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to get assessment history for location {location_id}: {e}")
            raise ServiceError(
                message=f"Failed to get assessment history for location {location_id}",
                code="get_assessment_history_failed",
                details=str(e)
            )
