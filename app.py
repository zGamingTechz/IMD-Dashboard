from flask import Flask, render_template, request, jsonify, send_file, redirect
from flask_sqlalchemy import SQLAlchemy
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


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'.xls', '.xlsx', '.csv'}

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Database Model
class WeatherData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    station_pressure_morning = db.Column(db.Float)
    station_pressure_evening = db.Column(db.Float)
    sea_level_pressure_morning = db.Column(db.Float)
    sea_level_pressure_evening = db.Column(db.Float)
    max_temp = db.Column(db.Float)
    min_temp = db.Column(db.Float)
    vapour_pressure_morning = db.Column(db.Float)
    vapour_pressure_evening = db.Column(db.Float)
    humidity_morning = db.Column(db.Float)
    humidity_evening = db.Column(db.Float)
    rainfall = db.Column(db.Float)
    location = db.Column(db.String(100), index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'station_pressure_morning': self.station_pressure_morning,
            'station_pressure_evening': self.station_pressure_evening,
            'sea_level_pressure_morning': self.sea_level_pressure_morning,
            'sea_level_pressure_evening': self.sea_level_pressure_evening,
            'max_temp': self.max_temp,
            'min_temp': self.min_temp,
            'vapour_pressure_morning': self.vapour_pressure_morning,
            'vapour_pressure_evening': self.vapour_pressure_evening,
            'humidity_morning': self.humidity_morning,
            'humidity_evening': self.humidity_evening,
            'rainfall': self.rainfall,
            'location': self.location
        }


def load_excel_data(file_path):
    try:
        df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)

        column_mapping = {
            'DATE': 'date',
            'STATION LEVEL PRESSURE 0830 IST': 'station_pressure_morning',
            'STATION LEVEL PRESSURE1730 IST': 'station_pressure_evening',
            'MEAN SEA LEVEL PRESSURE0830 IST': 'sea_level_pressure_morning',
            'MEAN SEA LEVEL PRESSURE1730 IST': 'sea_level_pressure_evening',
            'MAX TEMP': 'max_temp',
            'MIN TEMP': 'min_temp',
            'VAPOUR PRESSURE0830 IST': 'vapour_pressure_morning',
            'VAPOUR PRESSURE1730 IST': 'vapour_pressure_evening',
            'RELATIVE HUMIDITY ( %)0830 IST': 'humidity_morning',
            'RELATIVE HUMIDITY ( %)1730 IST': 'humidity_evening',
            'RAIN FALL    (IN MM)': 'rainfall',
            'LOCATION': 'location'
        }

        df.rename(columns=column_mapping, inplace=True)

        imported = 0
        skipped = 0

        for i, row in df.iterrows():
            try:
                if pd.isna(row.get('date')):
                    continue

                parsed_date = pd.to_datetime(row['date'], errors='coerce')
                if pd.isna(parsed_date):
                    print(f"Skipping row {i}: Invalid date '{row['date']}'")
                    continue

                new_data = {
                    'date': parsed_date.date(),
                    'station_pressure_morning': safe_float(row.get('station_pressure_morning')),
                    'station_pressure_evening': safe_float(row.get('station_pressure_evening')),
                    'sea_level_pressure_morning': safe_float(row.get('sea_level_pressure_morning')),
                    'sea_level_pressure_evening': safe_float(row.get('sea_level_pressure_evening')),
                    'max_temp': safe_float(row.get('max_temp')),
                    'min_temp': safe_float(row.get('min_temp')),
                    'vapour_pressure_morning': safe_float(row.get('vapour_pressure_morning')),
                    'vapour_pressure_evening': safe_float(row.get('vapour_pressure_evening')),
                    'humidity_morning': safe_float(row.get('humidity_morning')),
                    'humidity_evening': safe_float(row.get('humidity_evening')),
                    'rainfall': safe_float(row.get('rainfall')),
                    'location': str(row.get('location', '')).strip()
                }

                # Check if an exact same record exists
                exists = WeatherData.query.filter_by(**new_data).first()
                if exists:
                    skipped += 1
                    continue

                db.session.add(WeatherData(**new_data))
                imported += 1

            except Exception as row_err:
                print(f"Row {i} failed to import: {row_err}")
                continue

        db.session.commit()
        print(f"Import complete: {imported} added, {skipped} skipped.")
        return True

    except Exception as e:
        print(f"Error loading data: {e}")
        return False


def safe_float(value):
    if pd.isna(value) or value == '' or value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
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
            query = query.filter(WeatherData.min_temp >= float(data['min_temp_min']))
        if data.get('min_temp_max'):
            query = query.filter(WeatherData.min_temp <= float(data['min_temp_max']))
        if data.get('max_temp_min'):
            query = query.filter(WeatherData.max_temp >= float(data['max_temp_min']))
        if data.get('max_temp_max'):
            query = query.filter(WeatherData.max_temp <= float(data['max_temp_max']))

        # Rainfall filter
        if data.get('rainfall_min'):
            query = query.filter(WeatherData.rainfall >= float(data['rainfall_min']))
        if data.get('rainfall_max'):
            query = query.filter(WeatherData.rainfall <= float(data['rainfall_max']))

        # Humidity filters
        if data.get('humidity_min'):
            query = query.filter(
                db.or_(
                    WeatherData.humidity_morning >= float(data['humidity_min']),
                    WeatherData.humidity_evening >= float(data['humidity_min'])
                )
            )
        if data.get('humidity_max'):
            query = query.filter(
                db.or_(
                    WeatherData.humidity_morning <= float(data['humidity_max']),
                    WeatherData.humidity_evening <= float(data['humidity_max'])
                )
            )

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

        # Fetch data from DB
        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date >= start_date)
        if data.get('end_date'):
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date <= end_date)
        if data.get('location'):
            query = query.filter(WeatherData.location == data['location'])
        if data.get('min_temp_min'):
            query = query.filter(WeatherData.min_temp >= float(data['min_temp_min']))
        if data.get('min_temp_max'):
            query = query.filter(WeatherData.min_temp <= float(data['min_temp_max']))
        if data.get('max_temp_min'):
            query = query.filter(WeatherData.max_temp >= float(data['max_temp_min']))
        if data.get('max_temp_max'):
            query = query.filter(WeatherData.max_temp <= float(data['max_temp_max']))
        if data.get('rainfall_min'):
            query = query.filter(WeatherData.rainfall >= float(data['rainfall_min']))
        if data.get('rainfall_max'):
            query = query.filter(WeatherData.rainfall <= float(data['rainfall_max']))
        if data.get('humidity_min'):
            query = query.filter(
                db.or_(
                    WeatherData.humidity_morning >= float(data['humidity_min']),
                    WeatherData.humidity_evening >= float(data['humidity_min'])
                )
            )
        if data.get('humidity_max'):
            query = query.filter(
                db.or_(
                    WeatherData.humidity_morning <= float(data['humidity_max']),
                    WeatherData.humidity_evening <= float(data['humidity_max'])
                )
            )

        results = query.order_by(WeatherData.date.desc()).all()

        # New DF (for download)
        df_data = []
        for record in results:
            df_data.append({
                'Date': record.date.strftime('%Y-%m-%d'),
                'Station Pressure (Morning)': record.station_pressure_morning,
                'Station Pressure (Evening)': record.station_pressure_evening,
                'Sea Level Pressure (Morning)': record.sea_level_pressure_morning,
                'Sea Level Pressure (Evening)': record.sea_level_pressure_evening,
                'Max Temperature': record.max_temp,
                'Min Temperature': record.min_temp,
                'Vapour Pressure (Morning)': record.vapour_pressure_morning,
                'Vapour Pressure (Evening)': record.vapour_pressure_evening,
                'Humidity (Morning)': record.humidity_morning,
                'Humidity (Evening)': record.humidity_evening,
                'Rainfall (mm)': record.rainfall,
                'Location': record.location
            })

        df = pd.DataFrame(df_data)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"weather_data_{timestamp[0:4]}_{timestamp[4:6]}_{timestamp[6:8]}.xlsx"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Weather Data')

        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise Exception("Failed to create Excel file or file is empty")

        return send_file(
            filepath,
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
            db.func.avg(WeatherData.max_temp),
            db.func.avg(WeatherData.min_temp)
        ).first()

        avg_rainfall = db.session.query(
            db.func.avg(WeatherData.rainfall)
        ).first()

        avg_humidity = db.session.query(
            db.func.avg(WeatherData.humidity_morning),
            db.func.avg(WeatherData.humidity_evening)
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
                'min': round(avg_temp[1], 2) if avg_temp[1] else None
            },
            'avg_rainfall': round(avg_rainfall[0], 2),
            'avg_humidity': {
                'morning': round(avg_humidity[0] if avg_humidity else None),
                'evening': round(avg_humidity[1] if avg_humidity else None)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/plot', methods=['POST'])
def generate_plot():
    try:
        data = request.json
        plot_type = data.get('plot_type', 'temperature_trend')

        query = WeatherData.query

        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date >= start_date)
        if data.get('end_date'):
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            query = query.filter(WeatherData.date <= end_date)
        if data.get('location'):
            query = query.filter(WeatherData.location == data['location'])
        if data.get('min_temp_min'):
            query = query.filter(WeatherData.min_temp >= float(data['min_temp_min']))
        if data.get('min_temp_max'):
            query = query.filter(WeatherData.min_temp <= float(data['min_temp_max']))
        if data.get('max_temp_min'):
            query = query.filter(WeatherData.max_temp >= float(data['max_temp_min']))
        if data.get('max_temp_max'):
            query = query.filter(WeatherData.max_temp <= float(data['max_temp_max']))
        if data.get('rainfall_min'):
            query = query.filter(WeatherData.rainfall >= float(data['rainfall_min']))
        if data.get('rainfall_max'):
            query = query.filter(WeatherData.rainfall <= float(data['rainfall_max']))
        if data.get('humidity_min'):
            query = query.filter(
                db.or_(
                    WeatherData.humidity_morning >= float(data['humidity_min']),
                    WeatherData.humidity_evening >= float(data['humidity_min'])
                )
            )
        if data.get('humidity_max'):
            query = query.filter(
                db.or_(
                    WeatherData.humidity_morning <= float(data['humidity_max']),
                    WeatherData.humidity_evening <= float(data['humidity_max'])
                )
            )

        results = query.order_by(WeatherData.date.asc()).all()

        if not results:
            return jsonify({'success': False, 'error': 'No data found for plotting'})

        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')

        dates = [record.date for record in results]

        if plot_type == 'temperature_trend':
            max_temps = [record.max_temp for record in results if record.max_temp is not None]
            min_temps = [record.min_temp for record in results if record.min_temp is not None]
            valid_dates_max = [record.date for record in results if record.max_temp is not None]
            valid_dates_min = [record.date for record in results if record.min_temp is not None]

            ax.plot(valid_dates_max, max_temps, 'r-', label='Max Temperature', linewidth=2)
            ax.plot(valid_dates_min, min_temps, 'b-', label='Min Temperature', linewidth=2)
            ax.set_title('Temperature Trend Over Time', fontsize=16, fontweight='bold')
            ax.set_ylabel('Temperature (°C)', fontsize=12)

        elif plot_type == 'rainfall_pattern':
            rainfall = [record.rainfall if record.rainfall is not None else 0 for record in results]
            ax.bar(dates, rainfall, color='skyblue', alpha=0.7)
            ax.set_title('Rainfall Pattern', fontsize=16, fontweight='bold')
            ax.set_ylabel('Rainfall (mm)', fontsize=12)

        elif plot_type == 'humidity_comparison':
            morning_humidity = [record.humidity_morning for record in results if record.humidity_morning is not None]
            evening_humidity = [record.humidity_evening for record in results if record.humidity_evening is not None]
            valid_dates_morning = [record.date for record in results if record.humidity_morning is not None]
            valid_dates_evening = [record.date for record in results if record.humidity_evening is not None]

            ax.plot(valid_dates_morning, morning_humidity, 'g-', label='Morning Humidity', linewidth=2)
            ax.plot(valid_dates_evening, evening_humidity, 'orange', label='Evening Humidity', linewidth=2)
            ax.set_title('Humidity Comparison (Morning vs Evening)', fontsize=16, fontweight='bold')
            ax.set_ylabel('Humidity (%)', fontsize=12)

        elif plot_type == 'pressure_analysis':
            morning_pressure = [record.station_pressure_morning for record in results if
                                record.station_pressure_morning is not None]
            evening_pressure = [record.station_pressure_evening for record in results if
                                record.station_pressure_evening is not None]
            valid_dates_morning = [record.date for record in results if record.station_pressure_morning is not None]
            valid_dates_evening = [record.date for record in results if record.station_pressure_evening is not None]

            ax.plot(valid_dates_morning, morning_pressure, 'purple', label='Morning Pressure', linewidth=2)
            ax.plot(valid_dates_evening, evening_pressure, 'brown', label='Evening Pressure', linewidth=2)
            ax.set_title('Station Pressure Analysis', fontsize=16, fontweight='bold')
            ax.set_ylabel('Pressure (hPa)', fontsize=12)

        elif plot_type == 'temp_rainfall_correlation':
            # Scatter plot of temperature vs rainfall
            max_temps = [record.max_temp for record in results if
                         record.max_temp is not None and record.rainfall is not None]
            rainfall = [record.rainfall for record in results if
                        record.max_temp is not None and record.rainfall is not None]

            ax.scatter(max_temps, rainfall, alpha=0.6, color='coral')
            ax.set_title('Temperature vs Rainfall Correlation', fontsize=16, fontweight='bold')
            ax.set_xlabel('Max Temperature (°C)', fontsize=12)
            ax.set_ylabel('Rainfall (mm)', fontsize=12)

        elif plot_type == 'extreme_values':
            # Collect all extreme values in one chart
            extremes_data = {}

            # Temperature extremes
            max_temps = [record.max_temp for record in results if record.max_temp is not None]
            min_temps = [record.min_temp for record in results if record.min_temp is not None]
            if max_temps and min_temps:
                extremes_data['Highest Temp'] = max(max_temps)
                extremes_data['Lowest Temp'] = min(min_temps)

            # Rainfall extremes
            rainfall_values = [record.rainfall for record in results if
                               record.rainfall is not None and record.rainfall > 0]
            if rainfall_values:
                extremes_data['Max Rainfall'] = max(rainfall_values)

            # Humidity extremes
            humidity_morning = [record.humidity_morning for record in results if record.humidity_morning is not None]
            humidity_evening = [record.humidity_evening for record in results if record.humidity_evening is not None]
            if humidity_morning and humidity_evening:
                all_humidity = humidity_morning + humidity_evening
                extremes_data['Max Humidity'] = max(all_humidity)
                extremes_data['Min Humidity'] = min(all_humidity)

            if extremes_data:
                fig, ax = plt.subplots(figsize=(12, 8))

                labels = list(extremes_data.keys())
                values = list(extremes_data.values())
                colors = ['red', 'blue', 'darkblue', 'green', 'lightgreen'][:len(labels)]

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

        # Format dates on x-axis
        if plot_type != 'temp_rainfall_correlation':
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            ax.set_xlabel('Date', fontsize=12)

        if plot_type in ['temperature_trend', 'humidity_comparison', 'pressure_analysis']:
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
        plt.close()
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
        custom_path = os.path.join('new data', filename)
        os.makedirs(os.path.dirname(custom_path), exist_ok=True)
        file.save(custom_path)
        load_excel_data(custom_path)
        return redirect("/")
    return redirect("/")


@app.route('/backup')
def take_backup():
    print("h")
    try:
        backup_dir = os.path.join('backup')
        os.makedirs(backup_dir, exist_ok=True)

        # Generate timestamp for backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
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

    app.run(debug=True)