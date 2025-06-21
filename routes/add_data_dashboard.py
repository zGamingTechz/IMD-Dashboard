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
