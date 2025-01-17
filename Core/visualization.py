import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from .model_training import WeatherData, Location

class Visualization:
    def __init__(self, theme: str = 'plotly_dark'):
        self.theme = theme
        self.color_scales = {
            'risk': 'RdYlGn_r',
            'temperature': 'RdBu_r',
            'precipitation': 'Blues'
        }

    def create_dashboard(self, risks: Dict[str, float],
                        weather_data: List<WeatherData],
                        location: Location) -> Dict[str, go.Figure]:
        """Create comprehensive interactive dashboard"""
        return {
            'risk_assessment': self._create_risk_heatmap(risks),
            'weather_forecast': self._create_weather_forecast(weather_data),
            'threat_analysis': self._create_threat_analysis(risks, weather_data),
            'location_map': self._create_location_map(location, risks)
        }

    def _create_risk_heatmap(self, risks: Dict[str, float]) -> go.Figure:
        """Create interactive risk heatmap with confidence intervals"""
        risk_values = [v for k, v in risks.items() if not k.endswith('_confidence')]
        confidence_values = [v for k, v in risks.items() if k.endswith('_confidence')]
        
        fig = go.Figure(data=go.Heatmap(
            z=[risk_values],
            text=[[f"{v:.2f}" for v in risk_values]],
            colorscale=self.color_scales['risk'],
            showscale=True,
            customdata=[[f"Confidence: {c:.2f}" for c in confidence_values]],
            hovertemplate="Risk Level: %{z:.2f}<br>%{customdata}<extra></extra>"
        ))
        
        fig.update_layout(
            title="Risk Assessment Heatmap",
            xaxis_title="Risk Categories",
            yaxis_title="Risk Level",
            template=self.theme
        )
        
        return fig

    def _create_weather_forecast(self, weather_data: List<WeatherData]) -> go.Figure:
        """Create multi-parameter weather forecast visualization"""
        fig = make_subplots(rows=2, cols=2,
                        subplot_titles=("Temperature", "Precipitation",
                                        "Wind Speed", "Pressure"))
        
        timestamps = [w.timestamp for w in weather_data]
        
        # Temperature subplot
        fig.add_trace(
            go.Scatter(x=timestamps, y=[w.temperature for w in weather_data],
                    name="Temperature", line=dict(color="red")),
            row=1, col=1
        )
        
        # Precipitation subplot
        fig.add_trace(
            go.Scatter(x=timestamps, y=[w.precipitation for w in weather_data],
                    name="Precipitation", line=dict(color="blue")),
            row=1, col=2
        )
        
        # Wind Speed subplot
        fig.add_trace(
            go.Scatter(x=timestamps, y=[w.wind_speed for w in weather_data],
                    name="Wind Speed", line=dict(color="green")),
            row=2, col=1
        )
        
        # Pressure subplot
        fig.add_trace(
            go.Scatter(x=timestamps, y=[w.pressure for w in weather_data],
                    name="Pressure", line=dict(color="purple")),
            row=2, col=2
        )
        
        fig.update_layout(height=800, template=self.theme)
        return fig

    def _create_threat_analysis(self, risks: Dict[str, float],
                            weather_data: List<WeatherData]) -> go.Figure:
        """Create threat analysis visualization with time evolution"""
        # Implementation for threat analysis visualization
        pass

    def _create_location_map(self, location: Location,
                        risks: Dict[str, float]) -> go.Figure:
        """Create interactive map with risk overlay"""
        # Implementation for location-based visualization
        pass

    def export_dashboard(self, dashboard: Dict[str, go.Figure],
                        format: str = 'html') -> None:
        """Export dashboard in various formats"""
        for name, fig in dashboard.items():
            if format == 'html':
                fig.write_html(f"dashboard_{name}.html")
            elif format == 'png':
                fig.write_image(f"dashboard_{name}.png")
