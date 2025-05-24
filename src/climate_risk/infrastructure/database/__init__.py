"""Database package for the Climate Risk Assessment Tool."""
from .session import (
    sync_engine,
    async_engine,
    SyncSessionLocal,
    AsyncSessionLocal,
    get_db,
    get_session,
    get_sync_session,
    get_async_session,
    get_db_session,
    get_db_dependency,
)
from .models import (
    Base,
    LocationModel,
    WeatherDataModel,
    RiskAssessmentModel,
    RiskScoreModel,
)

__all__ = [
    # Engines
    'sync_engine',
    'async_engine',
    
    # Session factories
    'SyncSessionLocal',
    'AsyncSessionLocal',
    
    # Session getters
    'get_db',
    'get_session',
    'get_sync_session',
    'get_async_session',
    'get_db_session',
    'get_db_dependency',
    
    # Models
    'Base',
    'LocationModel',
    'WeatherDataModel',
    'RiskAssessmentModel',
    'RiskScoreModel',
]
