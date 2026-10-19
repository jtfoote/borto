from RPLCD.i2c import CharLCD
import time

lcd = CharLCD(
    i2c_expander="PCF8574",
    address=0x27,
    port=1,
    cols=16,
    rows=2
)

def write_to_lcd(line1: str, line2: str) -> None:
    try:
        lcd.clear()
        lcd.write_string("Hello MGMT-5078!")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("From BBF Inc.")
        time.sleep(10)
    finally:
        lcd.clear()
        lcd.close()