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
    serial_port = serial.Serial(
        port="/dev/serial0", 
        baudrate=9600,
        timeout=1
    )
except serial.SerialException:
    print("WARNING: Hardware not found, entering laptop simulation mode.", flush=True)
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
                    location: LOCATION = LOCATION(random.randint(1,5))
                    status: BORTO_STATUS = BORTO_STATUS.OK
                    if location != LOCATION.ENCLOSURE:
                        voltage = generate_voltage_val(location, tick)
                        current = generate_current_val(location, tick)
                        power = voltage * current
                        values = [voltage, current, power]
                        value_types = [VAL_TYPE.VOLTAGE, VAL_TYPE.CURRENT, VAL_TYPE.POWER]
                    else:
                        temperature = random.uniform(20,30)
                        values = [temperature]
                    data = {
                        'value_type': value_types,
                        'location' : location,
                        'values' : values,
                        'status' : status
                    }
                    time.sleep(0.5)
                else:
                    try:
                        while True:
                            if serial_port.in_waiting > 0:
                                # Read the line, decode bytes to string, and strip trailing whitespace
                                message = serial_port.readline().decode('utf-8').rstrip()
                                #print(message, flush=True)
                                # Process string
                                if message[0:2] != "ne":
                                    # want to make sure this is a valid string
                                    continue
                                while message != 'ee':
                                    message = message[2:] # Remove 'ne' for new entry
                                    if message[0:3] == 'DC1': # This is a dc1 entry
                                        location = LOCATION.DC1
                                        message = message[3:] # Remove location identifier
                                        value_str = message[0:6] # The next 6 characters are a float value
                                        value = float(value_str)
                                        message = message[7:] # Remove the value from the string
                                        
                                        new_metric = SystemMetric(
                                            voltage_value=value,
                                            current_value=0,
                                            power_value=0,
                                            value_location=location.value,
                                            status=BORTO_STATUS.OK.value
                                        )
                                        db.add(new_metric)
                                        db.commit()
                                        continue
                                    if message[0:3] == "BAT": # This is a battery entry
                                        location = LOCATION.BATTERY
                                        message = message[3:]
                                        value_str = message[0:6]
                                        value = float(value_str)
                                        message = message[7:]

                                        new_metric = SystemMetric(
                                            voltage_value=value,
                                            current_value=0,
                                            power_value=0,
                                            value_location=location.value,
                                            status=BORTO_STATUS.OK.value
                                        )
                                        db.add(new_metric)
                                        db.commit()
                                        continue
                                    if len(message) < 2:
                                        break
                    except KeyboardInterrupt:
                        serial_port.close()
                    continue    
                
                new_metric = SystemMetric(
                    voltage_value=data['values'][0],
                    current_value=data['values'][1],
                    power_value=data['values'][2],
                    value_location=data['location'].value,
                    status=data['status'].value
                )
                db.add(new_metric)
                db.commit()
                

            except Exception as e:
                print(f'Error: {e}', flush=True)
            

if __name__ == '__main__':
    read_and_store_metrics()
    
