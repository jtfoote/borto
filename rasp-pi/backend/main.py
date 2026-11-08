from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import select, desc
from shared.models import engine, SystemMetric, LOCATION, BORTO_STATUS
import json
from pydantic import BaseModel
import subprocess
from typing import Optional
import time
from datetime import datetime
import os

app = FastAPI()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# Define get_db ABOVE all route definitions that use Depends(get_db)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class WiFiCredentials(BaseModel):
    ssid: str
    password: Optional[str] = ""

class BatterySoCTracker:
    CAPACITY_AH = 5.0          # Two 12V 5Ah batteries in series = 24V, 5Ah
    CHARGE_EFFICIENCY = 0.85   # SLA charging efficiency (85%)
    
    # 24V Series Bank Voltage Thresholds (2x 12V SLA)
    V_CV_ABSORPTION = 28.8     # 14.4V per battery (CC -> CV switch point = ~80% SoC)
    V_OCV_FULL = 25.7          # 12.85V per battery resting (100% SoC)
    V_OCV_EMPTY = 23.0         # 11.50V per battery LVC (0% SoC)
    
    I_BULK_AMPS = 1.0          # 1.0A Bulk CC target
    I_TAIL_AMPS = 0.15         # 150mA tail current (100% Charged cutoff)

    def __init__(self):
        self.soc: float | None = None
        self.last_batt_id: int | None = None
        self.last_timestamp: datetime | None = None

    @classmethod
    def estimate_from_voltage_and_stage(cls, v: float, i: float, status: int) -> tuple[float, str]:
        if status == BORTO_STATUS.CHARGED.value:
            return 100.0, "Stage 3: Float / Charged"

        if status == BORTO_STATUS.CHARGING.value:
            # Stage 2: Absorption (Constant Voltage >= 28.8V, current tapering from 1.0A to 0.15A)
            if v >= (cls.V_CV_ABSORPTION - 0.2):
                i_abs = abs(i)
                taper_ratio = (cls.I_BULK_AMPS - i_abs) / (cls.I_BULK_AMPS - cls.I_TAIL_AMPS)
                taper_ratio = max(0.0, min(1.0, taper_ratio))
                return 80.0 + (20.0 * taper_ratio), "Stage 2: CV Absorption"
            # Stage 1: Bulk (Constant Current ~1.0A, voltage climbing to 28.8V -> 0% to 80% SoC)
            else:
                bulk_ratio = (v - 24.0) / (cls.V_CV_ABSORPTION - 24.0)
                bulk_ratio = max(0.0, min(1.0, bulk_ratio))
                return 80.0 * bulk_ratio, "Stage 1: CC Bulk"

        # Discharging or Standby: Open-Circuit / Loaded Voltage Lookup
        # Compensate slightly for internal resistance voltage sag under discharge load
        v_comp = v + (abs(i) * 0.35) if status == BORTO_STATUS.DISCHARGING.value else v
        ocv_ratio = (v_comp - cls.V_OCV_EMPTY) / (cls.V_OCV_FULL - cls.V_OCV_EMPTY)
        soc_est = max(0.0, min(100.0, ocv_ratio * 100.0))
        stage = "Discharging (Inverter Load)" if status == BORTO_STATUS.DISCHARGING.value else "Fault / Standby"
        return soc_est, stage

    def update(self, dc1_row: SystemMetric | None, batt_row: SystemMetric | None) -> dict:
        if not batt_row:
            return {"soc": 0.0, "stage": "Waiting for Telemetry...", "voltage": 0.0, "current": 0.0}

        v = dc1_row.voltage_value if (dc1_row and dc1_row.voltage_value is not None) else 25.0
        i = batt_row.current_value if (batt_row.current_value is not None) else 0.0
        status = batt_row.status

        curve_soc, stage = self.estimate_from_voltage_and_stage(v, i, status)

        # 1. Hard Anchor: If STM32 reports CHARGED (Status 2), lock SoC to 100%
        if status == BORTO_STATUS.CHARGED.value:
            self.soc = 100.0
            self.last_batt_id = batt_row.id
            self.last_timestamp = batt_row.timestamp
        # 2. First-time boot initialization
        elif self.soc is None:
            self.soc = curve_soc
            self.last_batt_id = batt_row.id
            self.last_timestamp = batt_row.timestamp
        # 3. New telemetry row received -> Perform Coulomb Counting + Curve Blending
        elif batt_row.id != self.last_batt_id:
            dt_hours = (batt_row.timestamp - self.last_timestamp).total_seconds() / 3600.0
            if 0 < dt_hours < 0.1:
                signed_i = abs(i) if status == BORTO_STATUS.CHARGING.value else (-abs(i) if status == BORTO_STATUS.DISCHARGING.value else 0.0)
                eff = self.CHARGE_EFFICIENCY if signed_i > 0 else 1.0
                delta_soc = (eff * signed_i * dt_hours / self.CAPACITY_AH) * 100.0
                self.soc = max(0.0, min(100.0, self.soc + delta_soc))
                
                # Blend 50% toward curve_soc so fast simulation cycles and real hardware both track accurately
                self.soc = (0.50 * self.soc) + (0.50 * curve_soc)

            self.last_batt_id = batt_row.id
            self.last_timestamp = batt_row.timestamp

        return {
            "soc": round(self.soc, 1),
            "stage": stage,
            "voltage": round(v, 2),
            "current": round(i, 2),
            "status": status
        }

soc_tracker = BatterySoCTracker()

@app.post("/api/connect-wifi")
def connect_wifi(creds: WiFiCredentials):
    request_file = "/app/host_data/connect_request.json"
    result_file = "/app/host_data/connect_result.json"

    if os.path.exists(result_file):
        os.remove(result_file)
    
    with open(request_file, 'w') as f:
        json.dump({"ssid": creds.ssid, "password": creds.password}, f)

    start_time = time.time()
    while time.time() - start_time < 20:
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                result = json.load(f)
            
            os.remove(result_file)

            if result.get("success"):
                return {"success": True, "message": "Successfully connected."}
            else:
                raise HTTPException(status_code=400, detail=result.get("error", "Failed to connect"))
            
        time.sleep(1)
    
    if os.path.exists(request_file):
        os.remove(request_file)
    raise HTTPException(status_code=504, detail="Host connection script timed out")

@app.get("/api/metrics/latest")
def get_latest_metric():
    with Session(engine) as db:
        # Fetch the most recent db entry and return
        latest = db.query(SystemMetric).order_by(SystemMetric.id.desc()).first()
        return latest

@app.get("/api/metrics/dc1")
def get_dc1_metrics(db: Session = Depends(get_db)):
    stmt = select(SystemMetric).where(SystemMetric.value_location == LOCATION.DC1.value).order_by(desc(SystemMetric.id)).limit(50)
    return db.execute(stmt).scalars().all()

@app.get("/api/metrics/batt")
def get_batt_metrics(db: Session = Depends(get_db)):
    stmt = select(SystemMetric).where(SystemMetric.value_location == LOCATION.BATTERY.value).order_by(desc(SystemMetric.id)).limit(50)
    return db.execute(stmt).scalars().all()

@app.get("/api/metrics/dc2")
def get_dc2_metrics(db: Session = Depends(get_db)):
    stmt = select(SystemMetric).where(SystemMetric.value_location == LOCATION.DC2.value).order_by(desc(SystemMetric.id)).limit(50)
    return db.execute(stmt).scalars().all()

@app.get("/api/metrics/enclosure")
def get_enclosure_metrics(db: Session = Depends(get_db)):
    stmt = select(SystemMetric).where(SystemMetric.value_location == LOCATION.ENCLOSURE.value).order_by(desc(SystemMetric.id)).limit(50)
    return db.execute(stmt).scalars().all()

@app.get("/api/metrics/soc")
def get_battery_soc(db: Session = Depends(get_db)):
    dc1_row = db.execute(
        select(SystemMetric).where(SystemMetric.value_location == LOCATION.DC1.value).order_by(desc(SystemMetric.id)).limit(1)
    ).scalars().first()
    batt_row = db.execute(
        select(SystemMetric).where(SystemMetric.value_location == LOCATION.BATTERY.value).order_by(desc(SystemMetric.id)).limit(1)
    ).scalars().first()
    return soc_tracker.update(dc1_row, batt_row)

@app.get("/api/debug/params")
def get_debug_params(db: Session = Depends(get_db)):
    """Fetches the most recent telemetry row for each location to populate Debug & Calibration UI."""
    def get_latest(loc_enum):
        stmt = select(SystemMetric).where(SystemMetric.value_location == loc_enum.value).order_by(desc(SystemMetric.id)).limit(1)
        return db.execute(stmt).scalars().first()

    dc1 = get_latest(LOCATION.DC1)
    batt = get_latest(LOCATION.BATTERY)
    dc2 = get_latest(LOCATION.DC2)
    enc = get_latest(LOCATION.ENCLOSURE)

    return {
        "dc1_setpoint": dc1.setpoint if dc1 else 0.0,
        "dc1_duty_cycle": dc1.duty_cycle if dc1 else 0.0,
        "batt_setpoint": batt.setpoint if batt else 0.0,
        "dc2_setpoint": dc2.setpoint if dc2 else 0.0,
        "dc2_duty_cycle": dc2.duty_cycle if dc2 else 0.0,
        "cal": {
            "dc1_v_slope": dc1.sensor_slope if dc1 else 1.0,
            "dc1_v_offset": dc1.sensor_offset if dc1 else 0.0,
            # Current sensor is located at BATTERY in the STM32 header
            "dc1_i_slope": batt.sensor_slope if batt else 1.0,
            "dc1_i_offset": batt.sensor_offset if batt else 0.0,
            "dc2_v_slope": dc2.sensor_slope if dc2 else 1.0,
            "dc2_v_offset": dc2.sensor_offset if dc2 else 0.0,
            "temp_slope": enc.sensor_slope if enc else 1.0,
            "temp_offset": enc.sensor_offset if enc else 0.0,
        }
    }

@app.get("/api/network-status")
def check_network_status():
    try:
        with open('/app/host_data/status.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"connected": False, "ssid": None}

class GeneralSettingsPayload(BaseModel):
    device_name: str
    operating_mode: str

class TouSettingsPayload(BaseModel):
    preset: str
    offPeakStart: str
    offPeakEnd: str
    onPeak1Start: str
    onPeak1End: str
    onPeak2Start: str = ""
    onPeak2End: str = ""
    reserveSoc: int = 50
    weekendsOffPeak: bool = True

class SetpointPayload(BaseModel):
    dc1_setpoint: float
    dc2_setpoint: float

class CalibrationPayload(BaseModel):
    dc1_v_slope: float = 1.0
    dc1_v_offset: float = 0.0
    dc1_i_slope: float = 1.0
    dc1_i_offset: float = 0.0
    dc2_v_slope: float = 1.0
    dc2_v_offset: float = 0.0
    temp_slope: float = 1.0
    temp_offset: float = 0.0

def _get_or_create_config(db: Session) -> SystemConfig:
    cfg = db.query(SystemConfig).filter(SystemConfig.id == 1).first()
    if not cfg:
        cfg = SystemConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

def _queue_param_cmd(db: Session, loc: LOCATION, setpoint: float | None = None, slope: float | None = None, offset: float | None = None):
    latest = db.execute(
        select(SystemMetric).where(SystemMetric.value_location == loc.value).order_by(desc(SystemMetric.id)).limit(1)
    ).scalars().first()
    db.add(STMCommand(
        cmd_type=CMD_TYPE.SET_PARAM.value,
        target=loc.value,
        setpoint=setpoint if setpoint is not None else (latest.setpoint if latest and latest.setpoint is not None else 0.0),
        sensor_slope=slope if slope is not None else (latest.sensor_slope if latest and latest.sensor_slope is not None else 1.0),
        sensor_offset=offset if offset is not None else (latest.sensor_offset if latest and latest.sensor_offset is not None else 0.0),
    ))

@app.post("/api/settings/general")
def save_general_settings(payload: GeneralSettingsPayload, db: Session = Depends(get_db)):
    cfg = _get_or_create_config(db)
    cfg.device_name = payload.device_name
    cfg.operating_mode = payload.operating_mode

    # If user picked an explicit manual mode, immediately queue the STM32 mode command
    mode_map = {
        "ups_backup": STM_MODE.STANDBY.value,
        "force_charge": STM_MODE.CHARGE.value,
        "force_discharge": STM_MODE.DISCHARGE.value,
    }
    if payload.operating_mode in mode_map:
        db.add(STMCommand(cmd_type=CMD_TYPE.SET_MODE.value, target=mode_map[payload.operating_mode]))

    db.commit()
    return {"status": "ok"}

@app.post("/api/settings/tou")
def save_tou_settings(payload: TouSettingsPayload, db: Session = Depends(get_db)):
    cfg = _get_or_create_config(db)
    cfg.preset = payload.preset
    cfg.off_peak_start = payload.offPeakStart
    cfg.off_peak_end = payload.offPeakEnd
    cfg.on_peak1_start = payload.onPeak1Start
    cfg.on_peak1_end = payload.onPeak1End
    cfg.on_peak2_start = payload.onPeak2Start
    cfg.on_peak2_end = payload.onPeak2End
    cfg.reserve_soc = payload.reserveSoc
    cfg.weekends_off_peak = 1 if payload.weekendsOffPeak else 0
    db.commit()
    return {"status": "ok"}

@app.post("/api/system/{action}")
def execute_system_power(action: str, db: Session = Depends(get_db)):
    if action == "reboot":
        db.add(STMCommand(cmd_type=CMD_TYPE.SYS_ACTION.value, target=SYS_ACTION.REBOOT_MCU.value))
    elif action == "shutdown":
        db.add(STMCommand(cmd_type=CMD_TYPE.SYS_ACTION.value, target=SYS_ACTION.SHUTDOWN.value))
    elif action == "clear_fault":
        db.add(STMCommand(cmd_type=CMD_TYPE.SYS_ACTION.value, target=SYS_ACTION.CLEAR_FAULT.value))
    else:
        raise HTTPException(status_code=400, detail="Invalid system action")
    db.commit()
    return {"status": f"{action} command queued for STM32"}

@app.post("/api/debug/setpoints")
def update_debug_setpoints(payload: SetpointPayload, db: Session = Depends(get_db)):
    _queue_param_cmd(db, LOCATION.DC1, setpoint=payload.dc1_setpoint)
    _queue_param_cmd(db, LOCATION.DC2, setpoint=payload.dc2_setpoint)
    db.commit()
    return {"status": "queued"}

@app.post("/api/debug/calibration")
def update_debug_calibration(payload: CalibrationPayload, db: Session = Depends(get_db)):
    _queue_param_cmd(db, LOCATION.DC1, slope=payload.dc1_v_slope, offset=payload.dc1_v_offset)
    _queue_param_cmd(db, LOCATION.BATTERY, slope=payload.dc1_i_slope, offset=payload.dc1_i_offset)
    _queue_param_cmd(db, LOCATION.DC2, slope=payload.dc2_v_slope, offset=payload.dc2_v_offset)
    _queue_param_cmd(db, LOCATION.ENCLOSURE, slope=payload.temp_slope, offset=payload.temp_offset)
    db.commit()
    return {"status": "queued"}