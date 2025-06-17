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
            document.getElementById('avgHumMor').textContent = data.avg_humidity.morning ? data.avg_humidity.morning : 'N/A';
            document.getElementById('avgHumEve').textContent = data.avg_humidity.evening ? data.avg_humidity.evening : 'N/A';
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
        min_temp_min: document.getElementById('minTempMin').value,
        min_temp_max: document.getElementById('minTempMax').value,
        max_temp_min: document.getElementById('maxTempMin').value,
        max_temp_max: document.getElementById('maxTempMax').value,
        rainfall_min: document.getElementById('rainfallMin').value,
        rainfall_max: document.getElementById('rainfallMax').value,
        humidity_min: document.getElementById('humidityMin').value,
        humidity_max: document.getElementById('humidityMax').value
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
        tbody.innerHTML = '<tr><td colspan="13" class="no-data">No data found matching your criteria</td></tr>';
    } else {
        data.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${record.date}</td>
                <td>${record.location || 'N/A'}</td>
                <td>${record.max_temp !== null ? record.max_temp.toFixed(1) : 'N/A'}</td>
                <td>${record.min_temp !== null ? record.min_temp.toFixed(1) : 'N/A'}</td>
                <td>${record.rainfall !== null ? record.rainfall.toFixed(1) : 'N/A'}</td>
                <td>${record.humidity_morning !== null ? record.humidity_morning.toFixed(1) : 'N/A'}</td>
                <td>${record.humidity_evening !== null ? record.humidity_evening.toFixed(1) : 'N/A'}</td>
                <td>${record.station_pressure_morning !== null ? record.station_pressure_morning.toFixed(2) : 'N/A'}</td>
                <td>${record.station_pressure_evening !== null ? record.station_pressure_evening.toFixed(2) : 'N/A'}</td>
                <td>${record.sea_level_pressure_morning !== null ? record.sea_level_pressure_morning.toFixed(2) : 'N/A'}</td>
                <td>${record.sea_level_pressure_evening !== null ? record.sea_level_pressure_evening.toFixed(2) : 'N/A'}</td>
                <td>${record.vapour_pressure_morning !== null ? record.vapour_pressure_morning.toFixed(2) : 'N/A'}</td>
                <td>${record.vapour_pressure_evening !== null ? record.vapour_pressure_evening.toFixed(2) : 'N/A'}</td>
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
    ['startDate', 'endDate', 'location', 'minTempMin', 'minTempMax', 'maxTempMin', 'maxTempMax', 'rainfallMin', 'rainfallMax', 'humidityMin', 'humidityMax'].forEach(id => {
        document.getElementById(id).value = '';
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
        // Create a temporary anchor element
        const link = document.createElement('a');
        link.href = plotImage.src;
        link.download = `weather_plot_${new Date().getTime()}.png`;

        // Temporarily add to DOM and click
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