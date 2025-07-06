from flask import Blueprint, request, jsonify, send_file, render_template
from models import WeatherData
from extensions import db
from datetime import datetime
import pandas as pd
import numpy as np
from io import BytesIO
import scipy.stats as stats


advanced_query_bp = Blueprint('advanced_query', __name__, url_prefix='/advanced-query')


@advanced_query_bp.route('/')
def advanced_query_page():
    # Get locations for dropdown
    locations = db.session.query(WeatherData.location.distinct()).filter(
        WeatherData.location.isnot(None),
        WeatherData.location != ''
    ).all()
    locations = [loc[0] for loc in locations if loc[0]]

    # Get date range
    date_range = db.session.query(
        db.func.min(WeatherData.date),
        db.func.max(WeatherData.date)
    ).first()

    return render_template('advanced_query.html',
                         locations=locations,
                         min_date=date_range[0],
                         max_date=date_range[1]
    )


@advanced_query_bp.route('/columns', methods=['GET'])
def get_available_columns():
    """Return list of all available columns in the database"""
    columns = [
        'date', 'location', 'station_index', 'year', 'month', 'day', 'hour',
        'station_level_pressure', 'mean_sea_level_pressure',
        'dry_bulb_temp', 'wet_bulb_temp', 'dew_point_temp',
        'daily_min_temp', 'daily_mean_temp', 'daily_max_temp',
        'relative_humidity', 'vapor_pressure',
        'wind_direction', 'wind_speed', 'wind_gust',
        'visibility', 'total_cloud_cover',
        'low_cloud_amount', 'medium_cloud_amount', 'high_cloud_amount',
        'cloud_type_low', 'cloud_type_high',
        'rainfall', 'evaporation', 'sunshine_hours'
    ]
    return jsonify({'columns': columns})


@advanced_query_bp.route('/query', methods=['POST'])
def advanced_query():
    try:
        data = request.json
        query = WeatherData.query

        # Apply standard filters
        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date >= start_date)
        if data.get('end_date'):
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date <= end_date)
        if data.get('location'):
            query = query.filter(WeatherData.location == data['location'])
        if data.get('min_temp_min'):
            query = query.filter(WeatherData.daily_min_temp >= float(data['min_temp_min']))
        if data.get('min_temp_max'):
            query = query.filter(WeatherData.daily_min_temp <= float(data['min_temp_max']))
        if data.get('max_temp_min'):
            query = query.filter(WeatherData.daily_max_temp >= float(data['max_temp_min']))
        if data.get('max_temp_max'):
            query = query.filter(WeatherData.daily_max_temp <= float(data['max_temp_max']))
        if data.get('rainfall_min'):
            query = query.filter(WeatherData.rainfall >= float(data['rainfall_min']))
        if data.get('rainfall_max'):
            query = query.filter(WeatherData.rainfall <= float(data['rainfall_max']))
        if data.get('humidity_min'):
            query = query.filter(WeatherData.relative_humidity >= float(data['humidity_min']))
        if data.get('humidity_max'):
            query = query.filter(WeatherData.relative_humidity <= float(data['humidity_max']))

        # Get selected columns or use all if not specified
        selected_columns = data.get('columns', [])

        # Execute query
        results = query.all()

        # Convert to DataFrame for easier manipulation
        df_data = []
        for record in results:
            df_data.append(record.to_dict())
        df = pd.DataFrame(df_data)

        # Filter columns if specified
        if selected_columns:
            # Ensure date is always included
            if 'date' not in selected_columns:
                selected_columns.insert(0, 'date')
            if 'location' not in selected_columns:
                selected_columns.insert(1, 'location')
            df = df[selected_columns]

        response_data = df.replace({np.nan: None}).to_dict(orient='records')

        return jsonify({
            'success': True,
            'data': response_data,
            'total': len(response_data)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@advanced_query_bp.route('/outliers', methods=['POST'])
def detect_outliers():
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

        # Get column to analyze for outliers
        column = data.get('column')
        if not column:
            return jsonify({'success': False, 'error': 'No column specified for outlier detection'}), 400

        # Get threshold (default to 3 standard deviations)
        threshold = float(data.get('threshold', 3))

        results = query.with_entities(
            getattr(WeatherData, column),
            WeatherData.date,
            WeatherData.location
        ).all()

        # Extract values
        values = [r[0] for r in results if r[0] is not None]
        if not values:
            return jsonify({'success': False, 'error': f'No valid data for column {column}'}), 400

        # Calculate z-scores
        z_scores = np.abs(stats.zscore(values))

        # Find outliers
        outliers = []
        for i, z in enumerate(z_scores):
            if z > threshold:
                outliers.append({
                    'date': results[i][1].strftime('%Y-%m-%d') if results[i][1] else None,
                    'location': results[i][2],
                    'value': values[i],
                    'z_score': z
                })

        for outlier in outliers:
            if isinstance(outlier['value'], float) and np.isnan(outlier['value']):
                outlier['value'] = None

        return jsonify({
            'success': True,
            'outliers': outliers,
            'column': column,
            'threshold': threshold,
            'total_outliers': len(outliers),
            'total_records': len(values)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@advanced_query_bp.route('/download', methods=['POST'])
def advanced_download():
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

        # Get selected columns or use all if not specified
        selected_columns = data.get('columns', [])

        results = query.all()

        # Convert to DataFrame
        df_data = []
        for record in results:
            df_data.append(record.to_dict())
        df = pd.DataFrame(df_data)

        # Filter columns if specified
        if selected_columns:
            # Ensure date and location are always included
            if 'date' not in selected_columns:
                selected_columns.insert(0, 'date')
            if 'location' not in selected_columns:
                selected_columns.insert(1, 'location')
            df = df[selected_columns]

        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Weather Data')
        output.seek(0)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"weather_data_advanced_{timestamp}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500