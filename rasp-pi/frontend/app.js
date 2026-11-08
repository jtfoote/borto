// Monitor for BORTO metrics
document.addEventListener('alpine:init', () => {
    Alpine.data('bortoMonitor', () => ({
        connected: false,
        current_ssid: '',
        connectionstatus: {},
        activeTab: 'dashboard',
        // DC1 (Voltage)
        dc1metrics: [],
        dc1_current_voltage: '0.0',
        dc1_average_voltage: '0.0',
        dc1_max_voltage: '0.0',
        dc1_min_voltage: '0.0',

        // Battery (Current)
        battmetrics: [],
        battstatus: 0,
        activeError: 0,
        batt_current_amp: '0.0',
        batt_average_amp: '0.0',
        batt_max_amp: '0.0',
        batt_min_amp: '0.0',

        batt_soc: 0.0,
        charging_stage: 'Initializing...',

        // DC2 (Voltage)
        dc2metrics: [],
        dc2_current_voltage: '0.0',
        dc2_average_voltage: '0.0',
        dc2_max_voltage: '0.0',
        dc2_min_voltage: '0.0',

        // Enclosure (Temperature)
        encmetrics: [],
        enc_current_temp: '0.0',
        enc_average_temp: '0.0',
        enc_max_temp: '0.0',
        enc_min_temp: '0.0',

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
            this.getBattMetrics();
            this.getDC2Metrics();
            this.getEnclosureMetrics();
            setInterval(() => {
                this.getDC1Metrics();
                this.getBattMetrics();
                this.getDC2Metrics();
                this.getEnclosureMetrics();
            }, 500);

            this.checkNetworkStatus();
            setInterval(() => {
                this.checkNetworkStatus();
            }, 2000);

            this.loadDebugParams();
            setInterval(() => {
                this.pollLiveDutyCycles();
            }, 1000);
        },

        calcStats(dataArray) {
            if (!dataArray || dataArray.length === 0) {
                return { current: '0.0', min: '0.0', max: '0.0', avg: '0.0', avgNum: 0 };
            }
            const current = dataArray.at(-1);
            const min = Math.min(...dataArray);
            const max = Math.max(...dataArray);
            const avgNum = dataArray.reduce((sum, val) => sum + val, 0) / dataArray.length;

            return {
                current: current.toFixed(1),
                min: min.toFixed(1),
                max: max.toFixed(1),
                avg: avgNum.toFixed(1),
                avgNum: Number(avgNum.toFixed(1))
            };
        },

        // Reusable chart updater for any 2-line chart (Value + Average)
        pushToChart(chart, value, timestamp) {
            if (!chart || value === null || value === undefined) return null;

            const time = timestamp.substring(11, 19);
            const primary_dataset = chart.data.datasets[0].data;
            const avg_dataset = chart.data.datasets[1]?.data;
            const chart_labels = chart.data.labels;

            // Prevent duplicate entries
            if (value === primary_dataset.at(-1) && time === chart_labels.at(-1)) {
                return null;
            }

            chart_labels.push(time);
            primary_dataset.push(value);

            if (chart_labels.length > 50) {
                chart_labels.shift();
                primary_dataset.shift();
                if (avg_dataset) avg_dataset.shift();
            }

            const stats = this.calcStats(primary_dataset);
            if (avg_dataset) {
                avg_dataset.push(stats.avgNum);
            }

            chart.update();
            return stats;
        },

        async getDC1Metrics() {
            try {
                const res = await fetch('/api/metrics/dc1');
                if (res.ok) {
                    this.dc1metrics = await res.json();
                    if (this.dc1metrics.length > 0) {
                        this.debug.dc1_duty_cycle = this.dc1metrics[0].duty_cycle ?? 0.0;
                        const stats = this.pushToChart(window.dc1_chart, this.dc1metrics[0].voltage_value, this.dc1metrics[0].timestamp);
                        if (stats) {
                            this.dc1_current_voltage = stats.current;
                            this.dc1_min_voltage = stats.min;
                            this.dc1_max_voltage = stats.max;
                            this.dc1_average_voltage = stats.avg;
                        }
                    }
                }
            } catch (error) {
                console.error('DC1 Metrics could not be read:', error);
            }
        },

        async getBattMetrics() {
            try {
                const [battRes, socRes] = await Promise.all([
                    fetch('/api/metrics/batt'),
                    fetch('/api/metrics/soc')
                ]);

                if (battRes.ok) {
                    this.battmetrics = await battRes.json();
                    if (this.battmetrics.length > 0) {
                        if (!this.manual_status_override) {
                            this.battstatus = this.battmetrics[0].status;
                            this.activeError = this.battmetrics[0].error || 0;
                        }
                        const stats = this.pushToChart(window.batt_chart, this.battmetrics[0].current_value, this.battmetrics[0].timestamp);
                        if (stats) {
                            this.batt_current_amp = stats.current;
                            this.batt_min_amp = stats.min;
                            this.batt_max_amp = stats.max;
                            this.batt_average_amp = stats.avg;
                        }
                    }
                }

                if (socRes.ok) {
                    const socData = await socRes.json();
                    // If user manually overrides status to 2 (CHARGED), preview 100% SoC
                    this.batt_soc = (this.manual_status_override && this.battstatus == 2) ? 100.0 : socData.soc;
                    this.charging_stage = (this.manual_status_override && this.battstatus == 2) ? 'Stage 3: Float / Charged' : socData.stage;
                }
            } catch (error) {
                console.error('Battery Metrics could not be read:', error);
            }
        },

        async getDC2Metrics() {
            try {
                const res = await fetch('/api/metrics/dc2');
                if (res.ok) {
                    this.dc2metrics = await res.json();
                    if (this.dc2metrics.length > 0) {
                        this.debug.dc2_duty_cycle = this.dc2metrics[0].duty_cycle ?? 0.0;
                        const stats = this.pushToChart(window.dc2_chart, this.dc2metrics[0].voltage_value, this.dc2metrics[0].timestamp);
                        if (stats) {
                            this.dc2_current_voltage = stats.current;
                            this.dc2_min_voltage = stats.min;
                            this.dc2_max_voltage = stats.max;
                            this.dc2_average_voltage = stats.avg;
                        }
                    }
                }
            } catch (error) {
                console.error('DC2 Metrics could not be read:', error);
            }
        },

        async getEnclosureMetrics() {
            try {
                const res = await fetch('/api/metrics/enclosure');
                if (res.ok) {
                    this.encmetrics = await res.json();
                    if (this.encmetrics.length > 0) {
                        const stats = this.pushToChart(window.enc_chart, this.encmetrics[0].temp_value, this.encmetrics[0].timestamp);
                        if (stats) {
                            this.enc_current_temp = stats.current;
                            this.enc_min_temp = stats.min;
                            this.enc_max_temp = stats.max;
                            this.enc_average_temp = stats.avg;
                        }
                    }
                }
            } catch (error) {
                console.error('Enclosure Metrics could not be read:', error);
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
                // console.log(this.connectionstatus);

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

        async pollLiveDutyCycles() {
            try {
                const res = await fetch('/api/debug/params');
                if (res.ok) {
                    const data = await res.json();
                    this.debug.dc1_duty_cycle = data.dc1_duty_cycle ?? this.debug.dc1_duty_cycle;
                    this.debug.dc2_duty_cycle = data.dc2_duty_cycle ?? this.debug.dc2_duty_cycle;
                    
                    // If debug mode is disabled (user is not typing), keep setpoints/cal synced with DB
                    if (!this.debug.enabled) {
                        this.debug.dc1_setpoint = data.dc1_setpoint ?? this.debug.dc1_setpoint;
                        this.debug.dc2_setpoint = data.dc2_setpoint ?? this.debug.dc2_setpoint;
                        if (data.cal) Object.assign(this.debug.cal, data.cal);
                    }
                }
            } catch (err) {
                console.error('Could not poll live debug metrics:', err);
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