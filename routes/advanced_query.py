from flask import Blueprint, jsonify, request, send_file, render_template
from models import WeatherData
from extensions import db
from datetime import datetime
import pandas as pd
import numpy as np
from io import BytesIO
from sqlalchemy import or_, and_

advanced_query_bp = Blueprint('advanced_query', __name__, url_prefix='/advanced-query')


@advanced_query_bp.route('/columns')
def get_columns():
    columns = [
        'date', 'location', 'station_index',
        'year', 'month', 'day', 'hour',
        'station_level_pressure', 'mean_sea_level_pressure',
        'dry_bulb_temp', 'wet_bulb_temp', 'dew_point_temp',
        'daily_min_temp', 'daily_mean_temp', 'daily_max_temp',
        'relative_humidity', 'vapor_pressure',
        'wind_direction', 'wind_speed', 'wind_gust',
        'visibility',
        'total_cloud_cover', 'low_cloud_amount', 'medium_cloud_amount',
        'high_cloud_amount', 'cloud_type_low', 'cloud_type_high',
        'rainfall', 'evaporation', 'sunshine_hours'
    ]
    return jsonify({'columns': columns})


@advanced_query_bp.route('/query', methods=['POST'])
def advanced_query():
    try:
        data = request.json
        query = WeatherData.query

        # --- Filters ---
        if data.get('start_date'):
            try:
                start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
                query = query.filter(WeatherData.date >= start_date)
            except:
                pass
        if data.get('end_date'):
            try:
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
                query = query.filter(WeatherData.date <= end_date)
            except:
                pass

        # Location filter (multi-select support)
        locations = data.get('location')
        if locations:
            if isinstance(locations, list):
                query = query.filter(WeatherData.location.in_(locations))
            else:
                query = query.filter(WeatherData.location == locations)

        def get_float(value):
            try:
                return float(value) if value not in [None, '', 'NaN'] else None
            except:
                return None

        def range_filter(column, min_key, max_key):
            min_val, max_val = get_float(data.get(min_key)), get_float(data.get(max_key))
            if min_val is not None:
                query = query.filter(getattr(WeatherData, column) >= min_val)
            if max_val is not None:
                query = query.filter(getattr(WeatherData, column) <= max_val)

        range_filter('daily_min_temp', 'min_temp_min', 'min_temp_max')
        range_filter('daily_max_temp', 'max_temp_min', 'max_temp_max')
        range_filter('relative_humidity', 'humidity_min', 'humidity_max')
        range_filter('rainfall', 'rainfall_min', 'rainfall_max')
        range_filter('wind_speed', 'wind_speed_min', 'wind_speed_max')
        range_filter('mean_sea_level_pressure', 'pressure_min', 'pressure_max')
        range_filter('total_cloud_cover', 'cloud_cover_min', 'cloud_cover_max')

        # Time of day filtering
        time_map = {
            'morning': (6, 12),
            'afternoon': (12, 18),
            'evening': (18, 24),
            'night': (0, 6),
        }
        time_filter = data.get('time_of_day')
        if time_filter in time_map:
            start, end = time_map[time_filter]
            if time_filter == 'night':
                query = query.filter(or_(WeatherData.hour >= 0, WeatherData.hour < 6))
            else:
                query = query.filter(and_(WeatherData.hour >= start, WeatherData.hour < end))

        # Pagination
        try:
            page = int(data.get('page', 1))
        except:
            page = 1
        try:
            per_page = int(data.get('per_page', 100))
        except:
            per_page = 100

        results = query.order_by(WeatherData.date.desc()).paginate(page=page, per_page=per_page, error_out=False)

        # Output with selected columns
        selected_columns = data.get('columns') or ['date', 'location', 'station_index', 'daily_max_temp', 'daily_min_temp', 'rainfall']
        response_data = []
        for record in results.items:
            row = record.to_dict()
            filtered = {col: ("N/A" if row.get(col) in [None, '', 'NaN'] else row.get(col)) for col in selected_columns}
            response_data.append(filtered)

        return jsonify({
            'success': True,
            'data': response_data,
            'total': results.total,
            'pages': results.pages,
            'current_page': results.page
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@advanced_query_bp.route('/outliers', methods=['POST'])
def detect_outliers():
    try:
        data = request.json
        column = data.get('column')
        threshold = float(data.get('threshold', 3))
        location = data.get('location')

        if not column:
            return jsonify({'success': False, 'error': 'Column is required'})

        # Build base query
        query = WeatherData.query.filter(getattr(WeatherData, column).isnot(None))

        # Apply location filter if specified
        if location:
            query = query.filter(WeatherData.location == location)

        # Apply date filters if specified
        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date >= start_date)
        if data.get('end_date'):
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date <= end_date)

        # Get all records that match filters
        records = query.all()
        total_records = len(records)

        if total_records == 0:
            return jsonify({'success': True, 'outliers': [], 'total_records': 0, 'column': column})

        # Calculate mean and standard deviation
        values = [getattr(record, column) for record in records]
        mean = np.mean(values)
        std = np.std(values)

        # Find outliers
        outliers = []
        for record in records:
            value = getattr(record, column)
            if value is None:
                continue

            z_score = (value - mean) / std if std != 0 else 0
            if abs(z_score) > threshold:
                outliers.append({
                    'date': record.date.strftime('%Y-%m-%d') if record.date else None,
                    'location': record.location,
                    'value': value,
                    'z_score': z_score,
                    'mean': mean,
                    'std': std
                })

        return jsonify({
            'success': True,
            'outliers': outliers,
            'total_records': total_records,
            'column': column,
            'mean': mean,
            'std': std
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@advanced_query_bp.route('/download', methods=['POST'])
def download_advanced_data():
    try:
        data = request.json
        query = WeatherData.query

        # Apply filters
        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date >= start_date)
        if data.get('end_date'):
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date <= end_date)
        if data.get('location'):
            query = query.filter(WeatherData.location == data['location'])

        # Column selection
        selected_columns = data.get('columns', [])
        if not selected_columns:
            selected_columns = ['date', 'location', 'station_index', 'daily_max_temp', 'daily_min_temp', 'rainfall']

        # Temperature filters
        if data.get('min_temp_min'):
            query = query.filter(WeatherData.daily_min_temp >= float(data['min_temp_min']))
        if data.get('min_temp_max'):
            query = query.filter(WeatherData.daily_min_temp <= float(data['min_temp_max']))
        if data.get('max_temp_min'):
            query = query.filter(WeatherData.daily_max_temp >= float(data['max_temp_min']))
        if data.get('max_temp_max'):
            query = query.filter(WeatherData.daily_max_temp <= float(data['max_temp_max']))

        # Rainfall filter
        if data.get('rainfall_min'):
            query = query.filter(WeatherData.rainfall >= float(data['rainfall_min']))
        if data.get('rainfall_max'):
            query = query.filter(WeatherData.rainfall <= float(data['rainfall_max']))

        # Get results
        results = query.order_by(WeatherData.date.desc()).all()

        # Create DataFrame with selected columns
        df_data = []
        for record in results:
            record_dict = record.to_dict()
            filtered_dict = {k: v for k, v in record_dict.items() if k in selected_columns}
            df_data.append(filtered_dict)

        df = pd.DataFrame(df_data)

        # Rename columns for better readability
        column_names = {
            'station_index': 'Station Index',
            'location': 'Location',
            'date': 'Date',
            'year': 'Year',
            'month': 'Month',
            'day': 'Day',
            'hour': 'Hour',
            'station_level_pressure': 'Station Pressure (hPa)',
            'mean_sea_level_pressure': 'Sea Level Pressure (hPa)',
            'dry_bulb_temp': 'Dry Bulb Temp (°C)',
            'wet_bulb_temp': 'Wet Bulb Temp (°C)',
            'dew_point_temp': 'Dew Point Temp (°C)',
            'daily_min_temp': 'Min Temp (°C)',
            'daily_mean_temp': 'Mean Temp (°C)',
            'daily_max_temp': 'Max Temp (°C)',
            'relative_humidity': 'Relative Humidity (%)',
            'vapor_pressure': 'Vapor Pressure (hPa)',
            'wind_direction': 'Wind Direction (°)',
            'wind_speed': 'Wind Speed (m/s)',
            'wind_gust': 'Wind Gust (m/s)',
            'visibility': 'Visibility (km)',
            'total_cloud_cover': 'Total Cloud Cover',
            'low_cloud_amount': 'Low Cloud Amount',
            'medium_cloud_amount': 'Medium Cloud Amount',
            'high_cloud_amount': 'High Cloud Amount',
            'cloud_type_low': 'Low Cloud Type',
            'cloud_type_high': 'High Cloud Type',
            'rainfall': 'Rainfall (mm)',
            'evaporation': 'Evaporation (mm)',
            'sunshine_hours': 'Sunshine Hours'
        }

        df.rename(columns=column_names, inplace=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Weather Data')
        output.seek(0)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"advanced_weather_data_{timestamp}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@advanced_query_bp.route('/advanced')
def advanced_query_page():
    locations = db.session.query(WeatherData.location.distinct()).filter(
        WeatherData.location.isnot(None),
        WeatherData.location != ''
    ).all()
    locations = [loc[0] for loc in locations if loc[0]]

    date_range = db.session.query(
        db.func.min(WeatherData.date),
        db.func.max(WeatherData.date)
    ).first()

    return render_template('advanced_dashboard.html',
                           locations=locations,
                           min_date=date_range[0],
                           max_date=date_range[1])