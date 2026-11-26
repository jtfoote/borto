import time
from datetime import datetime
from shared.models import (
    init_db, SessionLocal, SystemMetric, STMCommand, SystemConfig,
    CMD_TYPE, STM_MODE, LOCATION, BORTO_STATUS, BORTO_ERROR
)
from stm_comm import STM32Comm, STMStringException
from serial_lcd import LCDController

STATUS_LABELS = {
    BORTO_STATUS.CHARGING.value: "CHARGING",
    BORTO_STATUS.DISCHARGING.value: "DISCHARGE",
    BORTO_STATUS.CHARGED.value: "CHARGED",
    BORTO_STATUS.ERROR.value: "ERROR",
}

def is_time_in_window(now_str: str, start_str: str, end_str: str) -> bool:
    if not start_str or not end_str:
        return False
    if start_str <= end_str:
        return start_str <= now_str < end_str
    else: # Overnight window (e.g., 19:00 to 07:00)
        return now_str >= start_str or now_str < end_str

def evaluate_tou_desired_mode(cfg: SystemConfig) -> int:
    if cfg.operating_mode == "force_charge":
        return STM_MODE.CHARGE.value
    if cfg.operating_mode == "force_discharge":
        return STM_MODE.DISCHARGE.value
    if cfg.operating_mode == "ups_backup":
        return STM_MODE.STANDBY.value

    # Automatic TOU Mode (auto_tou)
    now = datetime.now()
    if cfg.weekends_off_peak and now.weekday() >= 5:
        return STM_MODE.CHARGE.value

    now_hhmm = now.strftime("%H:%M")
    if is_time_in_window(now_hhmm, cfg.off_peak_start, cfg.off_peak_end):
        return STM_MODE.CHARGE.value
    if is_time_in_window(now_hhmm, cfg.on_peak1_start, cfg.on_peak1_end) or \
       is_time_in_window(now_hhmm, cfg.on_peak2_start, cfg.on_peak2_end):
        return STM_MODE.DISCHARGE.value

    return STM_MODE.STANDBY.value

def sync_metric_to_lcd(lcd: LCDController, metric: SystemMetric):
    """Updates LCDController properties from incoming STM32 telemetry."""
    lcd.status = STATUS_LABELS.get(metric.status, "UNKNOWN")

    if metric.value_location == LOCATION.DC1.value:
        if metric.voltage_value is not None:
            lcd.dc1_voltage = metric.voltage_value
        if metric.duty_cycle is not None:
            lcd.dc1_pwm = metric.duty_cycle
    elif metric.value_location == LOCATION.DC2.value:
        if metric.voltage_value is not None:
            lcd.dc2_voltage = metric.voltage_value
        if metric.duty_cycle is not None:
            lcd.dc2_pwm = metric.duty_cycle
    elif metric.value_location == LOCATION.ENCLOSURE.value:
        if metric.temp_value is not None:
            lcd.temperature = metric.temp_value

    # Trigger or clear hardware fault override automatically
    if metric.status == BORTO_STATUS.ERROR.value:
        err_name = BORTO_ERROR(metric.error).name if metric.error in [e.value for e in BORTO_ERROR] else "FAULT"
        lcd.fault_status = f"{metric.error}: {err_name}"
        lcd.write_to_lcd((f"FAULT! Code: {metric.error}", err_name))
    else:
        lcd.fault_status = "0: NO_ERROR"
        if lcd.activeError is not None:
            lcd.clear_error()

def main():
    init_db()
    stm32 = STM32Comm()
    lcd = LCDController(inactivity_timeout=60.0) # Returns to Screen 0 after 60s
    tick = 0
    last_sent_mode = None

    try:
        while True:
            db = SessionLocal()
            try:
                # 1. Read incoming telemetry from STM32 (or generate simulated cycle packet)
                if stm32.sim:
                    message = stm32.gen_message(tick % 5)
                else:
                    message = stm32.read_message()

                if message:
                    result = stm32.parse_message(message)
                    metric = result[0] if isinstance(result, tuple) else result
                    if metric:
                        db.add(metric)
                        db.commit()
                        sync_metric_to_lcd(lcd, metric)

                # 2. Transmit any pending commands queued by the web UI
                pending = db.query(STMCommand).filter(STMCommand.processed == 0).order_by(STMCommand.id).all()
                for cmd in pending:
                    stm32.send_command(cmd.cmd_type, cmd.target, cmd.setpoint, cmd.sensor_slope, cmd.sensor_offset)
                    cmd.processed = 1
                if pending:
                    db.commit()

                # 3. Every 50 ticks (~5 seconds), evaluate TOU schedule on real hardware
                if not stm32.sim and tick % 50 == 0:
                    cfg = db.query(SystemConfig).filter(SystemConfig.id == 1).first()
                    if cfg:
                        desired_mode = evaluate_tou_desired_mode(cfg)
                        if desired_mode != last_sent_mode:
                            stm32.send_command(CMD_TYPE.SET_MODE.value, desired_mode)
                            last_sent_mode = desired_mode

                # 4. Refresh active LCD values & check inactivity return every 5 ticks (0.5s)
                if tick % 5 == 0:
                    if not lcd.check_inactivity():
                        lcd.update_lcd()

            except STMStringException as e:
                print(f"[Serial Parse Warning] {e}", flush=True)
            except Exception as e:
                print(f"[Serial Loop Error] {e}", flush=True)
                db.rollback()
            finally:
                db.close()

            tick += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        if stm32.ser:
            stm32.ser.close()
        lcd.close()

if __name__ == "__main__":
    main()