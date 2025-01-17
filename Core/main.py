import logging
from .model_training import MLModelManager, WeatherData, Location
from .risk_scoring import RiskScoring
from .recommendations import Recommendations
from .visualization import Visualization
from .data_integration import DataIntegration, APIConfig
from .health_impact_analysis import HealthImpactAnalysis
from .historical_analysis import HistoricalAnalysis

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Enhanced main execution with better error handling.
    
    Future improvements:
    - Add CLI interface
    - Add configuration file support
    - Add batch processing
    - Implement progress tracking
    """
    try:
        # Initialize components
        api_config = {
            'weather_api': APIConfig(
                base_url='https://api.weather.com',
                api_key='your_api_key',
                endpoints={'forecast': '/v3/wx/forecast/daily/5day'}
            )
        }
        data_integration = DataIntegration(api_config)
        model_manager = MLModelManager()
        risk_scoring = RiskScoring(model_manager)
        recommendations = Recommendations()
        visualization = Visualization()
        health_impact_analysis = HealthImpactAnalysis()
        historical_analysis = HistoricalAnalysis()

        # Example location
        location = Location(latitude=40.7128, longitude=-74.0060, elevation=10, region='NY')

        # Fetch weather data
        weather_data = data_integration.fetch_weather_data(location)

        # Analyze risks
        risks = risk_scoring.calculate_risk_scores(location, weather_data)

        # Get recommendations
        recs = recommendations.get_recommendations(risks)

        # Analyze health impacts
        health_hazards = health_impact_analysis.analyze_health_hazards(risks, location)

        # Create visualization dashboard
        dashboard = visualization.create_dashboard(risks, weather_data, location)

        # Export dashboard
        visualization.export_dashboard(dashboard)

    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()
