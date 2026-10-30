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
rightButton = Button(17, pull_up=True)
leftButton = Button(27, pull_up=True)

menuIndex = 0
totalMenuCount = 4
menu[("Page 1", "Home"), ("Page 2, Turtle"), ("Page 3", "Pig"), ("Page 4", "Snake")]

rightButton.when_pressed = nextMenu
leftButton.when_pressed = previousMenu
update_lcd

def nextMenu():
    global menuIndex
    menu = (menuIndex + 1) % totalMenuCount
    update_lcd()

def previousMenu():
    global menuIndex
    menu = (menuIndex - 1) % totalMenuCount
    update_lcd()

def update_lcd():
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(menu[menuIndex][0][:16])
    lcd.cursor_pos = (1, 0)
    lcd.write_string(menu[menuIndex][1][:16])

