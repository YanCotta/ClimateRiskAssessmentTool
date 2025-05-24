"""SQLAlchemy database models."""
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, Enum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from ....domain.entities.location import LocationType
from ....domain.entities.weather import WeatherCondition
from ....domain.entities.risk import RiskType, RiskLevel

# Base class for all models
Base = declarative_base()

def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())

class LocationModel(Base):
    """Location database model."""
    __tablename__ = "locations"
    
    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
        index=True
    )
    name = Column(String(255), nullable=False)
    location_type = Column(Enum(LocationType), nullable=False)
    country_code = Column(String(2), nullable=True, index=True)
    admin1_code = Column(String(20), nullable=True, index=True)
    admin2_code = Column(String(80), nullable=True, index=True)
    admin3_code = Column(String(20), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    elevation = Column(Float, nullable=True)
    timezone = Column(String(50), nullable=True)
    population = Column(Integer, nullable=True)
    geog = Column(
        Geometry(geometry_type='POINT', srid=4326, spatial_index=True),
        nullable=True
    )
    metadata_ = Column("metadata", JSONB, nullable=True, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    weather_data = relationship("WeatherDataModel", back_populates="location")
    risk_assessments = relationship("RiskAssessmentModel", back_populates="location")
    
    # Indexes
    __table_args__ = (
        Index('idx_location_geog', 'geog', postgresql_using='gist'),
        Index('idx_location_name', 'name', postgresql_using='gin', 
              postgresql_ops={'name': 'gin_trgm_ops'}),
    )
    
    def __repr__(self) -> str:
        return f"<Location(id={self.id}, name='{self.name}')>"

class WeatherDataModel(Base):
    """Weather data database model."""
    __tablename__ = "weather_data"
    
    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
        index=True
    )
    location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    timestamp = Column(DateTime, nullable=False, index=True)
    temperature = Column(Float, nullable=True)  # in Celsius
    feels_like = Column(Float, nullable=True)  # in Celsius
    temperature_min = Column(Float, nullable=True)  # in Celsius
    temperature_max = Column(Float, nullable=True)  # in Celsius
    pressure = Column(Float, nullable=True)  # in hPa
    humidity = Column(Float, nullable=True)  # in %
    wind_speed = Column(Float, nullable=True)  # in m/s
    wind_direction = Column(Float, nullable=True)  # in degrees
    wind_gust = Column(Float, nullable=True)  # in m/s
    cloud_cover = Column(Float, nullable=True)  # in %
    visibility = Column(Float, nullable=True)  # in meters
    precipitation = Column(Float, nullable=True)  # in mm
    snow = Column(Float, nullable=True)  # in mm
    weather_condition = Column(Enum(WeatherCondition), nullable=True)
    sunrise = Column(DateTime, nullable=True)
    sunset = Column(DateTime, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    location = relationship("LocationModel", back_populates="weather_data")
    
    # Indexes
    __table_args__ = (
        Index('idx_weather_data_timestamp', 'timestamp'),
        Index('idx_weather_data_location_timestamp', 'location_id', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<WeatherData(id={self.id}, location_id={self.location_id}, timestamp={self.timestamp})>"

class RiskAssessmentModel(Base):
    """Risk assessment database model."""
    __tablename__ = "risk_assessments"
    
    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
        index=True
    )
    location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    timestamp = Column(DateTime, nullable=False, index=True)
    overall_risk = Column(Float, nullable=False)  # 0-1 scale
    overall_level = Column(Enum(RiskLevel), nullable=False)
    valid_from = Column(DateTime, nullable=False, index=True)
    valid_to = Column(DateTime, nullable=False, index=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    location = relationship("LocationModel", back_populates="risk_assessments")
    risk_scores = relationship(
        "RiskScoreModel", 
        back_populates="assessment",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_risk_assessment_timestamp', 'timestamp'),
        Index('idx_risk_assessment_location_timestamp', 'location_id', 'timestamp'),
        Index('idx_risk_assessment_valid_range', 'valid_from', 'valid_to'),
    )
    
    def __repr__(self) -> str:
        return f"<RiskAssessment(id={self.id}, location_id={self.location_id}, timestamp={self.timestamp})>"

class RiskScoreModel(Base):
    """Risk score database model."""
    __tablename__ = "risk_scores"
    
    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
        index=True
    )
    assessment_id = Column(
        UUID(as_uuid=False),
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    risk_type = Column(Enum(RiskType), nullable=False, index=True)
    score = Column(Float, nullable=False)  # 0-1 scale
    confidence = Column(Float, nullable=True)  # 0-1 scale
    level = Column(Enum(RiskLevel), nullable=False)
    valid_from = Column(DateTime, nullable=False, index=True)
    valid_to = Column(DateTime, nullable=False, index=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    assessment = relationship("RiskAssessmentModel", back_populates="risk_scores")
    
    # Indexes
    __table_args__ = (
        Index('idx_risk_score_risk_type', 'risk_type'),
        Index('idx_risk_score_assessment_risk_type', 'assessment_id', 'risk_type', unique=True),
        Index('idx_risk_score_valid_range', 'valid_from', 'valid_to'),
    )
    
    def __repr__(self) -> str:
        return f"<RiskScore(id={self.id}, assessment_id={self.assessment_id}, risk_type={self.risk_type})>"
