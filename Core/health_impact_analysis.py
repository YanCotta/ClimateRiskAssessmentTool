from typing import Dict, List
from .model_training import Location

class HealthImpactAnalysis:
    def analyze_health_hazards(self, risks: Dict[str, float], location: Location) -> Dict[str, List[str]]:
        """
        Analyze potential health impacts based on risks and location.
        
        Future improvements:
        - Add demographic vulnerability factors
        - Include healthcare facility proximity
        - Add air quality impacts
        - Implement disease outbreak risk
        """
        health_hazards = {
            'immediate': [],
            'ongoing': [],
            'longterm': []
        }

        # Immediate health risks
        if risks.get('flood', 0) > 0.6:
            health_hazards['immediate'].extend([
                "Risk of waterborne diseases",
                "Injury from debris",
                "Water contamination exposure"
            ])

        # Ongoing health monitoring
        if risks.get('heatwave', 0) > 0.5:
            health_hazards['ongoing'].extend([
                "Heat exhaustion risk",
                "Cardiovascular strain",
                "Respiratory issues"
            ])

        # Long-term health considerations
        if risks.get('blackout', 0) > 0.7:
            health_hazards['longterm'].extend([
                "Medical equipment disruption",
                "Food safety concerns",
                "Mental health impacts"
            ])

        return health_hazards

class HealthImpactAnalysis:
    def __init__(self):
        self.vulnerability_factors = {
            'elderly_population': 1.5,
            'healthcare_access': 0.8,
            'air_quality_sensitivity': 1.2
        }
    
    def calculate_vulnerability_score(self, location: Location) -> float:
        """Calculate population vulnerability score"""
        score = 1.0
        for factor, weight in self.vulnerability_factors.items():
            if getattr(location, factor):
                score *= weight
        return score