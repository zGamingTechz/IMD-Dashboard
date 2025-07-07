// Validation rules for meteorological data
const validationRules = {
    dry_bulb_temp: { min: -50, max: 60, name: 'Dry Bulb Temperature' },
    wet_bulb_temp: { min: -50, max: 50, name: 'Wet Bulb Temperature' },
    dew_point_temp: { min: -60, max: 40, name: 'Dew Point Temperature' },
    daily_min_temp: { min: -50, max: 50, name: 'Daily Minimum Temperature' },
    daily_mean_temp: { min: -40, max: 55, name: 'Daily Mean Temperature' },
    daily_max_temp: { min: -30, max: 60, name: 'Daily Maximum Temperature' },
    station_level_pressure: { min: 800, max: 1100, name: 'Station Level Pressure' },
    mean_sea_level_pressure: { min: 950, max: 1050, name: 'Mean Sea Level Pressure' },
    relative_humidity: { min: 0, max: 100, name: 'Relative Humidity' },
    vapor_pressure: { min: 0, max: 100, name: 'Vapor Pressure' },
    wind_direction: { min: 0, max: 360, name: 'Wind Direction' },
    wind_speed: { min: 0, max: 200, name: 'Wind Speed' },
    wind_gust: { min: 0, max: 300, name: 'Wind Gust' },
    visibility: { min: 0, max: 50, name: 'Visibility' },
    total_cloud_cover: { min: 0, max: 8, name: 'Total Cloud Cover' },
    low_cloud_amount: { min: 0, max: 8, name: 'Low Cloud Amount' },
    medium_cloud_amount: { min: 0, max: 8, name: 'Medium Cloud Amount' },
    high_cloud_amount: { min: 0, max: 8, name: 'High Cloud Amount' },
    cloud_type_low: { min: 0, max: 10, name: 'Cloud Type Low' },
    cloud_type_high: { min: 0, max: 10, name: 'Cloud Type High' },
    rainfall: { min: 0, max: 1000, name: 'Rainfall' },
    evaporation: { min: 0, max: 50, name: 'Evaporation' },
    sunshine_hours: { min: 0, max: 14, name: 'Sunshine Hours' }
};

function validateForm() {
    const warnings = [];
    const form = document.getElementById('weatherDataForm');
    const formData = new FormData(form);

    // Check each field against validation rules
    for (const [fieldName, rule] of Object.entries(validationRules)) {
        const value = formData.get(fieldName);
        if (value && value !== '') {
            const numValue = parseFloat(value);
            if (numValue < rule.min || numValue > rule.max) {
                warnings.push(`${rule.name}: ${numValue} is outside normal range (${rule.min} - ${rule.max})`);
            }
        }
    }

    // Additional logical validations
    const minTemp = parseFloat(formData.get('daily_min_temp'));
    const maxTemp = parseFloat(formData.get('daily_max_temp'));
    const meanTemp = parseFloat(formData.get('daily_mean_temp'));

    if (minTemp && maxTemp && minTemp > maxTemp) {
        warnings.push('Daily minimum temperature is higher than maximum temperature');
    }

    if (meanTemp && minTemp && maxTemp && (meanTemp < minTemp || meanTemp > maxTemp)) {
        warnings.push('Daily mean temperature is outside the min-max range');
    }

    const wetBulb = parseFloat(formData.get('wet_bulb_temp'));
    const dryBulb = parseFloat(formData.get('dry_bulb_temp'));
    if (wetBulb && dryBulb && wetBulb > dryBulb) {
        warnings.push('Wet bulb temperature cannot be higher than dry bulb temperature');
    }

    // Date validation
    const year = parseInt(formData.get('year'));
    const month = parseInt(formData.get('month'));
    const day = parseInt(formData.get('day'));

    if (year && month && day) {
        const date = new Date(year, month - 1, day);
        if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
            warnings.push('Invalid date combination');
        }

        const currentDate = new Date();
        if (date > currentDate) {
            warnings.push('Future date entered - please verify');
        }
    }

    if (warnings.length > 0) {
        displayValidationResults(warnings);
    } else {
        // If no warnings, submit the form directly
        form.submit();
    }
}

function displayValidationResults(warnings) {
    const warningsContainer = document.getElementById('validationWarnings');
    const forceSubmitBtn = document.getElementById('forceSubmitBtn');

    let warningsHtml = '<div class="message message-warning"><i class="fas fa-exclamation-triangle"></i><strong>Data Validation Warnings:</strong><ul>';
    warnings.forEach(warning => {
        warningsHtml += `<li>${warning}</li>`;
    });
    warningsHtml += '</ul></div>';

    warningsContainer.innerHTML = warningsHtml;
    warningsContainer.style.display = 'block';
    forceSubmitBtn.style.display = 'inline-flex';

    // Scroll to warnings
    warningsContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function clearForm() {
    if (confirm('Are you sure you want to clear all form data?')) {
        document.getElementById('weatherDataForm').reset();
        document.getElementById('validationWarnings').style.display = 'none';
        document.getElementById('forceSubmitBtn').style.display = 'none';
    }
}

// Auto-validate on form submission
document.getElementById('weatherDataForm').addEventListener('submit', function(e) {
    if (!document.getElementById('forceSubmitBtn').contains(e.submitter)) {
        e.preventDefault();
        validateForm();
    }
});

// Set current year as default
document.addEventListener('DOMContentLoaded', function() {
    const yearInput = document.getElementById('year');
    if (!yearInput.value) {
        yearInput.value = new Date().getFullYear();
    }
});