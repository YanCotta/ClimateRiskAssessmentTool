"""Risk assessment domain entities."""
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional, Dict, Any
from pydantic import Field, validator, model_validator, confloat

from .base import BaseEntity

class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

class RiskType(str, Enum):
    """Types of climate risks."""
    FLOOD = "flood"
    HEATWAVE = "heatwave"
    HURRICANE = "hurricane"
    DROUGHT = "drought"
    WILDFIRE = "wildfire"
    COLD_WAVE = "cold_wave"
    STORM = "storm"
    SEA_LEVEL_RISE = "sea_level_rise"

class RiskScore(BaseEntity):
    """Risk assessment score for a specific risk type."""
    location_id: str = Field(..., description="Reference to location")
    risk_type: RiskType = Field(..., description="Type of risk")
    score: float = Field(..., description="Risk score (0-1)", ge=0.0, le=1.0)
    confidence: float = Field(..., description="Confidence in the score (0-1)", ge=0.0, le=1.0)
    level: RiskLevel = Field(..., description="Risk level based on score")
    
    # Time-related fields
    valid_from: datetime = Field(..., description="When this risk assessment is valid from")
    valid_to: datetime = Field(..., description="When this risk assessment expires")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional risk assessment metadata"
    )
    
    @validator('level', pre=True)
    def determine_risk_level(cls, v, values):
        """Determine risk level based on score if not provided."""
        if v is None and 'score' in values:
            score = values['score']
            if score >= 0.8:
                return RiskLevel.EXTREME
            elif score >= 0.6:
                return RiskLevel.HIGH
            elif score >= 0.4:
                return RiskLevel.MODERATE
            return RiskLevel.LOW
        return v
    
    @model_validator(mode='after')
    def validate_dates(self):
        """Ensure valid_to is after valid_from."""
        if self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        return self

class RiskAssessment(BaseEntity):
    """Comprehensive risk assessment for a location."""
    location_id: str = Field(..., description="Reference to location")
    timestamp: datetime = Field(..., description="When the assessment was made")
    
    # Risk scores by type
    risk_scores: Dict[RiskType, RiskScore] = Field(
        default_factory=dict,
        description="Risk scores by risk type"
    )
    
    # Overall risk metrics
    overall_risk: float = Field(..., description="Overall risk score (0-1)", ge=0.0, le=1.0)
    overall_level: RiskLevel = Field(..., description="Overall risk level")
    
    # Time range for which this assessment is valid
    valid_from: datetime = Field(..., description="When this assessment is valid from")
    valid_to: datetime = Field(..., description="When this assessment expires")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional assessment metadata"
    )
    
    @validator('overall_level', pre=True)
    def determine_overall_level(cls, v, values):
        """Determine overall risk level based on overall_risk if not provided."""
        if v is None and 'overall_risk' in values:
            risk = values['overall_risk']
            if risk >= 0.8:
                return RiskLevel.EXTREME
            elif risk >= 0.6:
                return RiskLevel.HIGH
            elif risk >= 0.4:
                return RiskLevel.MODERATE
            return RiskLevel.LOW
        return v
    
    @model_validator(mode='after')
    def validate_risk_scores(self):
        """Validate that risk scores match the assessment's time range."""
        for risk_score in self.risk_scores.values():
            if risk_score.valid_from < self.valid_from or risk_score.valid_to > self.valid_to:
                raise ValueError("Risk score time range must be within assessment time range")
        return self
