import pandas as pd
from typing import List
from datetime import datetime
from ..Core.model_training import WeatherData, Location

class SampleDataLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load_sample_data(self) -> List<WeatherData]:
        """Load sample weather data from a CSV file"""
        df = pd.read_csv(self.file_path)
        weather_data = []
        for _, row in df.iterrows():
            weather_data.append(WeatherData(
                temperature=row['temperature'],
                precipitation=row['precipitation'],
                humidity=row['humidity'],
                wind_speed=row['wind_speed'],
                pressure=row['pressure'],
                timestamp=datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S'),
                uv_index=row.get('uv_index', 0.0),
                air_quality=row.get('air_quality', {})
            ))
        return weather_data

    def load_sample_location(self) -> Location:
        """Load sample location data from a CSV file"""
        df = pd.read_csv(self.file_path)
        first_row = df.iloc[0]
        return Location(
            latitude=first_row['latitude'],
            longitude=first_row['longitude'],
            elevation=first_row['elevation'],
            region=first_row['region']
        )
