// Global variables
let currentOutliers = [];
let currentOutliersPage = 1;
let selectedLocations = [];
let allLocations = [];

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the dashboard
    initDashboard();
});

function initDashboard() {
    // Set up event listeners
    setupEventListeners();

    // Load available columns
    loadColumns();

    // Set default date range to last 30 days
    setDefaultDateRange();

    // Initialize location selector
    initLocationSelector();
}

function setupEventListeners() {
    // Search button
    document.getElementById('searchBtn').addEventListener('click', function() {
        executeQuery();
    });

    // Download button
    document.getElementById('downloadBtn').addEventListener('click', function() {
        downloadData();
    });

    // Outliers button
    document.getElementById('outliersBtn').addEventListener('click', function() {
        detectOutliers();
    });

    // Clear button
    document.getElementById('clearBtn').addEventListener('click', function() {
        clearFilters();
    });

    // Quick filter buttons
    document.querySelectorAll('.quick-filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            applyQuickFilter(this.dataset.filter);
        });
    });

    // Time filter buttons
    document.querySelectorAll('.time-filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all buttons
            document.querySelectorAll('.time-filter-btn').forEach(b => {
                b.classList.remove('active');
            });

            // Add active class to clicked button
            this.classList.add('active');
        });
    });

    // Per page selector
    document.getElementById('perPage').addEventListener('change', function() {
        executeQuery();
    });
}

function initLocationSelector() {
    const locationSelect = document.getElementById('locationSelect');
    const locationDropdown = document.getElementById('locationDropdown');
    const locationSearch = document.getElementById('locationSearch');
    const locationOptions = document.getElementById('locationOptions');
    const selectedLocationsContainer = document.getElementById('selectedLocations');
    const locationPlaceholder = document.getElementById('locationPlaceholder');

    // Populate allLocations array from HTML
    allLocations = Array.from(locationOptions.querySelectorAll('.location-option')).map(option => option.dataset.value);

    // Toggle dropdown
    locationSelect.addEventListener('click', function(e) {
        e.stopPropagation();
        const isVisible = locationDropdown.style.display === 'block';
        locationDropdown.style.display = isVisible ? 'none' : 'block';
        if (!isVisible) {
            locationSearch.focus();
        }
    });

    // Search functionality
    locationSearch.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const options = locationOptions.querySelectorAll('.location-option');

        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            option.style.display = text.includes(searchTerm) ? 'block' : 'none';
        });
    });

    // Handle option selection
    locationOptions.addEventListener('click', function(e) {
        if (e.target.classList.contains('location-option')) {
            const value = e.target.dataset.value;

            if (!selectedLocations.includes(value)) {
                selectedLocations.push(value);
                updateSelectedLocations();
                e.target.classList.add('selected');
            }

            locationSearch.value = '';
            filterLocationOptions('');
        }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!locationSelect.contains(e.target) && !locationDropdown.contains(e.target)) {
            locationDropdown.style.display = 'none';
        }
    });

    // Prevent dropdown from closing when clicking inside
    locationDropdown.addEventListener('click', function(e) {
        e.stopPropagation();
    });

    function updateSelectedLocations() {
        selectedLocationsContainer.innerHTML = '';

        if (selectedLocations.length === 0) {
            locationPlaceholder.style.display = 'block';
            return;
        }

        locationPlaceholder.style.display = 'none';

        selectedLocations.forEach(location => {
            const tag = document.createElement('div');
            tag.className = 'location-tag';
            tag.innerHTML = `
                <span>${location}</span>
                <span class="remove" onclick="removeLocation('${location}')">×</span>
            `;
            selectedLocationsContainer.appendChild(tag);
        });
    }

    function filterLocationOptions(searchTerm) {
        const options = locationOptions.querySelectorAll('.location-option');
        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            option.style.display = text.includes(searchTerm.toLowerCase()) ? 'block' : 'none';
        });
    }

    // Make removeLocation function globally accessible
    window.removeLocation = function(location) {
        selectedLocations = selectedLocations.filter(loc => loc !== location);
        updateSelectedLocations();

        // Update option styling
        const option = locationOptions.querySelector(`[data-value="${location}"]`);
        if (option) {
            option.classList.remove('selected');
        }
    };
}

function loadColumns() {
    fetch('/advanced-query/columns')
        .then(response => response.json())
        .then(data => {
            const columnsContainer = document.getElementById('columnsContainer');
            const outlierColumnSelect = document.getElementById('outlierColumn');

            // Clear existing options
            columnsContainer.innerHTML = '';
            outlierColumnSelect.innerHTML = '<option value="">Select column</option>';

            // Add columns to container
            data.columns.forEach(column => {
                // Add checkbox to columns container
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'column-checkbox';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `col_${column}`;
                checkbox.value = column;

                const label = document.createElement('label');
                label.htmlFor = `col_${column}`;
                label.textContent = formatColumnName(column);

                checkboxDiv.appendChild(checkbox);
                checkboxDiv.appendChild(label);
                columnsContainer.appendChild(checkboxDiv);

                // Add option to outlier dropdown
                const option = document.createElement('option');
                option.value = column;
                option.textContent = formatColumnName(column);
                outlierColumnSelect.appendChild(option);
            });

            // Set default columns
            ['date', 'location', 'station_index', 'daily_max_temp', 'daily_min_temp', 'rainfall'].forEach(col => {
                const checkbox = document.getElementById(`col_${col}`);
                if (checkbox) checkbox.checked = true;
            });
        })
        .catch(error => {
            showMessage('Error loading columns: ' + error.message, 'error');
        });
}

function setDefaultDateRange() {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    document.getElementById('startDate').valueAsDate = thirtyDaysAgo;
    document.getElementById('endDate').valueAsDate = new Date();
}

function formatColumnName(column) {
    return column
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
        .replace('Temp', 'Temp (°C)')
        .replace('Rainfall', 'Rainfall (mm)')
        .replace('Humidity', 'Humidity (%)')
        .replace('Pressure', 'Pressure (hPa)')
        .replace('Wind Speed', 'Wind Speed (m/s)');
}

function applyQuickFilter(type) {
    clearFilters();

    switch(type) {
        case 'rainfall_gt_10':
            document.getElementById('rainfallMin').value = '10';
            break;
        case 'high_temp':
            document.getElementById('maxTempMin').value = '35';
            break;
        case 'low_temp':
            document.getElementById('minTempMax').value = '10';
            break;
        case 'high_humidity':
            document.getElementById('humidityMin').value = '80';
            break;
        case 'windy':
            document.getElementById('windSpeedMin').value = '10';
            break;
    }

    executeQuery();
}

function collectFilters() {
    // Helper function to convert string to number or return undefined if empty
    function toNumber(value) {
        return value === '' ? undefined : Number(value);
    }

    const filters = {
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value,
        location: selectedLocations.length > 0 ? selectedLocations : undefined,

        // Temperature - convert to numbers
        min_temp_min: toNumber(document.getElementById('minTempMin').value),
        min_temp_max: toNumber(document.getElementById('minTempMax').value),
        max_temp_min: toNumber(document.getElementById('maxTempMin').value),
        max_temp_max: toNumber(document.getElementById('maxTempMax').value),

        // Rainfall - convert to numbers
        rainfall_min: toNumber(document.getElementById('rainfallMin').value),
        rainfall_max: toNumber(document.getElementById('rainfallMax').value),

        // Humidity - convert to numbers
        humidity_min: toNumber(document.getElementById('humidityMin').value),
        humidity_max: toNumber(document.getElementById('humidityMax').value),

        // Wind - convert to numbers
        wind_speed_min: toNumber(document.getElementById('windSpeedMin').value),
        wind_speed_max: toNumber(document.getElementById('windSpeedMax').value),

        // Pressure - convert to numbers
        pressure_min: toNumber(document.getElementById('pressureMin').value),
        pressure_max: toNumber(document.getElementById('pressureMax').value),

        // Cloud cover - convert to numbers
        cloud_cover_min: toNumber(document.getElementById('cloudCoverMin').value),
        cloud_cover_max: toNumber(document.getElementById('cloudCoverMax').value),

        // Time of day
        time_of_day: document.querySelector('.time-filter-btn.active')?.dataset.time
    };

    // Get selected columns
    const checkboxes = document.querySelectorAll('#columnsContainer input[type="checkbox"]:checked');
    filters.columns = Array.from(checkboxes).map(cb => cb.value);

    return filters;
}

function executeQuery(page = 1) {
    const filters = collectFilters();
    filters.page = page;
    filters.per_page = document.getElementById('perPage').value;

    showLoading();

    fetch('/advanced-query/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters)
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();

        if (data.success) {
            displayResults(data.data);
            updatePagination(data.current_page, data.pages, data.total);
            updateSummary(data.data);
            document.getElementById('resultsCount').textContent = `${data.total} records`;
            showMessage(`Found ${data.total} records`, 'success');

            // Show results and hide outliers
            document.getElementById('resultsContainer').style.display = 'block';
            document.getElementById('outliersSection').style.display = 'none';
        } else {
            showMessage('Error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showMessage('Error: ' + error.message, 'error');
    });
}

function detectOutliers(page = 1) {
    const filters = collectFilters();
    const column = document.getElementById('outlierColumn').value;
    const threshold = document.getElementById('outlierThreshold').value;
    const location = document.getElementById('outlierLocation').value;

    if (!column) {
        showMessage('Please select a column for outlier detection', 'error');
        return;
    }

    showLoading();

    fetch('/advanced-query/outliers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ...filters,
            column,
            threshold,
            location: location || undefined
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();

        if (data.success) {
            currentOutliers = data.outliers;
            displayOutliers(data.outliers);
            updateOutliersPagination(page, Math.ceil(data.outliers.length / 10), data.outliers.length);
            document.getElementById('outliersCount').textContent = `${data.outliers.length} outliers (${data.column})`;
            showMessage(`Found ${data.outliers.length} outliers in ${data.total_records} records (column: ${data.column})`, 'success');

            // Show outliers and hide results
            document.getElementById('outliersSection').style.display = 'block';
            document.getElementById('resultsContainer').style.display = 'none';
        } else {
            showMessage('Error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showMessage('Error: ' + error.message, 'error');
    });
}

function displayResults(data) {
    const table = document.getElementById('resultsTable');
    const thead = document.getElementById('tableHeaders');
    const tbody = document.getElementById('dataTableBody');

    // Clear previous results
    thead.innerHTML = '';
    tbody.innerHTML = '';

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="20" class="no-data">No data found matching your criteria</td></tr>';
        return;
    }

    // Create headers from first item's keys
    const headers = Object.keys(data[0]);
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = formatColumnName(header);
        thead.appendChild(th);
    });

    // Add data rows
    data.forEach(row => {
        const tr = document.createElement('tr');

        headers.forEach(header => {
            const td = document.createElement('td');
            let value = row[header];

            if (value === null || value === undefined) {
                value = 'N/A';
            } else if (header === 'date' && value) {
                // Format date
                value = new Date(value).toLocaleDateString();
            } else if (typeof value === 'number') {
                // Format numbers to 2 decimal places
                value = value.toFixed(2);
            }

            td.textContent = value;
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
}

function displayOutliers(outliers) {
    const tbody = document.getElementById('outliersTableBody');
    tbody.innerHTML = '';

    if (outliers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">No outliers found</td></tr>';
        return;
    }

    // Calculate pagination
    const perPage = 10;
    const startIdx = (currentOutliersPage - 1) * perPage;
    const endIdx = Math.min(startIdx + perPage, outliers.length);
    const paginatedOutliers = outliers.slice(startIdx, endIdx);

    paginatedOutliers.forEach(outlier => {
        const tr = document.createElement('tr');

        // Date
        const dateTd = document.createElement('td');
        dateTd.textContent = outlier.date ? new Date(outlier.date).toLocaleDateString() : 'N/A';
        tr.appendChild(dateTd);

        // Location
        const locTd = document.createElement('td');
        locTd.textContent = outlier.location || 'N/A';
        tr.appendChild(locTd);

        // Value
        const valueTd = document.createElement('td');
        valueTd.textContent = typeof outlier.value === 'number' ? outlier.value.toFixed(2) : outlier.value;
        tr.appendChild(valueTd);

        // Z-Score
        const zTd = document.createElement('td');
        zTd.textContent = outlier.z_score.toFixed(2);
        tr.appendChild(zTd);

        // Deviation
        const devTd = document.createElement('td');
        const deviation = outlier.z_score > 0 ? `+${outlier.z_score.toFixed(2)}σ` : `${outlier.z_score.toFixed(2)}σ`;
        devTd.textContent = deviation;
        devTd.style.color = outlier.z_score > 3 ? '#dc3545' : outlier.z_score > 2 ? '#fd7e14' : '#ffc107';
        tr.appendChild(devTd);

        tbody.appendChild(tr);
    });
}

function updateSummary(data) {
    if (data.length === 0) {
        document.getElementById('maxTemp').textContent = 'N/A';
        document.getElementById('minTemp').textContent = 'N/A';
        document.getElementById('maxRainfall').textContent = 'N/A';
        return;
    }

    // Get max and min temperatures from daily_max_temp and daily_min_temp
    const maxTemps = data
        .map(item => Number(item.daily_max_temp))
        .filter(val => !isNaN(val) && val !== null);

    const minTemps = data
        .map(item => Number(item.daily_min_temp))
        .filter(val => !isNaN(val) && val !== null);

    // Calculate overall max and min temperatures
    let overallMaxTemp = 'N/A';
    let overallMinTemp = 'N/A';

    if (maxTemps.length > 0) {
        overallMaxTemp = Math.max(...maxTemps).toFixed(1) + '°C';
    }

    if (minTemps.length > 0) {
        overallMinTemp = Math.min(...minTemps).toFixed(1) + '°C';
    }

    document.getElementById('maxTemp').textContent = overallMaxTemp;
    document.getElementById('minTemp').textContent = overallMinTemp;

    // Max rainfall
    const rainfalls = data
        .map(item => Number(item.rainfall))
        .filter(val => !isNaN(val) && val !== null && val > 0);

    if (rainfalls.length > 0) {
        const maxRainfall = Math.max(...rainfalls);
        document.getElementById('maxRainfall').textContent = maxRainfall.toFixed(1) + 'mm';
    } else {
        document.getElementById('maxRainfall').textContent = 'N/A';
    }
}

function updatePagination(current, total, totalRecords) {
    const container = document.getElementById('paginationContainer');
    container.innerHTML = '';

    if (total <= 1) return;

    // Previous button
    if (current > 1) {
        const prevBtn = createPaginationButton('Previous', current - 1);
        container.appendChild(prevBtn);
    }

    // First page
    if (current > 1) {
        const firstBtn = createPaginationButton('1', 1);
        if (current > 2) container.appendChild(firstBtn);
    }

    // Ellipsis before current page if needed
    if (current > 3) {
        const ellipsis = document.createElement('span');
        ellipsis.textContent = '...';
        ellipsis.className = 'pagination-ellipsis';
        container.appendChild(ellipsis);
    }

    // Current page and surrounding pages
    const startPage = Math.max(1, current - 1);
    const endPage = Math.min(total, current + 1);

    for (let i = startPage; i <= endPage; i++) {
        if (i === 1 && current > 3) continue; // Skip if we already added first page

        const pageBtn = createPaginationButton(i.toString(), i, i === current);
        container.appendChild(pageBtn);
    }

    // Ellipsis after current page if needed
    if (current < total - 2) {
        const ellipsis = document.createElement('span');
        ellipsis.textContent = '...';
        ellipsis.className = 'pagination-ellipsis';
        container.appendChild(ellipsis);
    }

    // Last page
    if (current < total) {
        const lastBtn = createPaginationButton(total.toString(), total);
        if (current < total - 1) container.appendChild(lastBtn);
    }

    // Next button
    if (current < total) {
        const nextBtn = createPaginationButton('Next', current + 1);
        container.appendChild(nextBtn);
    }

    // Info
    const info = document.createElement('div');
    info.className = 'pagination-info';
    info.textContent = `Page ${current} of ${total}`;
    container.appendChild(info);
}

function updateOutliersPagination(current, total, totalRecords) {
    const container = document.getElementById('outliersPaginationContainer');
    container.innerHTML = '';

    if (total <= 1) return;

    // Previous button
    if (current > 1) {
        const prevBtn = createOutliersPaginationButton('Previous', current - 1);
        container.appendChild(prevBtn);
    }

    // Page numbers
    for (let i = 1; i <= total; i++) {
        const pageBtn = createOutliersPaginationButton(i.toString(), i, i === current);
        container.appendChild(pageBtn);
    }

    // Next button
    if (current < total) {
        const nextBtn = createOutliersPaginationButton('Next', current + 1);
        container.appendChild(nextBtn);
    }

    // Info
    const info = document.createElement('div');
    info.className = 'pagination-info';
    info.textContent = `Page ${current} of ${total}`;
    container.appendChild(info);
}

function createPaginationButton(text, page, isActive = false) {
    const button = document.createElement('button');
    button.className = `pagination-btn ${isActive ? 'active' : ''}`;
    button.textContent = text;
    button.addEventListener('click', () => executeQuery(page));
    return button;
}

function createOutliersPaginationButton(text, page, isActive = false) {
    const button = document.createElement('button');
    button.className = `pagination-btn ${isActive ? 'active' : ''}`;
    button.textContent = text;
    button.addEventListener('click', () => {
        currentOutliersPage = page;
        displayOutliers(currentOutliers);
        updateOutliersPagination(page, Math.ceil(currentOutliers.length / 10), currentOutliers.length);
    });
    return button;
}

function downloadData() {
    const filters = collectFilters();
    showMessage('Preparing download...', 'info');

    fetch('/advanced-query/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Download failed');
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `weather_data_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        showMessage('Download completed!', 'success');
    })
    .catch(error => {
        showMessage('Download error: ' + error.message, 'error');
    });
}

function clearFilters() {
    // Clear input fields
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('minTempMin').value = '';
    document.getElementById('minTempMax').value = '';
    document.getElementById('maxTempMin').value = '';
    document.getElementById('maxTempMax').value = '';
    document.getElementById('rainfallMin').value = '';
    document.getElementById('rainfallMax').value = '';
    document.getElementById('humidityMin').value = '';
    document.getElementById('humidityMax').value = '';
    document.getElementById('windSpeedMin').value = '';
    document.getElementById('windSpeedMax').value = '';
    document.getElementById('pressureMin').value = '';
    document.getElementById('pressureMax').value = '';
    document.getElementById('cloudCoverMin').value = '';
    document.getElementById('cloudCoverMax').value = '';
    document.getElementById('outlierColumn').value = '';
    document.getElementById('outlierThreshold').value = '3';
    document.getElementById('outlierLocation').value = '';

    // Clear selected locations
    selectedLocations = [];
    document.getElementById('selectedLocations').innerHTML = '';
    document.getElementById('locationPlaceholder').style.display = 'block';

    // Remove selected styling from location options
    document.querySelectorAll('.location-option').forEach(option => {
        option.classList.remove('selected');
    });

    // Uncheck all column checkboxes
    document.querySelectorAll('#columnsContainer input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });

    // Re-check default columns
    ['date', 'location', 'station_index', 'daily_max_temp', 'daily_min_temp', 'rainfall'].forEach(col => {
        const checkbox = document.getElementById(`col_${col}`);
        if (checkbox) checkbox.checked = true;
    });

    // Reset time filters
    document.querySelectorAll('.time-filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Hide results and outliers
    document.getElementById('resultsContainer').style.display = 'none';
    document.getElementById('outliersSection').style.display = 'none';

    // Clear pagination
    document.getElementById('paginationContainer').innerHTML = '';
    document.getElementById('outliersPaginationContainer').innerHTML = '';

    // Reset summary
    document.getElementById('maxTemp').textContent = '-';
    document.getElementById('minTemp').textContent = '-';
    document.getElementById('maxRainfall').textContent = '-';

    showMessage('Filters cleared', 'info');
}

function showLoading() {
    document.getElementById('loadingContainer').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingContainer').style.display = 'none';
}

function showMessage(message, type) {
    const container = document.getElementById('messageContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}`;

    // Clear existing messages
    container.innerHTML = '';
    container.appendChild(messageDiv);

    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
}

// PDF Download functionality
document.getElementById('downloadPdfBtn').addEventListener('click', function() {
    const filters = collectFilters();

    // Show loading state
    const pdfBtn = document.getElementById('downloadPdfBtn');
    const originalText = pdfBtn.innerHTML;
    pdfBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
    pdfBtn.disabled = true;

    fetch('/advanced-query/download-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.blob();
    })
    .then(blob => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;

        // Generate filename with timestamp
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        a.download = `weather_report_${timestamp}.pdf`;

        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);

        showMessage('PDF downloaded successfully!', 'success');
    })
    .catch(error => {
        console.error('PDF download error:', error);
        showMessage(error.error || 'Failed to generate PDF', 'error');
    })
    .finally(() => {
        // Restore button state
        pdfBtn.innerHTML = originalText;
        pdfBtn.disabled = false;
    });
});

function showLoading() {
    document.getElementById('loadingContainer').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingContainer').style.display = 'none';
}

function showMessage(message, type) {
    const container = document.getElementById('messageContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}`;

    // Clear existing messages
    container.innerHTML = '';
    container.appendChild(messageDiv);

    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
}

// Make removeLocation function globally accessible
window.removeLocation = function(location) {
    selectedLocations = selectedLocations.filter(loc => loc !== location);
    updateSelectedLocations();

    // Update option styling
    const option = document.querySelector(`.location-option[data-value="${location}"]`);
    if (option) {
        option.classList.remove('selected');
    }
};

// Helper function to update selected locations display
function updateSelectedLocations() {
    const selectedLocationsContainer = document.getElementById('selectedLocations');
    const locationPlaceholder = document.getElementById('locationPlaceholder');

    selectedLocationsContainer.innerHTML = '';

    if (selectedLocations.length === 0) {
        locationPlaceholder.style.display = 'block';
        return;
    }

    locationPlaceholder.style.display = 'none';

    selectedLocations.forEach(location => {
        const tag = document.createElement('div');
        tag.className = 'location-tag';
        tag.innerHTML = `
            <span>${location}</span>
            <span class="remove" onclick="removeLocation('${location}')">×</span>
        `;
        selectedLocationsContainer.appendChild(tag);
    });
}