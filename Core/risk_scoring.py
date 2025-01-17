import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
from sklearn.preprocessing import MinMaxScaler
from .model_training import WeatherData, Location, MLModelManager

@dataclass
class RiskThresholds:
    """Risk thresholds configuration"""
    critical: float = 0.8
    high: float = 0.6
    moderate: float = 0.4
    low: float = 0.2

class RiskScoring:
    def __init__(self, model_manager: MLModelManager):
        self.model_manager = model_manager
        self.scaler = MinMaxScaler()
        self.thresholds = RiskThresholds()
        
    def calculate_risk_scores(self, location: Location,
                            weather_data: List<WeatherData]) -> Dict[str, Dict[str, float]]:
        """Calculate comprehensive risk scores with confidence levels"""
        # Convert data to features
        features = self._prepare_features(weather_data, location)
        
        # Get base predictions
        predictions = {
            risk_type: self.model_manager.predict(risk_type, features)
            for risk_type in ['flood', 'heatwave', 'hurricane', 'drought']
        }
        
        # Calculate combined risks
        combined_risks = self._combine_risk_factors(predictions, location)
        
        # Add temporal evolution
        temporal_risks = self._add_temporal_factors(combined_risks, weather_data)
        
        # Calculate confidence scores
        return self._add_confidence_scores(temporal_risks)

    def _prepare_features(self, weather_data: List<WeatherData],
                        location: Location) -> np.ndarray:
        """Prepare feature matrix for model input"""
        feature_matrix = np.array([w.to_feature_vector() for w in weather_data])
        location_features = np.array([
            location.latitude, location.longitude, location.elevation
        ])
        return np.hstack([feature_matrix, np.tile(location_features, (feature_matrix.shape[0], 1))])

    def _combine_risk_factors(self, predictions: Dict[str, Tuple[np.ndarray, float]],
                            location: Location) -> Dict[str, float]:
        """Combine multiple risk factors with location context"""
        combined_risks = {}
        for risk_type, (pred, uncertainty) in predictions.items():
            combined_risks[risk_type] = np.mean(pred) * (1 - uncertainty)
        return combined_risks

    def _add_temporal_factors(self, risks: Dict[str, float],
                            weather_data: List<WeatherData]) -> Dict[str, float]:
        """Add temporal evolution to risk scores"""
        for risk_type in risks.keys():
            risks[risk_type] *= self._calculate_temporal_factor(weather_data)
        return risks

    def _calculate_temporal_factor(self, weather_data: List<WeatherData]) -> float:
        """Calculate temporal factor based on weather data trends"""
        # Placeholder implementation
        return 1.0

    def _add_confidence_scores(self, risks: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Calculate confidence scores for each risk prediction"""
        return {
            risk_type: {
                'score': score,
                'confidence': self._calculate_confidence(score)
            }
            for risk_type, score in risks.items()
        }

    def _calculate_confidence(self, score: float) -> float:
        """Calculate confidence based on risk score"""
        if score >= self.thresholds.critical:
            return 0.9
        elif score >= self.thresholds.high:
            return 0.75
        elif score >= self.thresholds.moderate:
            return 0.5
        else:
            return 0.25
