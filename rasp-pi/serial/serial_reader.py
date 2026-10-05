from sqlalchemy.orm import Session
from shared.models import engine, SystemMetric, init_db, VAL_TYPE, LOCATION, BORTO_STATUS
import time
import serial
import time
import random
from math import sin

# initialize db if it hasn't been already
init_db()
# Simulation flag
SIMULATION_MODE = False
# Check for serial port
try:
    serial_port = serial.Serial(port="/dev/serial0", baudrate=115200, timeout=1)
except serial.SerialException:
    print("WARNING: Hardware not found, entering laptop simulation mode.")
    SIMULATION_MODE = True

def generate_voltage_val(location: LOCATION, time: int) -> float:
    match location:
        case LOCATION.RECTIFIER:
            return random.uniform(35.0,37.0)
        case LOCATION.DC1 | LOCATION.BATTERY:
            return random.uniform(22.5,25.0)
        case LOCATION.DC2:
            return random.uniform(39.0,40.0)
        case _: # Inverter location
            return 39.6*sin(time)

def generate_current_val(location: LOCATION, time: int) -> float:
    match location:
        case LOCATION.RECTIFIER:
            return random.uniform(3,5)
        case LOCATION.DC1:
            return random.uniform(4,6)
        case LOCATION.BATTERY:
            return random.uniform(-1.5,4)
        case LOCATION.DC2:
            return random.uniform(2,4)
        case _: # Inverter location
            return 0.707*sin(time)

def read_and_store_metrics() -> None:
    # Loop tick
    tick = 0
    with Session(engine) as db:
        while True:
            tick += 1
            # Reset values
            value: float = 0.0
            try:
                if SIMULATION_MODE:
                    # Generate fake data for testing
                    value_type: VAL_TYPE = VAL_TYPE(random.randint(1,4))
                    location: LOCATION = LOCATION(random.randint(1,5))
                    status: BORTO_STATUS = BORTO_STATUS.OK
                    match value_type:
                        case VAL_TYPE.VOLTAGE:
                            value = generate_voltage_val(location, tick)
                        case VAL_TYPE.CURRENT:
                            value = generate_current_val(location, tick)
                        case VAL_TYPE.POWER:
                            value = generate_current_val(location,tick) * generate_voltage_val(location, tick)
                        case VAL_TYPE.TEMPERATURE:
                            value = random.uniform(20,26)
                            location = LOCATION.ENCLOSURE
                    data = {
                        'value_type': value_type,
                        'location' : location,
                        'value' : value,
                        'status' : status
                    }
                    time.sleep(0.5)
                else:
                    # TODO implement real hardware read logic here
                    time.sleep(0.5)
                    continue
                
                new_metric = SystemMetric(
                    value_type=data['value_type'].value, 
                    value=data['value'], 
                    value_location=data['location'].value,
                    status=data['status'].value
                )
                db.add(new_metric)
                db.commit()

            except Exception as e:
                print(f'Error: {e}')
            

if __name__ == '__main__':
    read_and_store_metrics()
    
