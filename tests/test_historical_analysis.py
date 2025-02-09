from unittest import TestCase
import pandas as pd
import numpy as np
from Core.historical_analysis import HistoricalAnalysis

class TestHistoricalAnalysis(TestCase):
    def setUp(self):
        self.analyzer = HistoricalAnalysis(lookback_years=5)
        self.sample_data = pd.DataFrame({
            'temperature': np.random.normal(20, 5, 1825),  # 5 years of daily data
            'precipitation': np.random.exponential(1, 1825),
            'wind_speed': np.random.rayleigh(2, 1825)
        })
        
    def test_calculate_trends(self):
        trends = self.analyzer._calculate_trends(self.sample_data)
        self.assertIn('temperature', trends)
        self.assertIn('slope', trends['temperature'])