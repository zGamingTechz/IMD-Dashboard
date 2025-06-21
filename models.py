from extensions import db
from datetime import datetime

# Database Model
class WeatherData(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Identification and Time columns
    station_index = db.Column(db.String(20), index=True)  # INDEX column
    location = db.Column(db.String(20), index=True) # Locations (from index)
    year = db.Column(db.Integer, nullable=False, index=True)  # YEAR
    month = db.Column(db.Integer, nullable=False, index=True)  # MN
    day = db.Column(db.Integer, nullable=False)  # DT
    hour = db.Column(db.Integer)  # HR

    # Pressure columns
    station_level_pressure = db.Column(db.Float)  # ..SLP
    mean_sea_level_pressure = db.Column(db.Float)  # ..MSLP

    # Temperature columns
    dry_bulb_temp = db.Column(db.Float)  # ..DBT - Air temperature
    wet_bulb_temp = db.Column(db.Float)  # ..WBT - Temperature considering humidity
    dew_point_temp = db.Column(db.Float)  # ..DPT - Moisture content indicator

    # Humidity and moisture
    relative_humidity = db.Column(db.Float)  # .RH - Relative humidity percentage
    vapor_pressure = db.Column(db.Float)  # ..VP - Atmospheric moisture

    # Wind data
    wind_direction = db.Column(db.Float)  # DD - Wind direction in degrees
    wind_speed = db.Column(db.Float)  # FFF - Wind speed
    wind_gust = db.Column(db.Float)  # AW - Wind gusts or average wind

    # Visibility
    visibility = db.Column(db.Float)  # VV - Visibility in km or m

    # Cloud cover data
    total_cloud_cover = db.Column(db.Float)  # C - Total cloud cover
    low_cloud_amount = db.Column(db.Float)  # l A - Low cloud amount
    medium_cloud_amount = db.Column(db.Float)  # Cm - Medium cloud amount
    high_cloud_amount = db.Column(db.Float)  # Ch - High cloud amount
    cloud_type_low = db.Column(db.Float)  # A - Cloud type (low)
    cloud_type_high = db.Column(db.Float)  # A.1 - Cloud type (high)

    # Daily temperature extremes
    daily_min_temp = db.Column(db.Float)  # Dl - Daily minimum temperature
    daily_mean_temp = db.Column(db.Float)  # Dm - Daily mean temperature
    daily_max_temp = db.Column(db.Float)  # Dh - Daily maximum temperature

    # Weather phenomena (Corrupted in current data)
    rainfall = db.Column(db.Float)
    evaporation = db.Column(db.Float)
    sunshine_hours = db.Column(db.Float)

    # Composite date
    date = db.Column(db.Date, index=True)  # Computed from year, month, day

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Automatically create date from year, month, day if they exist
        if self.year and self.month and self.day:
            try:
                self.date = datetime(self.year, self.month, self.day).date()
            except ValueError:
                self.date = None

    def to_dict(self):
        return {
            'id': self.id,
            'location': self.location,
            'station_index': self.station_index,
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'hour': self.hour,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,

            # Pressure
            'station_level_pressure': self.station_level_pressure,
            'mean_sea_level_pressure': self.mean_sea_level_pressure,

            # Temperature
            'dry_bulb_temp': self.dry_bulb_temp,
            'wet_bulb_temp': self.wet_bulb_temp,
            'dew_point_temp': self.dew_point_temp,
            'daily_min_temp': self.daily_min_temp,
            'daily_mean_temp': self.daily_mean_temp,
            'daily_max_temp': self.daily_max_temp,

            # Humidity and moisture
            'relative_humidity': self.relative_humidity,
            'vapor_pressure': self.vapor_pressure,

            # Wind
            'wind_direction': self.wind_direction,
            'wind_speed': self.wind_speed,
            'wind_gust': self.wind_gust,

            # Visibility
            'visibility': self.visibility,

            # Cloud cover
            'total_cloud_cover': self.total_cloud_cover,
            'low_cloud_amount': self.low_cloud_amount,
            'medium_cloud_amount': self.medium_cloud_amount,
            'high_cloud_amount': self.high_cloud_amount,
            'cloud_type_low': self.cloud_type_low,
            'cloud_type_high': self.cloud_type_high,

            # Weather phenomena
            'rainfall': self.rainfall,
            'evaporation': self.evaporation,
            'sunshine_hours': self.sunshine_hours
        }

    def __repr__(self):
        return f'<WeatherData {self.station_index} {self.date}>'
