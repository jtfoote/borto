
from RPLCD.i2c import CharLCD
from gpiozero import Button
from signal import pause


class LCDController:

    def __init__(self):

        # Initialize LCD
        self.lcd = CharLCD(
            i2c_expander="PCF8574",
            address=0x27,
            port=1,
            cols=16,
            rows=2
        )

        # Initialize buttons
        self.rightButton = Button(17, pull_up=True, bounce_time=0.05)
        self.leftButton = Button(27, pull_up=True, bounce_time=0.05)

        # Menu settings
        self.menuIndex = 0
        self.menu = [
            ("Page 1", "Home"),
            ("Page 2", "Turtle"),
            ("Page 3", "Pig"),
            ("Page 4", "Snake")
        ]

        # No error initially
        self.activeError = None

        # Assign button functions
        self.rightButton.when_pressed = self.nextMenu
        self.leftButton.when_pressed = self.previousMenu

        # Display initial menu
        self.update_lcd()


    def nextMenu(self):

        # Ignore button presses during an error
        if self.activeError is not None:
            return

        self.menuIndex = (self.menuIndex + 1) % len(self.menu)
        self.update_lcd()


    def previousMenu(self):

        # Ignore button presses during an error
        if self.activeError is not None:
            return

        self.menuIndex = (self.menuIndex - 1) % len(self.menu)
        self.update_lcd()


    def update_lcd(self):

        # Determine what should be displayed
        if self.activeError is None:
            message = self.menu[self.menuIndex]
        else:
            message = self.activeError

        # Update LCD
        self.lcd.clear()

        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string(message[0][:16])

        self.lcd.cursor_pos = (1, 0)
        self.lcd.write_string(message[1][:16])


    def write_to_lcd(self, message):

        # Validate message
        if (not isinstance(message, (list, tuple))
                or len(message) != 2
                or not all(isinstance(line, str) for line in message)):
            raise ValueError("Message must contain two strings")

        # Store error message and update display
        self.activeError = message
        self.update_lcd()


    def clear_error(self):

        # Remove error and return to menu
        self.activeError = None
        self.update_lcd()


    def close(self):

        # Release hardware resources
        self.rightButton.when_pressed = None
        self.leftButton.when_pressed = None

        self.rightButton.close()
        self.leftButton.close()

        self.lcd.clear()
        self.lcd.close()


# Run only when this file is executed directly
if __name__ == "__main__":

    controller = LCDController()

    try:
        pause()

    finally:
        controller.close()