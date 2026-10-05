from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from datetime import datetime
from enum import Enum

# Init sqlalchemy base class
Base = declarative_base()

class SystemMetric(Base):
    __tablename__ = "borto_telemetry"

    # Primary key
    id: Column = Column(Integer, primary_key=True, index=True)

    # Time stamp
    timestamp: Column = Column(DateTime, default=datetime.utcnow, index=True)

    # Value type
    value_type: Column = Column(Integer, nullable=False)

    # Value
    value: Column = Column(Float, nullable=False)

    # Location
    value_location: Column = Column(Integer, nullable=False)

    # Status from BORTO
    status: Column = Column(Integer, default="NORMAL")

# Point database to location specified in docker-compose.yml
SQLACHEMY_DATABASE_URL = "sqlite:////app/data/borto.db"

engine = create_engine(
    SQLACHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

class VAL_TYPE(Enum):
    VOLTAGE = 1
    CURRENT = 2
    POWER = 3
    TEMPERATURE = 4

class LOCATION(Enum):
    RECTIFIER = 1
    DC1 = 2
    BATTERY = 3
    DC2 = 4
    INVERTER = 5
    ENCLOSURE = 6

class BORTO_STATUS(Enum):
    OK = 1
    FAULT = 2


def init_db() -> None:
    """
    Creates the data base and tables if they don't already exist.
    """
    Base.metadata.create_all(bind=engine)

