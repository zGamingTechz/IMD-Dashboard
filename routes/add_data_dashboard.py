from flask import Blueprint, render_template, request, redirect, url_for
from extensions import db
from models import WeatherData

add_data_bp = Blueprint('add_data', __name__)

@add_data_bp.route('/add-data', methods=['GET', 'POST'])
def add_data():
    return render_template("add_data.html")
