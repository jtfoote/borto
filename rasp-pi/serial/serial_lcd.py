import time
import threading
from RPLCD.i2c import CharLCD
from gpiozero import Button
from signal import pause


class LCDController:

    def __init__(self, inactivity_timeout: float = 60.0):
        self._lock = threading.Lock()
        self.inactivity_timeout = inactivity_timeout
        self.last_press_time = time.monotonic()

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

        # Variables for menu display
        self.status = "STANDBY"
        self.local_ip = "10.42.0.1"
        self.battery_soc = 100
        self.dc1_voltage = 0.0
        self.dc1_pwm = 0.0
        self.dc2_voltage = 0.0
        self.dc2_pwm = 0.0
        self.temperature = 0.0
        self.tou_mode = "Auto TOU"
        self.fault_status = "0: NO_ERROR"

        # Menu state
        self.menu_count = 7
        self.menuIndex = 0
        self.activeError = None
        self._last_rendered = ("", "")

        # Assign button functions
        self.rightButton.when_pressed = self.nextMenu
        self.leftButton.when_pressed = self.previousMenu

        # Display initial menu
        self.update_lcd(force=True)

    def _get_menu_screen(self, index: int) -> tuple[str, str]:
        """Builds the current menu strings dynamically so live telemetry shows up."""
        menus = [
            ("B.O.R.T.O. Ready", f"State: {self.status}"),
            ("Local IP", str(self.local_ip)),
            ("Battery Charge", f"SoC: {self.battery_soc}%"),
            ("DC1 Charger Bus", f"{self.dc1_voltage:.1f}V PWM:{self.dc1_pwm:.0f}%"),
            ("DC2 Boost (TP5)", f"{self.dc2_voltage:.1f}V PWM:{self.dc2_pwm:.0f}%"),
            (f"Temp: {self.temperature:.1f} C", f"Mode: {self.tou_mode}"),
            ("Fault Status", str(self.fault_status)),
        ]
        return menus[index % len(menus)]

    def nextMenu(self):
        self.last_press_time = time.monotonic()
        if self.activeError is not None:
            return
        self.menuIndex = (self.menuIndex + 1) % self.menu_count
        self.update_lcd()

    def previousMenu(self):
        self.last_press_time = time.monotonic()
        if self.activeError is not None:
            return
        self.menuIndex = (self.menuIndex - 1) % self.menu_count
        self.update_lcd()

    def check_inactivity(self) -> bool:
        """
        Called periodically from main.py.
        Returns the display to Screen 0 if no button was pressed within inactivity_timeout.
        """
        if self.activeError is not None or self.menuIndex == 0:
            return False

        if (time.monotonic() - self.last_press_time) >= self.inactivity_timeout:
            self.menuIndex = 0
            self.update_lcd()
            return True
        return False

    def update_lcd(self, force: bool = False):
        with self._lock:
            if self.activeError is None:
                raw_line1, raw_line2 = self._get_menu_screen(self.menuIndex)
            else:
                raw_line1, raw_line2 = self.activeError

            # Pad to 16 chars to overwrite old characters without lcd.clear() flicker
            line1 = str(raw_line1)[:16].ljust(16)
            line2 = str(raw_line2)[:16].ljust(16)

            if not force and (line1, line2) == self._last_rendered:
                return

            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(line1)
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2)
            self._last_rendered = (line1, line2)

    def write_to_lcd(self, message):
        if (not isinstance(message, (list, tuple))
                or len(message) != 2
                or not all(isinstance(line, str) for line in message)):
            raise ValueError("Message must contain two strings")

        self.activeError = (message[0], message[1])
        self.update_lcd()

    def clear_error(self):
        self.activeError = None
        self.update_lcd()

    def close(self):
        self.rightButton.when_pressed = None
        self.leftButton.when_pressed = None
        self.rightButton.close()
        self.leftButton.close()
        with self._lock:
            self.lcd.clear()
            self.lcd.close()


if __name__ == "__main__":
    controller = LCDController()
    try:
        pause()
    finally:
        controller.close()