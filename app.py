from flask import Flask, render_template, request, jsonify, send_file, redirect
from routes.add_data_dashboard import add_data_bp
import pandas as pd
import os
from datetime import datetime
import matplotlib
# To use non-interactive backend
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64
from werkzeug.utils import secure_filename
import shutil
import re
from extensions import db


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = "IMD_Jaipur"


# Initializing db from external file then importing
db.init_app(app)
from models import WeatherData


ALLOWED_EXTENSIONS = {'.xls', '.xlsx', '.csv'}

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register the new route
app.register_blueprint(add_data_bp)

stations = {
    "42343": "Ajmer",
    "42447": "Bhilwara",
    "42346": "Vanasthali",
    "42255": "Alwar",
    "42348": "Jaipur",
    "42174": "Pilani",
    "42249": "Sikar",
    "42452": "Kota",
    "42546": "Chittorgarh",
    "42542": "Dabok",
    "42435": "Barmer",
    "42441": "E.R. Road (Pali)",
    "42328": "Jaisalmer",
    "42339": "Jodhpur",
    "42540": "Mt. Abu",
    "42237": "Phalodi",
    "42165": "Bikaner",
    "42170": "Churu",
    "42123": "S. Ganganagar",
    "Will add more": 0
}


def load_excel_data(file_path):
    try:
        df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)

        # Column mappings
        column_mapping = {
            'INDEX': 'station_index',
            'YEAR': 'year',
            'MN': 'month',
            'HR': 'hour',
            'DT': 'day',
            '...SLP': 'station_level_pressure',
            '..MSLP': 'mean_sea_level_pressure',
            '..DBT': 'dry_bulb_temp',
            '..WBT': 'wet_bulb_temp',
            '..DPT': 'dew_point_temp',
            '.RH': 'relative_humidity',
            '..VP': 'vapor_pressure',
            'DD': 'wind_direction',
            'FFF': 'wind_speed',
            'AW': 'wind_gust',
            'VV': 'visibility',
            'C': 'total_cloud_cover',
            'l A': 'low_cloud_amount',
            'Cm': 'medium_cloud_amount',
            'A': 'cloud_type_low',
            'Ch': 'high_cloud_amount',
            'A.1': 'cloud_type_high',
            'Dl': 'daily_min_temp',
            'Dm': 'daily_mean_temp',
            'Dh': 'daily_max_temp'
        }

        existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
        df.rename(columns=existing_columns, inplace=True)

        # Handling the corrupted column
        corrupted_col_name = None
        for col in df.columns:
            if 'TC h c a Ht' in str(col) or len(str(col)) > 50:
                corrupted_col_name = col
                break

        imported = 0
        skipped = 0
        errors = 0
        filtered_station_index = 0

        for i, row in df.iterrows():
            try:
                # Skipping rows with missing essential data
                if pd.isna(row.get('year')) or pd.isna(row.get('month')) or pd.isna(row.get('day')):
                    skipped += 1
                    continue

                # Get station index and convert to string
                station_index_raw = safe_string(row.get('station_index'))

                # Skipping records where station index starts with '1'
                if station_index_raw and station_index_raw.startswith('1'):
                    filtered_station_index += 1
                    continue

                # Parsing the corrupted column for rainfall and other data
                rainfall_val = None
                evaporation_val = None
                sunshine_val = None

                if corrupted_col_name and not pd.isna(row.get(corrupted_col_name)):
                    corrupted_data = str(row[corrupted_col_name])
                    rainfall_match = re.search(r'(\d{3}\.\d)', corrupted_data)
                    if rainfall_match:
                        rainfall_val = safe_float(rainfall_match.group(1))

                # Creating new weather data record
                new_data = {
                    'station_index': station_index_raw,
                    'location': stations.get(station_index_raw, 'Unknown'),
                    'year': safe_int(row.get('year')),
                    'month': safe_int(row.get('month')),
                    'day': safe_int(row.get('day')),
                    'hour': safe_int_allow_zero(row.get('hour')),

                    # Pressure data
                    'station_level_pressure': safe_float(row.get('station_level_pressure')),
                    'mean_sea_level_pressure': safe_float(row.get('mean_sea_level_pressure')),

                    # Temperature data
                    'dry_bulb_temp': safe_float(row.get('dry_bulb_temp')),
                    'wet_bulb_temp': safe_float(row.get('wet_bulb_temp')),
                    'dew_point_temp': safe_float(row.get('dew_point_temp')),
                    'daily_min_temp': safe_float(row.get('daily_min_temp')),
                    'daily_mean_temp': safe_float(row.get('daily_mean_temp')),
                    'daily_max_temp': safe_float(row.get('daily_max_temp')),

                    # Humidity and moisture
                    'relative_humidity': safe_float(row.get('relative_humidity')),
                    'vapor_pressure': safe_float(row.get('vapor_pressure')),

                    # Wind data
                    'wind_direction': safe_float(row.get('wind_direction')),
                    'wind_speed': safe_float(row.get('wind_speed')),
                    'wind_gust': safe_float(row.get('wind_gust')),

                    # Visibility
                    'visibility': safe_float(row.get('visibility')),

                    # Cloud cover
                    'total_cloud_cover': safe_float(row.get('total_cloud_cover')),
                    'low_cloud_amount': safe_float(row.get('low_cloud_amount')),
                    'medium_cloud_amount': safe_float(row.get('medium_cloud_amount')),
                    'high_cloud_amount': safe_float(row.get('high_cloud_amount')),
                    'cloud_type_low': safe_float(row.get('cloud_type_low')),
                    'cloud_type_high': safe_float(row.get('cloud_type_high')),

                    # Weather phenomena
                    'rainfall': rainfall_val,
                    'evaporation': evaporation_val,
                    'sunshine_hours': sunshine_val
                }

                # Checking if record with same station, year, month, day, hour exists
                existing = WeatherData.query.filter_by(
                    station_index=new_data['station_index'],
                    year=new_data['year'],
                    month=new_data['month'],
                    day=new_data['day'],
                    hour=new_data['hour']
                ).first()

                if existing:
                    skipped += 1
                    continue

                weather_record = WeatherData(**new_data)
                db.session.add(weather_record)
                imported += 1

                # Committing in batches of 100 for better performance
                if imported % 100 == 0:
                    db.session.commit()
                    print(f"Imported {imported} records so far...")

            except Exception as row_err:
                print(f"Row {i} failed to import: {row_err}")
                errors += 1
                continue

        # Final commit
        db.session.commit()
        print(
            f"Import complete: {imported} imported, {skipped} skipped, {errors} errors, {filtered_station_index} filtered by station index.")
        return True

    except Exception as e:
        print(f"Error loading data: {e}")
        db.session.rollback()
        return False


def safe_float(value):
    """Safely convert value to float, return None if invalid or zero"""
    if pd.isna(value) or value == '' or value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if value == '':
                return None
        float_val = float(value)
        # Convert 0 to None
        if float_val == 0.0:
            return None
        return float_val
    except (ValueError, TypeError):
        return None


def safe_int(value):
    """Safely convert value to integer, return None if invalid or zero"""
    if pd.isna(value) or value == '' or value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if value == '':
                return None
        int_val = int(float(value))
        return int_val
    except (ValueError, TypeError):
        return None


def safe_int_allow_zero(value):
    """Safely convert value to integer, allowing zero values (month, day, hour)"""
    if pd.isna(value) or value == '' or value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if value == '':
                return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_string(value):
    """Safely convert value to string, return None if invalid"""
    if pd.isna(value) or value is None:
        return None
    try:
        return str(value).strip()
    except:
        return None


@app.route('/')
def dashboard():
    # unique locations for dropdown
    locations = db.session.query(WeatherData.location.distinct()).filter(
        WeatherData.location.isnot(None),
        WeatherData.location != ''
    ).all()
    locations = [loc[0] for loc in locations if loc[0]]

    # date range
    date_range = db.session.query(
        db.func.min(WeatherData.date),
        db.func.max(WeatherData.date)
    ).first()

    return render_template('dashboard.html', locations=locations, min_date=date_range[0], max_date=date_range[1])


@app.route('/query', methods=['POST'])
def query_data():
    try:
        data = request.json
        query = WeatherData.query

        # Date filters
        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date >= start_date)

        if data.get('end_date'):
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date <= end_date)

        # Location filter
        if data.get('location'):
            query = query.filter(WeatherData.location == data['location'])

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

        # Humidity filters
        if data.get('humidity_min'):
            query = query.filter(WeatherData.relative_humidity >= float(data['humidity_min']))
        if data.get('humidity_max'):
            query = query.filter(WeatherData.relative_humidity <= float(data['humidity_max']))

        page = data.get('page', 1)
        per_page = data.get('per_page', 100)
        results = query.order_by(WeatherData.date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'data': [record.to_dict() for record in results.items],
            'total': results.total,
            'pages': results.pages,
            'current_page': results.page
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/download', methods=['POST'])
def download_data():
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

        results = query.order_by(WeatherData.date.desc()).all()

        # Create DataFrame for download
        df_data = []
        for record in results:
            df_data.append({
                'Date': record.date.strftime('%Y-%m-%d') if record.date else '',
                'Location': record.location,
                'Station Index': record.station_index,
                'Year': record.year,
                'Month': record.month,
                'Day': record.day,
                'Hour': record.hour,
                'Station Level Pressure': record.station_level_pressure,
                'Mean Sea Level Pressure': record.mean_sea_level_pressure,
                'Dry Bulb Temperature': record.dry_bulb_temp,
                'Wet Bulb Temperature': record.wet_bulb_temp,
                'Dew Point Temperature': record.dew_point_temp,
                'Daily Min Temperature': record.daily_min_temp,
                'Daily Mean Temperature': record.daily_mean_temp,
                'Daily Max Temperature': record.daily_max_temp,
                'Relative Humidity': record.relative_humidity,
                'Vapor Pressure': record.vapor_pressure,
                'Wind Direction': record.wind_direction,
                'Wind Speed': record.wind_speed,
                'Wind Gust': record.wind_gust,
                'Visibility': record.visibility,
                'Total Cloud Cover': record.total_cloud_cover,
                'Low Cloud Amount': record.low_cloud_amount,
                'Medium Cloud Amount': record.medium_cloud_amount,
                'High Cloud Amount': record.high_cloud_amount,
                'Cloud Type Low': record.cloud_type_low,
                'Cloud Type High': record.cloud_type_high,
                'Rainfall': record.rainfall,
                'Evaporation': record.evaporation,
                'Sunshine Hours': record.sunshine_hours
            })

        df = pd.DataFrame(df_data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Weather Data')
        output.seek(0)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"weather_data_{timestamp}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Download error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/stats')
def get_stats():
    try:
        total_records = WeatherData.query.count()
        locations_count = db.session.query(WeatherData.location.distinct()).count()

        date_range = db.session.query(
            db.func.min(WeatherData.date),
            db.func.max(WeatherData.date)
        ).first()

        avg_temp = db.session.query(
            db.func.avg(WeatherData.daily_max_temp),
            db.func.avg(WeatherData.daily_min_temp),
            db.func.avg(WeatherData.daily_mean_temp)
        ).first()

        avg_rainfall = db.session.query(
            db.func.avg(WeatherData.rainfall)
        ).first()

        avg_humidity = db.session.query(
            db.func.avg(WeatherData.relative_humidity)
        ).first()

        avg_pressure = db.session.query(
            db.func.avg(WeatherData.station_level_pressure),
            db.func.avg(WeatherData.mean_sea_level_pressure)
        ).first()

        return jsonify({
            'total_records': total_records,
            'locations': locations_count,
            'date_range': {
                'start': date_range[0].strftime('%Y-%m-%d') if date_range[0] else None,
                'end': date_range[1].strftime('%Y-%m-%d') if date_range[1] else None
            },
            'avg_temps': {
                'max': round(avg_temp[0], 2) if avg_temp[0] else None,
                'min': round(avg_temp[1], 2) if avg_temp[1] else None,
                'mean': round(avg_temp[2], 2) if avg_temp[2] else None
            },
            'avg_rainfall': round(avg_rainfall[0], 2) if avg_rainfall[0] else None,
            'avg_humidity': round(avg_humidity[0], 2) if avg_humidity[0] else None,
            'avg_pressure': {
                'station_level': round(avg_pressure[0], 2) if avg_pressure[0] else None,
                'sea_level': round(avg_pressure[1], 2) if avg_pressure[1] else None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/plot', methods=['POST'])
def generate_plot():
    try:
        data = request.json
        plot_type = data.get('plot_type', 'temperature_trend')

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

        results = query.order_by(WeatherData.date.asc()).all()

        if not results:
            return jsonify({'success': False, 'error': 'No data found for plotting'})

        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')

        dates = [record.date for record in results]

        if plot_type == 'temperature_trend':
            max_temps = [record.daily_max_temp for record in results if record.daily_max_temp is not None]
            min_temps = [record.daily_min_temp for record in results if record.daily_min_temp is not None]
            mean_temps = [record.daily_mean_temp for record in results if record.daily_mean_temp is not None]
            valid_dates_max = [record.date for record in results if record.daily_max_temp is not None]
            valid_dates_min = [record.date for record in results if record.daily_min_temp is not None]
            valid_dates_mean = [record.date for record in results if record.daily_mean_temp is not None]

            ax.plot(valid_dates_max, max_temps, 'r-', label='Max Temperature', linewidth=2)
            ax.plot(valid_dates_min, min_temps, 'b-', label='Min Temperature', linewidth=2)
            ax.plot(valid_dates_mean, mean_temps, 'g-', label='Mean Temperature', linewidth=2)
            ax.set_title('Temperature Trend Over Time', fontsize=16, fontweight='bold')
            ax.set_ylabel('Temperature (°C)', fontsize=12)

        elif plot_type == 'rainfall_pattern':
            rainfall = [record.rainfall if record.rainfall is not None else 0 for record in results]
            ax.bar(dates, rainfall, color='skyblue', alpha=0.7)
            ax.set_title('Rainfall Pattern', fontsize=16, fontweight='bold')
            ax.set_ylabel('Rainfall (mm)', fontsize=12)

        elif plot_type == 'humidity_comparison':
            humidity = [record.relative_humidity for record in results if record.relative_humidity is not None]
            valid_dates = [record.date for record in results if record.relative_humidity is not None]

            ax.plot(valid_dates, humidity, 'g-', label='Relative Humidity', linewidth=2)
            ax.set_title('Humidity Over Time', fontsize=16, fontweight='bold')
            ax.set_ylabel('Humidity (%)', fontsize=12)

        elif plot_type == 'pressure_analysis':
            station_pressure = [record.station_level_pressure for record in results if
                                record.station_level_pressure is not None]
            sea_level_pressure = [record.mean_sea_level_pressure for record in results if
                                  record.mean_sea_level_pressure is not None]
            valid_dates_station = [record.date for record in results if record.station_level_pressure is not None]
            valid_dates_sea = [record.date for record in results if record.mean_sea_level_pressure is not None]

            ax.plot(valid_dates_station, station_pressure, 'purple', label='Station Level Pressure', linewidth=2)
            ax.plot(valid_dates_sea, sea_level_pressure, 'brown', label='Sea Level Pressure', linewidth=2)
            ax.set_title('Pressure Analysis', fontsize=16, fontweight='bold')
            ax.set_ylabel('Pressure (hPa)', fontsize=12)

        elif plot_type == 'temp_rainfall_correlation':
            # Scatter plot of temperature vs rainfall
            max_temps = [record.daily_max_temp for record in results if
                         record.daily_max_temp is not None and record.rainfall is not None]
            rainfall = [record.rainfall for record in results if
                        record.daily_max_temp is not None and record.rainfall is not None]

            ax.scatter(max_temps, rainfall, alpha=0.6, color='coral')
            ax.set_title('Temperature vs Rainfall Correlation', fontsize=16, fontweight='bold')
            ax.set_xlabel('Max Temperature (°C)', fontsize=12)
            ax.set_ylabel('Rainfall (mm)', fontsize=12)

        elif plot_type == 'wind_analysis':
            wind_speeds = [record.wind_speed for record in results if record.wind_speed is not None]
            valid_dates = [record.date for record in results if record.wind_speed is not None]

            ax.plot(valid_dates, wind_speeds, 'orange', label='Wind Speed', linewidth=2)
            ax.set_title('Wind Speed Over Time', fontsize=16, fontweight='bold')
            ax.set_ylabel('Wind Speed (m/s)', fontsize=12)

        elif plot_type == 'extreme_values':
            # Collect all extreme values in one chart
            extremes_data = {}

            # Temperature extremes
            max_temps = [record.daily_max_temp for record in results if record.daily_max_temp is not None]
            min_temps = [record.daily_min_temp for record in results if record.daily_min_temp is not None]
            if max_temps and min_temps:
                extremes_data['Highest Temp'] = max(max_temps)
                extremes_data['Lowest Temp'] = min(min_temps)

            # Rainfall extremes
            rainfall_values = [record.rainfall for record in results if
                               record.rainfall is not None and record.rainfall > 0]
            if rainfall_values:
                extremes_data['Max Rainfall'] = max(rainfall_values)

            # Humidity extremes
            humidity_values = [record.relative_humidity for record in results if record.relative_humidity is not None]
            if humidity_values:
                extremes_data['Max Humidity'] = max(humidity_values)
                extremes_data['Min Humidity'] = min(humidity_values)

            # Wind extremes
            wind_values = [record.wind_speed for record in results if record.wind_speed is not None]
            if wind_values:
                extremes_data['Max Wind Speed'] = max(wind_values)

            if extremes_data:
                fig, ax = plt.subplots(figsize=(12, 8))

                labels = list(extremes_data.keys())
                values = list(extremes_data.values())
                colors = ['red', 'blue', 'darkblue', 'green', 'lightgreen', 'orange'][:len(labels)]

                bars = ax.barh(labels, values, color=colors, alpha=0.8)

                for i, (bar, value) in enumerate(zip(bars, values)):
                    width = bar.get_width()
                    ax.text(width + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                            f'{value:.1f}', ha='left', va='center', fontweight='bold')

                ax.set_title('Weather Parameter Extreme Values', fontsize=16, fontweight='bold')
                ax.set_xlabel('Values')
                ax.grid(True, alpha=0.3, axis='x')
                plt.tight_layout()
            else:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, 'No data available for extreme values analysis',
                        ha='center', va='center', fontsize=14, transform=ax.transAxes)
                ax.set_title('Extreme Values Analysis', fontsize=16, fontweight='bold')
                ax.axis('off')

        if plot_type not in ['temp_rainfall_correlation', 'extreme_values']:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax.xaxis.set_major_locator(mdates.YearLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)
            ax.set_xlabel('Year', fontsize=12)

        if plot_type in ['temperature_trend', 'humidity_comparison', 'pressure_analysis', 'wind_analysis']:
            ax.legend()

        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        # Convert plot to base64 string
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()

        return jsonify({
            'success': True,
            'plot_data': f'data:image/png;base64,{img_data}',
            'plot_type': plot_type
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/upload', methods=['POST'])
def upload_data():
    file = request.files.get('file')
    if file:
        filename = secure_filename(file.filename)
        _, ext = os.path.splitext(filename)

        if ext.lower() not in ALLOWED_EXTENSIONS:
            return "Only Excel files are allowed", 400

        filename = secure_filename("new_data" + ext)
        custom_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(custom_path)
        load_excel_data(custom_path)
        return redirect("/")
    return redirect("/")


@app.route('/backup')
def take_backup():
    try:
        backup_dir = os.path.join('backup')
        os.makedirs(backup_dir, exist_ok=True)

        # Generate timestamp for backup filename
        timestamp = datetime.now().strftime('Y%Y_M%m_D%d_Hour%H')
        backup_filename = f'weather_data_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)

        db_path = 'instance/weather_data.db'

        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)

            return send_file(
                backup_path,
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=backup_filename
            )
        else:
            return jsonify({'success': False, 'error': 'Database file not found'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': f'Backup failed: {str(e)}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run()