from RPLCD.i2c import CharLCD
from gpiozero import Button
from signal import pause
import time


lcd = CharLCD(
    i2c_expander="PCF8574",
    address=0x27,
    port=1,
    cols=16,
    rows=2
)
rightButton = Button(17, pull_up=True, bounce_time=0.05)
leftButton = Button(27, pull_up=True, bounce_time=0.05)

menuIndex = 0

menu = [("Page 1", "Home"), 
        ("Page 2", "Turtle"), 
        ("Page 3", "Pig"), 
        ("Page 4", "Snake")
        ]
totalMenuCount = len(menu)

def nextMenu():
    global menuIndex
    menuIndex = (menuIndex + 1) % totalMenuCount
    update_lcd()

def previousMenu():
    global menuIndex
    menuIndex = (menuIndex - 1) % totalMenuCount
    update_lcd()

def update_lcd():
    lcd.clear()

    lcd.cursor_pos = (0, 0)
    lcd.write_string(menu[menuIndex][0][:16])

    lcd.cursor_pos = (1, 0)
    lcd.write_string(menu[menuIndex][1][:16])

rightButton.when_pressed = nextMenu
leftButton.when_pressed = previousMenu
update_lcd()

try:
    pause()

finally:
    lcd.clear()
    lcd.close()
    rightButton.close()
    leftButton.close()
