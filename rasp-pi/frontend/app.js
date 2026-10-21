// Monitor for BORTO metrics
document.addEventListener('alpine:init', () => {
    Alpine.data('bortoMonitor', () => ({
        connected: false,
        connectionstatus: {},
        activeTab: 'dashboard',
        dc1metrics: {},
        dc1_current_voltage: 0,
        dc1_value_count: 0,
        dc1_average_voltage: 0,
        dc1_max_voltage: 0,
        dc1_min_voltage: 0,
        battmetrics: {},
        battstatus: 0,
        manual_status_override: false,
        startPolling() {
            this.getDC1Metrics();
            setInterval(() => {
                this.getDC1Metrics();
            }, 500); 
            this.getBattMetrics();
            setInterval(() => {
                this.getBattMetrics();
            }, 500);
            this.checkNetworkStatus();
            setInterval(() => {
                this.checkNetworkStatus();
            }, 2000);
        },
        async getDC1Metrics () {
            try {
                const dc1response = await fetch('/api/metrics/dc1');
                if (dc1response.ok) {
                    this.dc1metrics = await dc1response.json();
                }
                this.add_voltage_data_to_chart(dc1_chart);
            } catch (error) {
                console.error('DC1 Metrics could not be read:', error);
            }
        },
        add_voltage_data_to_chart(chart) {
            const voltage = this.dc1metrics[0].voltage_value;
            const time = this.dc1metrics[0].timestamp.substring(11,19);
            const voltage_dataset = chart.data.datasets[0].data;
            const avg_voltage_dataset = chart.data.datasets[1].data;
            const chart_labels = chart.data.labels;
            // Prevent duplicate entries
            if (voltage === voltage_dataset.at(-1) &&
                time === chart_labels.at(-1)    
            )
            {
                // console.log("Duplicate voltage values.");
                return;
            }
            chart_labels.push(time);
            voltage_dataset.push(voltage);

            if (chart_labels.length > 50) {
                chart_labels.shift();
                voltage_dataset.shift();
                avg_voltage_dataset.shift();
            }

            if (chart === dc1_chart) {
                this.update_current_dc1();
                this.update_max_dc1();
                this.update_min_dc1();
                this.update_average_dc1();
            }

            chart.update();
        },
        update_current_dc1 () {
            this.dc1_current_voltage = this.dc1metrics[0].voltage_value.toFixed(1);
        },
        update_average_dc1 () {
            this.dc1_average_voltage = (((this.dc1_average_voltage * this.dc1_value_count) + this.dc1metrics[0].voltage_value) / (this.dc1_value_count + 1)).toFixed(1);
            this.dc1_value_count++;
            dc1_chart.data.datasets[1].data.push(this.dc1_average_voltage);
        },
        update_max_dc1() {
            const voltage = this.dc1metrics[0].voltage_value;
            if (voltage > this.dc1_max_voltage) {
                this.dc1_max_voltage = voltage.toFixed(1);
            }
        },
        update_min_dc1 () {
            const voltage = this.dc1metrics[0].voltage_value;
            if (this.dc1_min_voltage === 0 || this.dc1_min_voltage > voltage) {
                this.dc1_min_voltage = voltage.toFixed(1);
            } 
        },
        async getBattMetrics () {
            try {
                const battresponse = await fetch('/api/metrics/batt');
                if (battresponse.ok) {
                    this.battmetrics = await battresponse.json();
                }
                if (!this.manual_status_override) {
                    this.battstatus = this.battmetrics[0].status;
                    // console.log(this.battstatus);
                }
                let time = this.battmetrics[0].timestamp.substring(11,19);
                add_battery_data_to_chart(
                        batt_chart, 
                        this.battmetrics[0].voltage_value,
                        this.battmetrics[0].current_value,
                        this.battmetrics[0].voltage_value * this.battmetrics[0].current_value,
                        time,
                    );
            } catch (error) {
                console.error('Battery Metrics could not be read:', error);
            }
        },
        async checkNetworkStatus () {
            try {
                const networkStatus = await fetch('api/network-status');
                if (networkStatus.ok) {
                    this.connectionstatus = await networkStatus.json();
                }
                this.connected = this.connectionstatus.connected;
                console.log(this.connectionstatus);

            } catch (error) {
                console.error('Network status chould not be verified.', error);
            }
        }
    }));

    Alpine.data('wifiManager', () => ({
        ssid: '',
        password: '',
        status: '',
        connecting: false,

        connectToWifi() {
            this.connecting = true;
            this.status = '';
            // console.log(JSON.stringify({ssid: this.ssid, password: this.password}));
            fetch('/api/connect-wifi', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    ssid: this.ssid,
                    password: this.password
                })
            })
            .then(response => response.json().then(data => ({status: response.data, body: data})))
            .then(result => {
                // console.log(result.body);
                this.connecting = false;
                if (result.status === 200) {
                    this.status = 'Connected successfully.';
                } else {
                    this.status = 'Error: ' + (result.body.detail || "Failed to connect.");
                }
            })
            .catch(error => {
                this.connecting = false;
                this.status = "Network error occurred."
            })
        }
    }));
});

let dc1_voltage_toggle = document.getElementById("dc1-voltage-toggle");
dc1_voltage_toggle.addEventListener('change', () => {
    if (dc1_voltage_toggle.checked) {
        dc1_chart.setDatasetVisibility(0, true);
    } else {
        dc1_chart.setDatasetVisibility(0, false);
    }
    dc1_chart.update();
})

let dc1_average_voltage_toggle = document.getElementById("dc1-average-voltage-toggle");
dc1_average_voltage_toggle.addEventListener('change', () => {
    if (dc1_average_voltage_toggle.checked) {
        dc1_chart.setDatasetVisibility(1, true);
    } else {
        dc1_chart.setDatasetVisibility(1, false);
    }
    dc1_chart.update();
})

let batt_voltage_toggle = document.getElementById("batt-voltage-toggle");
batt_voltage_toggle.addEventListener('change', () => {
    if (batt_voltage_toggle.checked) {
        batt_chart.setDatasetVisibility(0, true);
    } else {
        batt_chart.setDatasetVisibility(0, false);
    }
    batt_chart.update();
});
let batt_current_toggle = document.getElementById("batt-current-toggle");
batt_current_toggle.addEventListener('change', () => {
    if (batt_current_toggle.checked) {
        batt_chart.setDatasetVisibility(1, true);
    } else {
        batt_chart.setDatasetVisibility(1, false);
    }
    batt_chart.update();
});
let batt_power_toggle = document.getElementById("batt-power-toggle");
batt_power_toggle.addEventListener('change', () => {
    if (batt_power_toggle.checked) {
        batt_chart.setDatasetVisibility(2, true);
    } else {
        batt_chart.setDatasetVisibility(2, false);
    }
    batt_chart.update();
})

function update_current_batt_values(voltage, current) {
    let current_batt_voltage = document.getElementById("batt-current-voltage");
    current_batt_voltage.textContent = voltage.toFixed(1);
    let current_batt_current = document.getElementById("batt-current-current");
    current_batt_current.textContent = current.toFixed(1);
}

let batt_value_count = 0;
let batt_average_voltage = 0;
let batt_average_current = 0;
function update_batt_average(voltage, current) {
    batt_average_voltage = ((batt_average_voltage * batt_value_count) + voltage) / (batt_value_count + 1);
    batt_average_current = ((batt_average_current * batt_value_count) + current) / (batt_value_count + 1);
    batt_value_count++;
    let batt_avg_voltage = document.getElementById("batt-average-voltage");
    let batt_avg_current = document.getElementById("batt-average-current");
    batt_avg_voltage.textContent = batt_average_voltage.toFixed(1);
    batt_avg_current.textContent = batt_average_current.toFixed(1);

    // dc1_chart.data.datasets[1].data.push(dc1_average_voltage);
}

function add_battery_data_to_chart(chart, voltage, current, power, timestamp) {
    // Guard clause prevents duplicate data entries 
    if (
        (voltage === chart.data.datasets[0].data.at(-1)) &&
        (current === chart.data.datasets[1].data.at(-1)) &&
        (power === chart.data.datasets[2].data.at(-1)) &&
        (timestamp === chart.data.labels.at(-1))
    )
    {
        console.log("Duplicate battery values");
        return;
    }
    
    chart.data.labels.push(timestamp);
    
    chart.data.datasets[0].data.push(voltage);
    chart.data.datasets[1].data.push(current);
    chart.data.datasets[2].data.push(power);

    if (chart.data.labels.length > 50) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
        chart.data.datasets[1].data.shift();
        chart.data.datasets[2].data.shift();
    }

    update_current_batt_values(voltage, current);
    update_batt_average(voltage, current);

    chart.update();
}

