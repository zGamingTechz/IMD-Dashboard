from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from models import WeatherData
from extensions import db
from datetime import datetime

edit_data_bp = Blueprint('edit_data', __name__, template_folder='../templates')


@edit_data_bp.route('/edit-data', methods=['GET', 'POST'])
def edit_data_dashboard():
    if request.method == 'POST':
        # Handle form submission for finding records
        station_index = request.form.get('station_index')
        year = request.form.get('year')
        month = request.form.get('month')
        day = request.form.get('day')
        hour = request.form.get('hour')

        # Basic validation
        if not all([station_index, year, month, day, hour]):
            flash('Station index, year, month, day and hour are required', 'error')
            return redirect(url_for('edit_data.edit_data_dashboard'))

        try:
            # Convert to appropriate types
            year = int(year)
            month = int(month)
            day = int(day)
            hour = int(hour)
        except ValueError:
            flash('Please enter valid numbers for year, month, day and hour', 'error')
            return redirect(url_for('edit_data.edit_data_dashboard'))

        # Query the database
        query = WeatherData.query.filter_by(
            station_index=station_index,
            year=year,
            month=month,
            day=day,
            hour=hour
        )

        records = query.all()

        if not records:
            flash('No records found matching your criteria', 'warning')
            return redirect(url_for('edit_data.edit_data_dashboard'))

        return render_template('edit_data_results.html', records=records)

    return render_template('edit_data_dashboard.html')


@edit_data_bp.route('/delete-record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    record = WeatherData.query.get_or_404(record_id)

    try:
        db.session.delete(record)
        db.session.commit()
        flash('Record deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting record: {str(e)}', 'error')

    return redirect(url_for('edit_data.edit_data_dashboard'))


@edit_data_bp.route('/edit-record/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    record = WeatherData.query.get_or_404(record_id)

    if request.method == 'POST':
        try:
            # Update all fields from the form
            record.station_index = request.form.get('station_index')
            record.location = request.form.get('location')
            record.year = int(request.form.get('year'))
            record.month = int(request.form.get('month'))
            record.day = int(request.form.get('day'))
            record.hour = int(request.form.get('hour')) if request.form.get('hour') else None

            # Temperature fields
            record.dry_bulb_temp = float(request.form.get('dry_bulb_temp')) if request.form.get(
                'dry_bulb_temp') else None
            record.wet_bulb_temp = float(request.form.get('wet_bulb_temp')) if request.form.get(
                'wet_bulb_temp') else None
            record.dew_point_temp = float(request.form.get('dew_point_temp')) if request.form.get(
                'dew_point_temp') else None
            record.daily_min_temp = float(request.form.get('daily_min_temp')) if request.form.get(
                'daily_min_temp') else None
            record.daily_mean_temp = float(request.form.get('daily_mean_temp')) if request.form.get(
                'daily_mean_temp') else None
            record.daily_max_temp = float(request.form.get('daily_max_temp')) if request.form.get(
                'daily_max_temp') else None

            # Pressure fields
            record.station_level_pressure = float(request.form.get('station_level_pressure')) if request.form.get(
                'station_level_pressure') else None
            record.mean_sea_level_pressure = float(request.form.get('mean_sea_level_pressure')) if request.form.get(
                'mean_sea_level_pressure') else None

            # Humidity and moisture
            record.relative_humidity = float(request.form.get('relative_humidity')) if request.form.get(
                'relative_humidity') else None
            record.vapor_pressure = float(request.form.get('vapor_pressure')) if request.form.get(
                'vapor_pressure') else None

            # Wind data
            record.wind_direction = float(request.form.get('wind_direction')) if request.form.get(
                'wind_direction') else None
            record.wind_speed = float(request.form.get('wind_speed')) if request.form.get('wind_speed') else None
            record.wind_gust = float(request.form.get('wind_gust')) if request.form.get('wind_gust') else None

            # Visibility
            record.visibility = float(request.form.get('visibility')) if request.form.get('visibility') else None

            # Cloud cover
            record.total_cloud_cover = float(request.form.get('total_cloud_cover')) if request.form.get(
                'total_cloud_cover') else None
            record.low_cloud_amount = float(request.form.get('low_cloud_amount')) if request.form.get(
                'low_cloud_amount') else None
            record.medium_cloud_amount = float(request.form.get('medium_cloud_amount')) if request.form.get(
                'medium_cloud_amount') else None
            record.high_cloud_amount = float(request.form.get('high_cloud_amount')) if request.form.get(
                'high_cloud_amount') else None
            record.cloud_type_low = float(request.form.get('cloud_type_low')) if request.form.get(
                'cloud_type_low') else None
            record.cloud_type_high = float(request.form.get('cloud_type_high')) if request.form.get(
                'cloud_type_high') else None

            # Weather phenomena
            record.rainfall = float(request.form.get('rainfall')) if request.form.get('rainfall') else None
            record.evaporation = float(request.form.get('evaporation')) if request.form.get('evaporation') else None
            record.sunshine_hours = float(request.form.get('sunshine_hours')) if request.form.get(
                'sunshine_hours') else None

            # Update date field
            if record.year and record.month and record.day:
                try:
                    record.date = datetime(record.year, record.month, record.day).date()
                except ValueError:
                    record.date = None

            db.session.commit()
            flash('Record updated successfully', 'success')
            return redirect(url_for('edit_data.edit_data_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating record: {str(e)}', 'error')
            return redirect(url_for('edit_data.edit_record', record_id=record_id))

    return render_template('edit_record_form.html', record=record)