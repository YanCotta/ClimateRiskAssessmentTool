from typing import Dict, List, Any
from .model_training import Location

class Recommendations:
    def get_recommendations(self, risks: Dict[str, float]) -> Dict[str, List[str]]:
        """Generate detailed, prioritized recommendations"""
        recommendations = {
            'critical': [],
            'important': [],
            'preparatory': []
        }
        
        # Critical actions (immediate response needed)
        if any(risk > 0.8 for risk in risks.values()):
            recommendations['critical'].append("Prepare for immediate evacuation")

        # Important actions (24-48 hour response)
        if risks.get('blackout', 0) > 0.6:
            recommendations['important'].append("Secure backup power supply")

        # Preparatory actions (longer-term preparation)
        recommendations['preparatory'].append("Create communication plan")

        return recommendations

    def get_emergency_recommendations(self, risks: Dict[str, float], 
                                health_hazards: Dict[str, List[str]],
                                location: Location) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate detailed emergency recommendations with priorities.
        
        Future improvements:
        - Add cost estimates
        - Include local resource locations
        - Add evacuation routes
        - Implement priority scoring
        """
        recommendations = {
            'critical': [],
            'important': [],
            'preparatory': []
        }
        
        # Critical actions (immediate response needed)
        if any(risk > 0.8 for risk in risks.values()):
            recommendations['critical'].append({
                'action': "Prepare for immediate evacuation",
                'priority': 1,
                'timeline': "Within 6 hours",
                'resources': ["Emergency kit", "Vehicle fuel", "Important documents"]
            })

        # Important actions (24-48 hour response)
        if risks.get('blackout', 0) > 0.6:
            recommendations['important'].append({
                'action': "Secure backup power supply",
                'priority': 2,
                'timeline': "Within 24 hours",
                'resources': ["Generator", "Batteries", "Fuel supply"]
            })

        # Preparatory actions (longer-term preparation)
        recommendations['preparatory'].append({
            'action': "Create communication plan",
            'priority': 3,
            'timeline': "Within 72 hours",
            'resources': ["Emergency contacts", "Meeting locations", "Communication devices"]
        })

        return recommendations
