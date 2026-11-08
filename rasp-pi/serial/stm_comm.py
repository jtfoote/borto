import random
import serial
from math import sin
from shared.models import (
    SystemMetric, LOCATION, BORTO_STATUS, BORTO_ERROR,
    CMD_TYPE, STM_MODE, SYS_ACTION
)

class STMStringException(Exception):
    """Exception raised when string parsing fails"""

    def __init__(self, message: str, error_code: int):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Error Code: {self.error_code})"

class STM32Comm:
    # --- Tunable Simulation Step Resolution ---
    # Smaller SoC steps = more data points per phase!
    CHARGE_STEP_SOC = 0.4       # 0.4% per sweep -> 250 steps (200 in Bulk CC, 50 in Absorption CV)
    CHARGED_HOLD_SWEEPS = 25    # Hold on CHARGED (Status 2) for 25 sweeps
    DISCHARGE_STEP_SOC = 0.5    # 0.5% per sweep -> 200 steps from 100% down to 0%

    def __init__(self, port="/dev/serial0", baud_rate=9600):
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=1)
            self.sim = 0
        except serial.SerialException:
            self.ser = None
            self.sim = 1

        self.sim_soc = 0.0
        self.sim_state = BORTO_STATUS.CHARGING.value
        self.sim_charged_ticks = 0
        self.sim_temp = 28.0

    def send_command(self, cmd_type: int, target: int, setpoint: float = 0.0, slope: float = 1.0, offset: float = 0.0) -> str:
        """Formats and transmits 'nc<cmd_type>,<target>,<v1>,<v2>,<v3>ec\\r\\n' to the STM32."""
        if cmd_type == CMD_TYPE.SET_PARAM.value:
            v1 = int(round(setpoint * 1000))
            v2 = int(round(slope * 1000))
            v3 = int(round(offset * 1000))
            self.sim_overrides[target] = {"setpoint": v1, "slope": v2, "offset": v3}
        else:
            v1, v2, v3 = 0, 0, 0
            # Update simulation state when user manually forces a mode or reboots
            if cmd_type == CMD_TYPE.SET_MODE.value:
                if target == STM_MODE.CHARGE.value:
                    self.sim_state = BORTO_STATUS.CHARGING_OK.value
                elif target == STM_MODE.DISCHARGE.value:
                    self.sim_state = BORTO_STATUS.DISCHARGING_OK.value
                elif target == STM_MODE.STANDBY.value:
                    self.sim_state = BORTO_STATUS.CHARGED.value
            elif cmd_type == CMD_TYPE.SYS_ACTION.value and target == SYS_ACTION.REBOOT_MCU.value:
                self.sim_soc = 0.0
                self.sim_state = BORTO_STATUS.CHARGING_OK.value

        packet = f"nc{cmd_type},{target},{v1},{v2},{v3}ec\r\n"
        if not self.sim and self.ser:
            self.ser.write(packet.encode("utf-8"))
            self.ser.flush()

        print(f"[UART TX -> STM32] {packet.strip()}", flush=True)
        return packet

    def _step_simulation(self):
        """Advances the battery state machine once per full 5-location sweep."""
        if self.sim_state == BORTO_STATUS.CHARGING.value:
            self.sim_soc += self.CHARGE_STEP_SOC
            self.sim_temp = min(42.0, self.sim_temp + 0.03)
            if self.sim_soc >= 100.0:
                self.sim_soc = 100.0
                self.sim_state = BORTO_STATUS.CHARGED.value
                self.sim_charged_ticks = 0

        elif self.sim_state == BORTO_STATUS.CHARGED.value:
            self.sim_charged_ticks += 1
            self.sim_temp = max(28.0, self.sim_temp - 0.05)
            if self.sim_charged_ticks >= self.CHARGED_HOLD_SWEEPS:
                self.sim_state = BORTO_STATUS.DISCHARGING.value

        elif self.sim_state == BORTO_STATUS.DISCHARGING.value:
            self.sim_soc -= self.DISCHARGE_STEP_SOC
            self.sim_temp = min(45.0, self.sim_temp + 0.04)
            if self.sim_soc <= 0.0:
                self.sim_soc = 0.0
                self.sim_state = BORTO_STATUS.CHARGING.value

    def gen_message(self, location: int) -> str:
        # Step the state machine once at the start of each 5-location group
        if location == LOCATION.DC1.value:
            self._step_simulation()

        status = self.sim_state
        error = BORTO_ERROR.NO_ERROR.value
        voltage = 0
        current = 0
        temp = 0
        duty_cycle = 0
        setpoint = 0
        slope = 1000
        offset = 0

        # Calculate realistic physical values based on current state & SoC
        if status == BORTO_STATUS.CHARGING.value:
            if self.sim_soc <= 80.0:
                # Stage 1: Bulk CC (1.0A constant, Voltage rises 24.0V -> 28.8V)
                v_dc1 = 24.0 + (self.sim_soc / 80.0) * (28.8 - 24.0)
                i_batt = 1.0
                dc1_setpoint_mv = 1000  # 1.0A CC target
            else:
                # Stage 2: Absorption CV (28.8V constant, Current tapers 1.0A -> 0.15A)
                v_dc1 = 28.8
                taper = (self.sim_soc - 80.0) / 20.0
                i_batt = 1.0 - taper * (1.0 - 0.15)
                dc1_setpoint_mv = 28800 # 28.8V CV target
            dc1_pwm = int((v_dc1 / 36.0) * 1000)
            dc2_pwm = 0
            inv_pwm = 0

        elif status == BORTO_STATUS.CHARGED.value:
            # Stage 3: Float Maintenance (27.2V float, ~0.05A trickle)
            v_dc1 = 27.2
            i_batt = 0.05
            dc1_setpoint_mv = 27200
            dc1_pwm = int((v_dc1 / 36.0) * 1000)
            dc2_pwm = 0
            inv_pwm = 0

        else: # DISCHARGING
            # Loaded voltage sags from 25.35V (100%) down to 22.65V (0% under 1.0A load)
            v_ocv = 23.0 + (self.sim_soc / 100.0) * (25.7 - 23.0)
            i_batt = -1.0
            v_dc1 = v_ocv - (abs(i_batt) * 0.35)
            dc1_setpoint_mv = 0
            dc1_pwm = 0
            dc2_pwm = 620  # 62.0% Boost duty cycle active
            inv_pwm = 500  # 50.0% Inverter duty cycle active

        match location:
            case LOCATION.DC1.value: # 0
                voltage = int(random.gauss(v_dc1, 0.008) * 1000)
                duty_cycle = dc1_pwm
                setpoint = dc1_setpoint_mv
            case LOCATION.BATTERY.value: # 1
                current = int(random.gauss(i_batt, 0.004) * 1000)
                setpoint = 1000 if status == BORTO_STATUS.CHARGING.value else -1000
            case LOCATION.DC2.value: # 2
                v_dc2 = 39.6 if status == BORTO_STATUS.DISCHARGING.value else v_dc1
                voltage = int(random.gauss(v_dc2, 0.01) * 1000)
                duty_cycle = dc2_pwm
                setpoint = 39600
            case LOCATION.INVERTER.value: # 3
                duty_cycle = inv_pwm
            case LOCATION.ENCLOSURE.value: # 4
                temp = int(random.gauss(self.sim_temp, 0.03) * 10)
            case _:
                raise Exception(f"'{location}' is not a valid location.")

        return f"ne{location},{status},{error},{voltage},{current},{temp},{duty_cycle},{setpoint},{slope},{offset}ee"

    @staticmethod
    def parse_message(message: str) -> tuple[SystemMetric, int]:
        message = message.strip()
        
        if not message.startswith('ne') or not message.endswith('ee'):
            raise STMStringException("Invalid string wrapper.", 1)
        
        payload = message[2:-2]
        parts = payload.split(',')
        
        if len(parts) != 10:
            raise STMStringException(f"Invalid field count: expected 10, got {len(parts)}", 2)
            
        try:
            location = int(parts[0])
            status = int(parts[1])
            error = int(parts[2])
            voltage_mv = int(parts[3])
            current_ma = int(parts[4])
            temp_dt = int(parts[5])
            duty_cycle_dp = int(parts[6])
            setpoint_raw = int(parts[7])
            slope_raw = int(parts[8])
            offset_raw = int(parts[9])
        except ValueError:
            raise STMStringException("Invalid data type in payload fields.", 3)

        # Initialize defaults for location-specific metrics
        voltage = None
        current = None
        temp = None

        # Convert raw integers into standard float units (V, A, °C, %)
        duty_cycle = duty_cycle_dp / 10.0
        setpoint = setpoint_raw / 1000.0 # Converts mV or mA to V or A
        sensor_slope = float(slope_raw)
        sensor_offset = float(offset_raw)

        # Assign primary metrics based on location enum
        match location:
            case LOCATION.DC1.value | LOCATION.DC2.value | LOCATION.INVERTER.value:
                voltage = voltage_mv / 1000.0
            case LOCATION.BATTERY.value:
                voltage = voltage_mv / 1000.0
                current = current_ma / 1000.0
            case LOCATION.ENCLOSURE.value:
                temp = temp_dt / 10.0
            case _:
                raise STMStringException(f"Location ID '{location}' invalid.", 6)

        return SystemMetric(
            voltage_value=voltage,
            current_value=current,
            temp_value=temp,
            duty_cycle=duty_cycle,
            setpoint=setpoint,
            sensor_slope=sensor_slope,
            sensor_offset=sensor_offset,
            value_location=location,
            status=status,
            error=error
        ), status

    def close(self):
        if self.ser:
            self.ser.close()