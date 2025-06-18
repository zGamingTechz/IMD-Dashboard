let currentPage = 1;
let totalPages = 1;
let currentFilters = {};

document.addEventListener('DOMContentLoaded', function() {
    loadStats();
});

window.onclick = function(event) {
    let modal = document.getElementById('uploadModal')
    if (event.target == modal) modal.style.display = "none"
}

function loadStats() {
    fetch('/stats')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error loading stats:', data.error);
                return;
            }
            document.getElementById('totalRecords').textContent = data.total_records || 0;
            document.getElementById('locationsCount').textContent = data.locations || 0;
            document.getElementById('avgMaxTemp').textContent = data.avg_temps.max ? data.avg_temps.max + '°C' : 'N/A';
            document.getElementById('avgMinTemp').textContent = data.avg_temps.min ? data.avg_temps.min + '°C' : 'N/A';
            document.getElementById('avgRainfall').textContent = data.avg_rainfall ? data.avg_rainfall + 'mm' : 'N/A';

            document.getElementById('avgHumMor').textContent = data.avg_humidity ? data.avg_humidity + '%' : 'N/A';
        })
        .catch(error => {
            console.error('Error loading stats:', error);
        });
}

function collectFilters() {
    return {
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value,
        location: document.getElementById('location').value,

        daily_min_temp_min: document.getElementById('minTempMin').value,
        daily_min_temp_max: document.getElementById('minTempMax').value,
        daily_max_temp_min: document.getElementById('maxTempMin').value,
        daily_max_temp_max: document.getElementById('maxTempMax').value,

        rainfall_min: document.getElementById('rainfallMin').value,
        rainfall_max: document.getElementById('rainfallMax').value,

        relative_humidity_min: document.getElementById('humidityMin').value,
        relative_humidity_max: document.getElementById('humidityMax').value,

        // Additional filters for new data fields
        dry_bulb_temp_min: document.getElementById('dryBulbTempMin')?.value,
        dry_bulb_temp_max: document.getElementById('dryBulbTempMax')?.value,
        wet_bulb_temp_min: document.getElementById('wetBulbTempMin')?.value,
        wet_bulb_temp_max: document.getElementById('wetBulbTempMax')?.value,
        wind_speed_min: document.getElementById('windSpeedMin')?.value,
        wind_speed_max: document.getElementById('windSpeedMax')?.value,
        station_level_pressure_min: document.getElementById('stationPressureMin')?.value,
        station_level_pressure_max: document.getElementById('stationPressureMax')?.value
    };
}

function searchData(page = 1) {
    currentFilters = collectFilters();
    currentFilters.page = page;
    currentFilters.per_page = 10;
    showLoading();
    fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentFilters)
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displayResults(data.data);
            updatePagination(data.current_page, data.pages, data.total);
            showMessage(`Found ${data.total} records`, 'success');
            if (data.total > 0) {
                document.getElementById('plotContainer').style.display = 'block';
                generatePlot('temperature_trend');
            }
        } else {
            showMessage('Error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showMessage('Error: ' + error.message, 'error');
    });
}

function generatePlot(plotType) {
    const filters = collectFilters();
    filters.plot_type = plotType;
    showMessage('Generating plot...', 'info');
    fetch('/plot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('plotImage').src = data.plot_data;
            showMessage('Plot generated successfully!', 'success');
        } else {
            showMessage('Plot error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showMessage('Plot error: ' + error.message, 'error');
    });
}

function displayResults(data) {
    const tbody = document.getElementById('dataTableBody');
    tbody.innerHTML = '';
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="20" class="no-data">No data found matching your criteria</td></tr>';
    } else {
        data.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${record.date || 'N/A'}</td>
                <td>${record.location || 'N/A'}</td>
                <td>${record.station_index || 'N/A'}</td>
                <td>${record.hour !== null ? record.hour : 'N/A'}</td>
                <td>${record.daily_max_temp !== null ? record.daily_max_temp.toFixed(1) + '°C' : 'N/A'}</td>
                <td>${record.daily_min_temp !== null ? record.daily_min_temp.toFixed(1) + '°C' : 'N/A'}</td>
                <td>${record.daily_mean_temp !== null ? record.daily_mean_temp.toFixed(1) + '°C' : 'N/A'}</td>
                <td>${record.dry_bulb_temp !== null ? record.dry_bulb_temp.toFixed(1) + '°C' : 'N/A'}</td>
                <td>${record.wet_bulb_temp !== null ? record.wet_bulb_temp.toFixed(1) + '°C' : 'N/A'}</td>
                <td>${record.dew_point_temp !== null ? record.dew_point_temp.toFixed(1) + '°C' : 'N/A'}</td>
                <td>${record.relative_humidity !== null ? record.relative_humidity.toFixed(1) + '%' : 'N/A'}</td>
                <td>${record.rainfall !== null ? record.rainfall.toFixed(1) + 'mm' : 'N/A'}</td>
                <td>${record.station_level_pressure !== null ? record.station_level_pressure.toFixed(2) + ' hPa' : 'N/A'}</td>
                <td>${record.mean_sea_level_pressure !== null ? record.mean_sea_level_pressure.toFixed(2) + ' hPa' : 'N/A'}</td>
                <td>${record.vapor_pressure !== null ? record.vapor_pressure.toFixed(2) + ' hPa' : 'N/A'}</td>
                <td>${record.wind_speed !== null ? record.wind_speed.toFixed(1) + ' m/s' : 'N/A'}</td>
                <td>${record.wind_direction !== null ? record.wind_direction.toFixed(0) + '°' : 'N/A'}</td>
                <td>${record.wind_gust !== null ? record.wind_gust.toFixed(1) + ' m/s' : 'N/A'}</td>
                <td>${record.visibility !== null ? record.visibility.toFixed(1) + ' km' : 'N/A'}</td>
                <td>${record.total_cloud_cover !== null ? record.total_cloud_cover.toFixed(1) : 'N/A'}</td>
            `;
            tbody.appendChild(row);
        });
    }
    document.getElementById('resultsContainer').style.display = 'block';
}

function updatePagination(current, total, totalRecords) {
    currentPage = current;
    totalPages = total;
    const container = document.getElementById('paginationContainer');
    container.innerHTML = '';
    if (total <= 1) return;

    if (current > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.className = 'pagination-btn';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i> Previous';
        prevBtn.onclick = () => searchData(current - 1);
        container.appendChild(prevBtn);
    }

    const startPage = Math.max(1, current - 2);
    const endPage = Math.min(total, current + 2);

    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `pagination-btn ${i === current ? 'active' : ''}`;
        pageBtn.textContent = i;
        pageBtn.onclick = () => searchData(i);
        container.appendChild(pageBtn);
    }

    if (current < total) {
        const nextBtn = document.createElement('button');
        nextBtn.className = 'pagination-btn';
        nextBtn.innerHTML = 'Next <i class="fas fa-chevron-right"></i>';
        nextBtn.onclick = () => searchData(current + 1);
        container.appendChild(nextBtn);
    }

    const info = document.createElement('div');
    info.className = 'pagination-info';
    info.textContent = `Page ${current} of ${total} (${totalRecords} total records)`;
    container.appendChild(info);
}

function downloadData() {
    const filters = collectFilters();
    showMessage('Preparing download...', 'info');
    fetch('/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }).catch(() => {
                throw new Error(`HTTP error! status: ${response.status}`);
            });
        }
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'weather_data.xlsx';
        if (contentDisposition && contentDisposition.includes('filename=')) {
            filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
        }
        return response.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
        if (blob.size === 0) {
            throw new Error('Downloaded file is empty');
        }
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);
        showMessage('Download completed successfully!', 'success');
    })
    .catch(error => {
        console.error('Download error:', error);
        showMessage('Download error: ' + error.message, 'error');
    });
}

function clearFilters() {
    const filterIds = [
        'startDate', 'endDate', 'location',
        'minTempMin', 'minTempMax', 'maxTempMin', 'maxTempMax',
        'rainfallMin', 'rainfallMax', 'humidityMin', 'humidityMax',
        'dryBulbTempMin', 'dryBulbTempMax', 'wetBulbTempMin', 'wetBulbTempMax',
        'windSpeedMin', 'windSpeedMax', 'stationPressureMin', 'stationPressureMax'
    ];

    filterIds.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.value = '';
        }
    });

    document.getElementById('resultsContainer').style.display = 'none';
    document.getElementById('plotContainer').style.display = 'none';
    document.getElementById('paginationContainer').innerHTML = '';
    showMessage('Filters cleared', 'info');
}

function loadAllData() {
    clearFilters();
    searchData();
}

function loadRecentData() {
    clearFilters();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    document.getElementById('startDate').value = thirtyDaysAgo.toISOString().split('T')[0];
    document.getElementById('endDate').value = new Date().toISOString().split('T')[0];
    searchData();
}

function showLoading() {
    document.getElementById('loadingContainer').style.display = 'flex';
    document.getElementById('resultsContainer').style.display = 'none';
}

function hideLoading() {
    document.getElementById('loadingContainer').style.display = 'none';
}

function showMessage(message, type) {
    const container = document.getElementById('messageContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}`;
    container.innerHTML = '';
    container.appendChild(messageDiv);
    setTimeout(() => {
        container.innerHTML = '';
    }, 5000);
}

document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchData();
    }
});

function downloadPlot() {
    const plotImage = document.getElementById('plotImage');

    if (!plotImage.src || plotImage.src === '') {
        showMessage('No plot available to download. Please generate a plot first.', 'error');
        return;
    }

    try {
        // Temporary anchor element
        const link = document.createElement('a');
        link.href = plotImage.src;
        link.download = `weather_plot_${new Date().getTime()}.png`;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showMessage('Plot downloaded successfully!', 'success');
    } catch (error) {
        console.error('Download error:', error);
        showMessage('Error downloading plot: ' + error.message, 'error');
    }
}

function takeBackup() {
    showMessage('Preparing backup...', 'info');

    fetch('/backup', {
        method: 'GET'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }).catch(() => {
                throw new Error(`HTTP error! status: ${response.status}`);
            });
        }

        // Get filename from Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'weather_data_backup.db';
        if (contentDisposition && contentDisposition.includes('filename=')) {
            filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
        }

        return response.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
        if (blob.size === 0) {
            throw new Error('Backup file is empty');
        }

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();

        // Cleanup
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);

        showMessage('Backup downloaded successfully!', 'success');
    })
    .catch(error => {
        console.error('Backup error:', error);
        showMessage('Backup error: ' + error.message, 'error');
    });
}

// Additional utility functions for new data structure
function formatTemperature(temp) {
    return temp !== null ? temp.toFixed(1) + '°C' : 'N/A';
}

function formatPressure(pressure) {
    return pressure !== null ? pressure.toFixed(2) + ' hPa' : 'N/A';
}

function formatHumidity(humidity) {
    return humidity !== null ? humidity.toFixed(1) + '%' : 'N/A';
}

function formatWind(wind) {
    return wind !== null ? wind.toFixed(1) + ' m/s' : 'N/A';
}

function formatWindDirection(direction) {
    return direction !== null ? direction.toFixed(0) + '°' : 'N/A';
}

function formatRainfall(rainfall) {
    return rainfall !== null ? rainfall.toFixed(1) + ' mm' : 'N/A';
}

function formatVisibility(visibility) {
    return visibility !== null ? visibility.toFixed(1) + ' km' : 'N/A';
}

// Export data summary function
function exportDataSummary() {
    const filters = collectFilters();
    showMessage('Generating data summary...', 'info');

    fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({...filters, per_page: 10000}) // Get more data for summary
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.data.length > 0) {
            generateDataSummaryReport(data.data);
        } else {
            showMessage('No data available for summary', 'error');
        }
    })
    .catch(error => {
        showMessage('Error generating summary: ' + error.message, 'error');
    });
}

function generateDataSummaryReport(data) {
    // Calculate statistics
    const temps = data.filter(r => r.daily_max_temp !== null).map(r => r.daily_max_temp);
    const minTemps = data.filter(r => r.daily_min_temp !== null).map(r => r.daily_min_temp);
    const rainfall = data.filter(r => r.rainfall !== null && r.rainfall > 0).map(r => r.rainfall);
    const humidity = data.filter(r => r.relative_humidity !== null).map(r => r.relative_humidity);
    const windSpeeds = data.filter(r => r.wind_speed !== null).map(r => r.wind_speed);

    const summary = {
        totalRecords: data.length,
        temperatureStats: {
            maxTemp: temps.length > 0 ? Math.max(...temps) : 'N/A',
            minTemp: minTemps.length > 0 ? Math.min(...minTemps) : 'N/A',
            avgMaxTemp: temps.length > 0 ? (temps.reduce((a, b) => a + b, 0) / temps.length).toFixed(1) : 'N/A',
            avgMinTemp: minTemps.length > 0 ? (minTemps.reduce((a, b) => a + b, 0) / minTemps.length).toFixed(1) : 'N/A'
        },
        rainfallStats: {
            totalRainfall: rainfall.length > 0 ? rainfall.reduce((a, b) => a + b, 0).toFixed(1) : 'N/A',
            avgRainfall: rainfall.length > 0 ? (rainfall.reduce((a, b) => a + b, 0) / rainfall.length).toFixed(1) : 'N/A',
            maxRainfall: rainfall.length > 0 ? Math.max(...rainfall) : 'N/A',
            rainyDays: rainfall.length
        },
        humidityStats: {
            avgHumidity: humidity.length > 0 ? (humidity.reduce((a, b) => a + b, 0) / humidity.length).toFixed(1) : 'N/A',
            maxHumidity: humidity.length > 0 ? Math.max(...humidity) : 'N/A',
            minHumidity: humidity.length > 0 ? Math.min(...humidity) : 'N/A'
        },
        windStats: {
            avgWindSpeed: windSpeeds.length > 0 ? (windSpeeds.reduce((a, b) => a + b, 0) / windSpeeds.length).toFixed(1) : 'N/A',
            maxWindSpeed: windSpeeds.length > 0 ? Math.max(...windSpeeds) : 'N/A'
        }
    };

    console.log('Weather Data Summary:', summary);
    showMessage('Data summary generated. Check console for details.', 'success');
}