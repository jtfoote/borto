import random
import serial
from math import sin
from shared.models import SystemMetric

class STMStringException(Exception):
    """Exception raised when string parsing fails"""

    def __init__(self, message: str, error_code: int):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (Error Code: {self.error_code})"

class STM32Comm:
    def __init__(self, port="/dev/serial0", baud_rate=9600):
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=1)
            # set simulation flag to zero since serial connection succeeded
            self.sim = 0 
        except serial.SerialException:
            self.ser = None
            # set simulation flag to one since serial connection failed
            self.sim = 1
    
    def read_message(self):
        if not self.sim and self.ser.in_waiting > 0:
            return self.ser.readline().decode('utf-8').rstrip()
        
    def gen_message(self, location: int) -> str:
        match location:
            case 1: # DC1, Voltage only
                voltage = random.gauss(25,0.6)
                return f"ne1{voltage:06.3f}V01See"
            case 2: # Battery, Voltage and Current
                voltage = random.gauss(25,0.6)
                current = random.gauss(1, 0.05)
                status = 1
                return f"ne2{voltage:06.3f}V{current:06.3f}A{status:02}See"
            case 3: # DC2, Voltage only
                voltage = random.gauss(39.6,0.3)
                return f"ne3{voltage:06.3f}V01See"
            case 4: # Inverter, voltage only
                voltage = 39.6*sin(120*3.1415*random.uniform(0,0.017))
                return f"ne4{voltage:06.3f}V01See"
            case 5:
                temp = random.gauss(35, 6)
                return f"ne5{temp:06.3f}C01See"
            case _:
                raise STMStringException(f"'{location}' is not a valid location.", 7)

    @staticmethod
    def parse_message(message: str) -> tuple[SystemMetric, int]:
        # Ensure message is valid
        if message[0:2] != 'ne' or message[-2:] != 'ee':
            raise STMStringException("Invalid string.", 1)
        parsed_message = message[2:] # Copy the string, remove 'ne'
        # First part of string will be the location ID
        try:
            location = int(parsed_message[0])
        except ValueError:
            raise STMStringException(f"Location ID '{parsed_message[0]}' invalid.", 2)
        parsed_message = parsed_message[1:] # Remove location ID
        # Next 6 characters are a float value with the value indicator at the 7th character
        try:
            value = float(parsed_message[0:6])
        except ValueError:
            raise STMStringException(f"Value '{parsed_message[0:6]}' invalid.", 3)
        value_type = parsed_message[6]
        # The first value_type will always be voltage unless the location is enclosure
        parsed_message = parsed_message[7:]
        # At this point, the message should only contain the status and 'ee' unless location is battery
        # Status will always be in this location
        try:
            status = int(parsed_message[-5:-3])
        except ValueError:
            raise STMStringException(f"Status value '{parsed_message[-5:-3]}' invalid.", 5)
        match location:
            case 1 | 3 | 4: # DC1 or DC2 or INV
                voltage = value
                current = None
                temp = None
            case 2: # Battery
                voltage = value
                try:
                    # Battery is the only location that contains two values
                    current = float(parsed_message[0:6])
                except ValueError:
                    raise STMStringException(f"Current value '{parsed_message[0:6]}' invalid.", 4)
                temp = None
            case 5: # Enclosure
                temp = value
                voltage = None
                current = None
        return SystemMetric(
            voltage_value=voltage,
            current_value=current,
            temp_value=temp,
            value_location=location,
            status=status
        ), status

    def close(self):
        self.ser.close()