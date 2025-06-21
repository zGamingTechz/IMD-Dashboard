from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import WeatherData
from datetime import datetime

add_data_bp = Blueprint('add_data', __name__)


@add_data_bp.route('/add-data', methods=['GET', 'POST'])
def add_data():
    if request.method == 'POST':
        try:
            # Extract form data
            form_data = request.form

            # Required fields validation
            required_fields = ['station_index', 'location', 'year', 'month', 'day']
            for field in required_fields:
                if not form_data.get(field):
                    flash(f'{field.replace("_", " ").title()} is required', 'error')
                    return render_template("add_data.html")

            # Date validation
            try:
                year = int(form_data.get('year'))
                month = int(form_data.get('month'))
                day = int(form_data.get('day'))

                # Check if date is valid
                datetime(year, month, day)

                # Check if date is not in future
                if datetime(year, month, day).date() > datetime.now().date():
                    if not form_data.get('force_submit'):
                        flash('Future date detected. Please verify the date or use "Add Anyway" to proceed.', 'error')
                        return render_template("add_data.html")

            except ValueError:
                flash('Invalid date combination', 'error')
                return render_template("add_data.html")


            # Helper function to safely convert to float
            def safe_float(value):
                if value and value.strip():
                    try:
                        return float(value)
                    except ValueError:
                        return None
                return None


            # Helper function to safely convert to int
            def safe_int(value):
                if value and value.strip():
                    try:
                        return int(value)
                    except ValueError:
                        return None
                return None


            # Create WeatherData object
            weather_data = WeatherData(
                # Required fields
                station_index=form_data.get('station_index').strip(),
                location=form_data.get('location').strip(),
                year=year,
                month=month,
                day=day,

                # Optional time field
                hour=safe_int(form_data.get('hour')),

                # Temperature measurements
                dry_bulb_temp=safe_float(form_data.get('dry_bulb_temp')),
                wet_bulb_temp=safe_float(form_data.get('wet_bulb_temp')),
                dew_point_temp=safe_float(form_data.get('dew_point_temp')),
                daily_min_temp=safe_float(form_data.get('daily_min_temp')),
                daily_mean_temp=safe_float(form_data.get('daily_mean_temp')),
                daily_max_temp=safe_float(form_data.get('daily_max_temp')),

                # Pressure measurements
                station_level_pressure=safe_float(form_data.get('station_level_pressure')),
                mean_sea_level_pressure=safe_float(form_data.get('mean_sea_level_pressure')),

                # Humidity and moisture
                relative_humidity=safe_float(form_data.get('relative_humidity')),
                vapor_pressure=safe_float(form_data.get('vapor_pressure')),

                # Wind measurements
                wind_direction=safe_float(form_data.get('wind_direction')),
                wind_speed=safe_float(form_data.get('wind_speed')),
                wind_gust=safe_float(form_data.get('wind_gust')),

                # Visibility and cloud cover
                visibility=safe_float(form_data.get('visibility')),
                total_cloud_cover=safe_float(form_data.get('total_cloud_cover')),
                low_cloud_amount=safe_float(form_data.get('low_cloud_amount')),
                medium_cloud_amount=safe_float(form_data.get('medium_cloud_amount')),
                high_cloud_amount=safe_float(form_data.get('high_cloud_amount')),
                cloud_type_low=safe_float(form_data.get('cloud_type_low')),
                cloud_type_high=safe_float(form_data.get('cloud_type_high')),

                # Weather phenomena
                rainfall=safe_float(form_data.get('rainfall')),
                evaporation=safe_float(form_data.get('evaporation')),
                sunshine_hours=safe_float(form_data.get('sunshine_hours'))
            )

            # Data validation (if not force submit)
            if not form_data.get('force_submit'):
                validation_warnings = validate_weather_data(weather_data)
                if validation_warnings:
                    for warning in validation_warnings:
                        flash(warning, 'warning')
                    return render_template("add_data.html")

            # Add to database
            db.session.add(weather_data)
            print("h")
            db.session.commit()

            flash(f'Weather data successfully added for {weather_data.location} on {weather_data.date}', 'success')
            return redirect(url_for('add_data.add_data'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding weather data: {str(e)}', 'error')
            return render_template("add_data.html")

    return render_template("add_data.html")


def validate_weather_data(weather_data):
    """
    Validate weather data against meteorological standards
    Return list of warning messages (I will update it later with sir)
    """
    warnings = []

    # Temperature validations
    if weather_data.dry_bulb_temp is not None:
        if weather_data.dry_bulb_temp < -50 or weather_data.dry_bulb_temp > 60:
            warnings.append(
                f'Dry bulb temperature ({weather_data.dry_bulb_temp}°C) is outside normal range (-50 to 60°C)')

    if weather_data.wet_bulb_temp is not None:
        if weather_data.wet_bulb_temp < -50 or weather_data.wet_bulb_temp > 50:
            warnings.append(
                f'Wet bulb temperature ({weather_data.wet_bulb_temp}°C) is outside normal range (-50 to 50°C)')

    if weather_data.dew_point_temp is not None:
        if weather_data.dew_point_temp < -60 or weather_data.dew_point_temp > 40:
            warnings.append(
                f'Dew point temperature ({weather_data.dew_point_temp}°C) is outside normal range (-60 to 40°C)')

    # Temperature logic validations
    if (weather_data.daily_min_temp is not None and
            weather_data.daily_max_temp is not None and
            weather_data.daily_min_temp > weather_data.daily_max_temp):
        warnings.append('Daily minimum temperature is higher than maximum temperature')

    if (weather_data.daily_mean_temp is not None and
            weather_data.daily_min_temp is not None and
            weather_data.daily_max_temp is not None):
        if (weather_data.daily_mean_temp < weather_data.daily_min_temp or
                weather_data.daily_mean_temp > weather_data.daily_max_temp):
            warnings.append('Daily mean temperature is outside the min-max range')

    if (weather_data.wet_bulb_temp is not None and
            weather_data.dry_bulb_temp is not None and
            weather_data.wet_bulb_temp > weather_data.dry_bulb_temp):
        warnings.append('Wet bulb temperature cannot be higher than dry bulb temperature')

    # Pressure validations
    if weather_data.station_level_pressure is not None:
        if weather_data.station_level_pressure < 800 or weather_data.station_level_pressure > 1100:
            warnings.append(
                f'Station level pressure ({weather_data.station_level_pressure} hPa) is outside normal range (800-1100 hPa)')

    if weather_data.mean_sea_level_pressure is not None:
        if weather_data.mean_sea_level_pressure < 950 or weather_data.mean_sea_level_pressure > 1050:
            warnings.append(
                f'Mean sea level pressure ({weather_data.mean_sea_level_pressure} hPa) is outside normal range (950-1050 hPa)')

    # Humidity validations
    if weather_data.relative_humidity is not None:
        if weather_data.relative_humidity < 0 or weather_data.relative_humidity > 100:
            warnings.append(f'Relative humidity ({weather_data.relative_humidity}%) is outside valid range (0-100%)')

    # Wind validations
    if weather_data.wind_direction is not None:
        if weather_data.wind_direction < 0 or weather_data.wind_direction > 360:
            warnings.append(f'Wind direction ({weather_data.wind_direction}°) is outside valid range (0-360°)')

    if weather_data.wind_speed is not None:
        if weather_data.wind_speed < 0 or weather_data.wind_speed > 200:
            warnings.append(f'Wind speed ({weather_data.wind_speed} m/s) is outside normal range (0-200 m/s)')

    # Cloud cover validations
    cloud_fields = [
        ('total_cloud_cover', weather_data.total_cloud_cover),
        ('low_cloud_amount', weather_data.low_cloud_amount),
        ('medium_cloud_amount', weather_data.medium_cloud_amount),
        ('high_cloud_amount', weather_data.high_cloud_amount)
    ]

    for field_name, value in cloud_fields:
        if value is not None and (value < 0 or value > 8):
            warnings.append(
                f'{field_name.replace("_", " ").title()} ({value} oktas) is outside valid range (0-8 oktas)')

    # Rainfall validation
    if weather_data.rainfall is not None:
        if weather_data.rainfall < 0 or weather_data.rainfall > 1000:
            warnings.append(f'Rainfall ({weather_data.rainfall} mm) is outside normal range (0-1000 mm)')

    # Sunshine hours validation
    if weather_data.sunshine_hours is not None:
        if weather_data.sunshine_hours < 0 or weather_data.sunshine_hours > 14:
            warnings.append(f'Sunshine hours ({weather_data.sunshine_hours}) is outside valid range (0-14 hours)')

    return warnings