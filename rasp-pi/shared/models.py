from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, Float, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class LOCATION(Enum):
    DC1 = 0
    BATTERY = 1
    DC2 = 2
    INVERTER = 3
    ENCLOSURE = 4

class BORTO_STATUS(Enum):
    CHARGING = 0
    CHARGING_OK = 0      # Alias so both .CHARGING and .CHARGING_OK work
    DISCHARGING = 1
    DISCHARGING_OK = 1   # Alias so both .DISCHARGING and .DISCHARGING_OK work
    CHARGED = 2
    ERROR = 3

class BORTO_ERROR(Enum):
    NO_ERROR = 0
    OVER_VOLTAGE = 1
    UNDER_VOLTAGE = 2
    OVER_CURRENT = 3
    UNDER_CURRENT = 4
    OVER_TEMPERATURE = 5
    UNDER_TEMPERATURE = 6
    PWM_FAULT = 7

# Reverse-UART Command Enums (Pi -> STM32)
class CMD_TYPE(Enum):
    SET_PARAM = 0
    SET_MODE = 1
    SYS_ACTION = 2

class STM_MODE(Enum):
    STANDBY = 0
    CHARGE = 1
    DISCHARGE = 2

class SYS_ACTION(Enum):
    CLEAR_FAULT = 0
    REBOOT_MCU = 1
    SHUTDOWN = 2

class SystemMetric(Base):
    __tablename__ = "borto_metrics"

    id: Column = Column(Integer, primary_key=True, index=True)
    timestamp: Column = Column(DateTime, default=datetime.utcnow)
    value_location: Column = Column(Integer, nullable=False, index=True)
    status: Column = Column(Integer, nullable=False)
    error: Column = Column(Integer, nullable=False)
    voltage_value: Column = Column(Float, nullable=True)
    current_value: Column = Column(Float, nullable=True)
    temp_value: Column = Column(Float, nullable=True)
    duty_cycle: Column = Column(Float, nullable=True)
    setpoint: Column = Column(Float, nullable=True)
    sensor_slope: Column = Column(Float, nullable=True)
    sensor_offset: Column = Column(Float, nullable=True)

class STMCommand(Base):
    __tablename__ = "borto_commands"

    id: Column = Column(Integer, primary_key=True, index=True)
    timestamp: Column = Column(DateTime, default=datetime.utcnow)
    cmd_type: Column = Column(Integer, nullable=False, default=0) # 0=SET_PARAM, 1=SET_MODE, 2=SYS_ACTION
    target: Column = Column(Integer, nullable=False, default=0)   # Location_t, STM_MODE, or SYS_ACTION
    setpoint: Column = Column(Float, default=0.0)
    sensor_slope: Column = Column(Float, default=1.0)
    sensor_offset: Column = Column(Float, default=0.0)
    processed: Column = Column(Integer, default=0, index=True)    # 0=Pending, 1=Sent

class SystemConfig(Base):
    __tablename__ = "borto_config"

    id: Column = Column(Integer, primary_key=True) # Single row (id=1)
    device_name: Column = Column(String, default="BORTO2026")
    operating_mode: Column = Column(String, default="auto_tou") # auto_tou, ups_backup, force_charge, force_discharge
    preset: Column = Column(String, default="winter")
    off_peak_start: Column = Column(String, default="19:00")
    off_peak_end: Column = Column(String, default="07:00")
    on_peak1_start: Column = Column(String, default="07:00")
    on_peak1_end: Column = Column(String, default="11:00")
    on_peak2_start: Column = Column(String, default="17:00")
    on_peak2_end: Column = Column(String, default="19:00")
    reserve_soc: Column = Column(Integer, default=50)
    weekends_off_peak: Column = Column(Integer, default=1)

# Database Engine & Session Helper
SQLALCHEMY_DATABASE_URL = "sqlite:////app/data/borto.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)