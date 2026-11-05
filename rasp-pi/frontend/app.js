// Monitor for BORTO metrics
document.addEventListener('alpine:init', () => {
    Alpine.data('bortoMonitor', () => ({
        connected: false,
        current_ssid: '',
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

        savingSettings: false,
        settingsMsg: '',
        settingsErr: false,

        settings: {
            deviceName: 'BORTO2026',
            operatingMode: 'auto_tou',
            tou: {
                preset: 'winter',
                offPeakStart: '19:00',
                offPeakEnd: '07:00',
                onPeak1Start: '07:00',
                onPeak1End: '11:00',
                onPeak2Start: '17:00',
                onPeak2End: '19:00',
                reserveSoc: 50,
                weekendsOffPeak: true
            }
        },

        powerModal: {
            open: false,
            action: '',
            title: '',
            message: ''
        },

        loadingDebug: false,

        debug: {
            enabled: false,
            dc1_setpoint: 0.0,
            dc2_setpoint: 0.0,
            dc1_duty_cycle: 0.0, // Updated via polling or loadDebugParams()
            dc2_duty_cycle: 0.0, // Updated via polling or loadDebugParams()
            cal: {
                dc1_v_slope: 1.0,
                dc1_v_offset: 0.0,
                dc1_i_slope: 1.0,
                dc1_i_offset: 0.0,
                dc2_v_slope: 1.0,
                dc2_v_offset: 0.0,
                temp_slope: 1.0,
                temp_offset: 0.0,
            }
        },

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
                this.current_ssid = this.connectionstatus.ssid;
                console.log(this.connectionstatus);

            } catch (error) {
                console.error('Network status chould not be verified.', error);
            }
        },
        notifySettings(msg, isErr = false) {
            this.settingsMsg = msg;
            this.settingsErr = isErr;
            setTimeout(() => { this.settingsMsg = ''; }, 5000);
        },

        applyTouPreset() {
            const p = this.settings.tou.preset;
            if (p === 'winter') {
                Object.assign(this.settings.tou, {
                    offPeakStart: '19:00', offPeakEnd: '07:00',
                    onPeak1Start: '07:00', onPeak1End: '11:00',
                    onPeak2Start: '17:00', onPeak2End: '19:00'
                });
            } else if (p === 'summer') {
                Object.assign(this.settings.tou, {
                    offPeakStart: '19:00', offPeakEnd: '07:00',
                    onPeak1Start: '11:00', onPeak1End: '17:00',
                    onPeak2Start: '', onPeak2End: ''
                });
            } else if (p === 'ulo') {
                Object.assign(this.settings.tou, {
                    offPeakStart: '23:00', offPeakEnd: '07:00',
                    onPeak1Start: '16:00', onPeak1End: '21:00',
                    onPeak2Start: '', onPeak2End: ''
                });
            }
        },

        async saveGeneralSettings() {
            this.savingSettings = true;
            try {
                const res = await fetch('/api/settings/general', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        device_name: this.settings.deviceName,
                        operating_mode: this.settings.operatingMode
                    })
                });
                if (!res.ok) throw new Error('Failed to save device settings');
                this.notifySettings('Device settings updated.');
            } catch (err) {
                this.notifySettings(err.message, true);
            } finally {
                this.savingSettings = false;
            }
        },

        async saveTouSettings() {
            this.savingSettings = true;
            try {
                const res = await fetch('/api/settings/tou', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.settings.tou)
                });
                if (!res.ok) throw new Error('Failed to save TOU schedule');
                this.notifySettings('Time of Use schedule saved.');
            } catch (err) {
                this.notifySettings(err.message, true);
            } finally {
                this.savingSettings = false;
            }
        },

        async syncBrowserTime() {
            try {
                const res = await fetch('/api/settings/time', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ iso_time: new Date().toISOString() })
                });
                if (!res.ok) throw new Error('Failed to sync system time');
                this.notifySettings('System time synced with browser.');
            } catch (err) {
                this.notifySettings(err.message, true);
            }
        },

        confirmPower(action) {
            this.powerModal.action = action;
            this.powerModal.title = action === 'reboot' ? 'Reboot BORTO2026?' : 'Shut Down BORTO2026?';
            this.powerModal.message = action === 'reboot'
                ? 'The Raspberry Pi will restart and the dashboard will reconnect in ~45 seconds.'
                : 'The Raspberry Pi will halt. You will need to physically toggle power to turn it back on.';
            this.powerModal.open = true;
        },

        async executePowerAction() {
            this.savingSettings = true;
            try {
                const res = await fetch(`/api/system/${this.powerModal.action}`, { method: 'POST' });
                if (!res.ok) throw new Error(`Failed to initiate ${this.powerModal.action}`);
                this.powerModal.open = false;
                this.notifySettings(`System ${this.powerModal.action} initiated...`);
            } catch (err) {
                this.notifySettings(err.message, true);
            } finally {
                this.savingSettings = false;
            }
        },

        async loadDebugParams() {
            this.loadingDebug = true;
            try {
                const res = await fetch('/api/debug/params');
                if (!res.ok) throw new Error('Failed to read debug parameters from MCU');
                const data = await res.json();

                this.debug.dc1_setpoint = data.dc1_setpoint ?? this.debug.dc1_setpoint;
                this.debug.dc2_setpoint = data.dc2_setpoint ?? this.debug.dc2_setpoint;
                this.debug.dc1_duty_cycle = data.dc1_duty_cycle ?? this.debug.dc1_duty_cycle;
                this.debug.dc2_duty_cycle = data.dc2_duty_cycle ?? this.debug.dc2_duty_cycle;

                if (data.cal) {
                    Object.assign(this.debug.cal, data.cal);
                }
                this.notifySettings('Debug parameters loaded from controller.');
            } catch (err) {
                this.notifySettings(err.message, true);
            } finally {
                this.loadingDebug = false;
            }
        },

        // WRITE DC1 & DC2 setpoints to backend
        async saveDebugSetpoints() {
            if (!this.debug.enabled) return;
            this.savingSettings = true;
            try {
                const res = await fetch('/api/debug/setpoints', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        dc1_setpoint: this.debug.dc1_setpoint,
                        dc2_setpoint: this.debug.dc2_setpoint
                    })
                });
                if (!res.ok) throw new Error('Failed to write DC1/DC2 setpoints');
                this.notifySettings('DC1 & DC2 setpoints updated.');
            } catch (err) {
                this.notifySettings(err.message, true);
            } finally {
                this.savingSettings = false;
            }
        },

        // WRITE DC1 (V/I) & DC2 (V) calibration slopes and offsets to backend
        async saveSensorCalibration() {
            if (!this.debug.enabled) return;
            this.savingSettings = true;
            try {
                const res = await fetch('/api/debug/calibration', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.debug.cal)
                });
                if (!res.ok) throw new Error('Failed to write sensor calibration');
                this.notifySettings('Sensor calibration slopes and offsets updated.');
            } catch (err) {
                this.notifySettings(err.message, true);
            } finally {
                this.savingSettings = false;
            }
        },
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

