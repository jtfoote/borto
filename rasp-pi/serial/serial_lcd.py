from RPLCD.i2c import CharLCD
from gpiozero import button
from signal import pause
import time


lcd = CharLCD(
    i2c_expander="PCF8574",
    address=0x27,
    port=1,
    cols=16,
    rows=2
)
button = Button(17)

pages = [("Welcome User!", "Right Button: >"), ("Page 2", "Button Works")]

pages_index = 0;

def update_lcd():
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(pages[page_index][0])
    lcd.cursor_pos = (1, 0)
    lcd.write_string(pages[page_index][1])

def next_page():
    global page_index
    page_index = (page_index + 1) % len(pages)
    update_lcd()