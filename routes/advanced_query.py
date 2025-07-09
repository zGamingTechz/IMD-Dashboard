from flask import Blueprint, jsonify, request, send_file, render_template
from models import WeatherData
from extensions import db
from datetime import datetime
import pandas as pd
import numpy as np
from io import BytesIO
from sqlalchemy import or_, and_
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os

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

        # Location filter (multi-select support) - FIXED
        locations = data.get('location')
        if locations:
            if isinstance(locations, list) and len(locations) > 0:
                # Filter out empty strings and None values
                valid_locations = [loc for loc in locations if loc and loc.strip()]
                if valid_locations:
                    query = query.filter(WeatherData.location.in_(valid_locations))
            elif isinstance(locations, str) and locations.strip():
                query = query.filter(WeatherData.location == locations.strip())

        def get_float(value):
            try:
                return float(value) if value not in [None, '', 'NaN'] else None
            except:
                return None

        # Fixed range_filter function to properly handle query modifications
        def apply_range_filter(column, min_key, max_key):
            nonlocal query
            min_val, max_val = get_float(data.get(min_key)), get_float(data.get(max_key))
            if min_val is not None:
                query = query.filter(getattr(WeatherData, column) >= min_val)
            if max_val is not None:
                query = query.filter(getattr(WeatherData, column) <= max_val)

        apply_range_filter('daily_min_temp', 'min_temp_min', 'min_temp_max')
        apply_range_filter('daily_max_temp', 'max_temp_min', 'max_temp_max')
        apply_range_filter('relative_humidity', 'humidity_min', 'humidity_max')
        apply_range_filter('rainfall', 'rainfall_min', 'rainfall_max')
        apply_range_filter('wind_speed', 'wind_speed_min', 'wind_speed_max')
        apply_range_filter('mean_sea_level_pressure', 'pressure_min', 'pressure_max')
        apply_range_filter('total_cloud_cover', 'cloud_cover_min', 'cloud_cover_max')

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
        selected_columns = data.get('columns') or ['date', 'location', 'station_index', 'daily_max_temp',
                                                   'daily_min_temp', 'rainfall']
        response_data = []
        for record in results.items:
            row = record.to_dict()
            filtered = {col: ("N/A" if row.get(col) in [None, '', 'NaN'] else row.get(col)) for col in selected_columns}
            response_data.append(filtered)

        # Calculate summary statistics for dry_bulb_temp - FIXED
        summary_stats = {}
        if results.items:
            # Get dry_bulb_temp values that are not None
            dry_bulb_temps = [getattr(record, 'dry_bulb_temp') for record in results.items
                              if getattr(record, 'dry_bulb_temp') is not None]

            if dry_bulb_temps:
                summary_stats['max_temp'] = max(dry_bulb_temps)
                summary_stats['min_temp'] = min(dry_bulb_temps)
            else:
                summary_stats['max_temp'] = None
                summary_stats['min_temp'] = None

            # Get max rainfall
            rainfalls = [getattr(record, 'rainfall') for record in results.items
                         if getattr(record, 'rainfall') is not None and getattr(record, 'rainfall') > 0]
            summary_stats['max_rainfall'] = max(rainfalls) if rainfalls else None
        else:
            summary_stats = {'max_temp': None, 'min_temp': None, 'max_rainfall': None}

        return jsonify({
            'success': True,
            'data': response_data,
            'total': results.total,
            'pages': results.pages,
            'current_page': results.page,
            'summary': summary_stats
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@advanced_query_bp.route('/outliers', methods=['POST'])
def detect_outliers():
    try:
        data = request.json
        column = data.get('column')
        threshold = float(data.get('threshold', 3))
        locations = data.get('location')  # Can be single location or list

        if not column:
            return jsonify({'success': False, 'error': 'Column is required'})

        # Build base query
        query = WeatherData.query.filter(getattr(WeatherData, column).isnot(None))

        # Apply location filter if specified - FIXED for multi-select
        if locations:
            if isinstance(locations, list) and len(locations) > 0:
                valid_locations = [loc for loc in locations if loc and loc.strip()]
                if valid_locations:
                    query = query.filter(WeatherData.location.in_(valid_locations))
            elif isinstance(locations, str) and locations.strip():
                query = query.filter(WeatherData.location == locations.strip())

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

        # Location filter - FIXED for multi-select
        locations = data.get('location')
        if locations:
            if isinstance(locations, list) and len(locations) > 0:
                valid_locations = [loc for loc in locations if loc and loc.strip()]
                if valid_locations:
                    query = query.filter(WeatherData.location.in_(valid_locations))
            elif isinstance(locations, str) and locations.strip():
                query = query.filter(WeatherData.location == locations.strip())

        # Column selection
        selected_columns = data.get('columns', [])
        if not selected_columns:
            selected_columns = ['date', 'location', 'station_index', 'daily_max_temp', 'daily_min_temp', 'rainfall']

        # Apply other filters
        def apply_filter(column, min_key, max_key):
            nonlocal query
            if data.get(min_key):
                try:
                    query = query.filter(getattr(WeatherData, column) >= float(data[min_key]))
                except:
                    pass
            if data.get(max_key):
                try:
                    query = query.filter(getattr(WeatherData, column) <= float(data[max_key]))
                except:
                    pass

        apply_filter('daily_min_temp', 'min_temp_min', 'min_temp_max')
        apply_filter('daily_max_temp', 'max_temp_min', 'max_temp_max')
        apply_filter('rainfall', 'rainfall_min', 'rainfall_max')
        apply_filter('relative_humidity', 'humidity_min', 'humidity_max')
        apply_filter('wind_speed', 'wind_speed_min', 'wind_speed_max')
        apply_filter('mean_sea_level_pressure', 'pressure_min', 'pressure_max')
        apply_filter('total_cloud_cover', 'cloud_cover_min', 'cloud_cover_max')

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


@advanced_query_bp.route('/download-pdf', methods=['POST'])
def download_pdf():
    try:
        data = request.json
        query = WeatherData.query

        # Filters
        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date >= start_date)
        if data.get('end_date'):
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date <= end_date)

        # Location filter - multi-select support
        locations = data.get('location')
        if locations:
            if isinstance(locations, list) and len(locations) > 0:
                valid_locations = [loc for loc in locations if loc and loc.strip()]
                if valid_locations:
                    query = query.filter(WeatherData.location.in_(valid_locations))
            elif isinstance(locations, str) and locations.strip():
                query = query.filter(WeatherData.location == locations.strip())

        # Column selection
        selected_columns = data.get('columns', [])
        if not selected_columns:
            selected_columns = ['date', 'location', 'station_index', 'daily_max_temp', 'daily_min_temp', 'rainfall']

        # Other filters
        def apply_filter(column, min_key, max_key):
            nonlocal query
            if data.get(min_key):
                try:
                    query = query.filter(getattr(WeatherData, column) >= float(data[min_key]))
                except:
                    pass
            if data.get(max_key):
                try:
                    query = query.filter(getattr(WeatherData, column) <= float(data[max_key]))
                except:
                    pass

        apply_filter('daily_min_temp', 'min_temp_min', 'min_temp_max')
        apply_filter('daily_max_temp', 'max_temp_min', 'max_temp_max')
        apply_filter('rainfall', 'rainfall_min', 'rainfall_max')
        apply_filter('relative_humidity', 'humidity_min', 'humidity_max')
        apply_filter('wind_speed', 'wind_speed_min', 'wind_speed_max')
        apply_filter('mean_sea_level_pressure', 'pressure_min', 'pressure_max')
        apply_filter('total_cloud_cover', 'cloud_cover_min', 'cloud_cover_max')

        results = query.order_by(WeatherData.date.desc()).all()

        if not results:
            return jsonify({'success': False, 'error': 'No data found for the specified criteria'}), 400

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

        # Container for the 'Flowable' objects
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER
        )

        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_LEFT
        )

        hindi_style = ParagraphStyle(
            'Hindi',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT
        )

        # Header Section
        header_data = [
            ['Indian Meteorological Department<br/>Jaipur', '', 'भारतीय मौसम विभाग<br/>जयपुर']
        ]

        header_table = Table(header_data, colWidths=[2.5 * inch, 2 * inch, 2.5 * inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 12))

        # IMD Logo
        try:
            logo_path = os.path.join('static', 'IMD Logo.png')
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=1 * inch, height=1 * inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            else:
                # Fallback if logo not found
                logo_placeholder = Paragraph("IMD LOGO", title_style)
                elements.append(logo_placeholder)
        except:
            logo_placeholder = Paragraph("IMD LOGO", title_style)
            elements.append(logo_placeholder)

        elements.append(Spacer(1, 20))

        # Title
        title = Paragraph("Weather Data Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))

        # Basic Information
        info_text = f"""
        <b>Report Generation Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Data Period:</b> {data.get('start_date', 'Not specified')} to {data.get('end_date', 'Not specified')}<br/>
        <b>Total Records:</b> {len(results)}<br/>
        <b>Locations:</b> {', '.join(locations) if locations else 'All locations'}<br/>
        <b>Selected Parameters:</b> {', '.join(selected_columns)}
        """

        info_para = Paragraph(info_text, header_style)
        elements.append(info_para)
        elements.append(Spacer(1, 20))

        # Prepare data for table
        # Column name mapping for better readability
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

        # Table headers
        headers = [column_names.get(col, col) for col in selected_columns]

        # Table data
        table_data = [headers]

        for record in results:
            record_dict = record.to_dict()
            row = []
            for col in selected_columns:
                value = record_dict.get(col)
                if value is None or value == '':
                    row.append('N/A')
                elif isinstance(value, float):
                    row.append(f"{value:.2f}")
                else:
                    row.append(str(value))
            table_data.append(row)

        # Adjust column widths based on number of columns
        num_columns = len(selected_columns)
        if num_columns <= 4:
            col_width = 1.5 * inch
        elif num_columns <= 6:
            col_width = 1.2 * inch
        else:
            col_width = 0.9 * inch

        data_table = Table(table_data, colWidths=[col_width] * num_columns)

        # Styling the table
        data_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),

            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),
        ]))

        elements.append(data_table)

        doc.build(elements)

        pdf_value = buffer.getvalue()
        buffer.close()

        output = BytesIO(pdf_value)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"weather_report_{timestamp}.pdf"

        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500