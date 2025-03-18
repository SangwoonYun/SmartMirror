# modules/clock.py

from module import BaseModule
from config import MODULE_LAYOUT


class ClockModule(BaseModule):
    """Clock module that displays the current time with real-time updates and configurable styling.

    This module inherits from BaseModule and implements the render method to return
    an HTML formatted string. The style of the clock (e.g., text size, font family) is
    configurable via the configuration file.
    """

    @property
    def name(self):
        """Get the unique name of the module.

        Returns:
            str: The module name 'clock'.
        """
        return 'clock'

    def render(self):
        """Render the module's UI as an HTML string with real-time clock updates and configurable style.

        Retrieves the text size and font family from the configuration and applies them
        as inline styles to the clock container. Also includes a JavaScript snippet that
        updates the time every second.

        Returns:
            str: HTML content representing the clock with real-time updates.
        """
        # Retrieve the clock configuration
        clock_config = MODULE_LAYOUT.get(self.name, {})
        time_format = clock_config.get('time_format', '%H:%M:%S')
        refresh_interval = clock_config.get('refresh_interval', 100)
        options = clock_config.get('options', {})
        style = " ".join(f"{key}: {value};" for key, value in options.items())

        html = (
            f"<div id='clock-module' class='clock' style='{style}'>"
            "  <span id='clock-time'></span>"
            "</div>"
            "<script>"
            "  var timeFormat = '" + time_format + "';"
            "  function formatTime(now, format) {"
            "    return format.replace('%H', String(now.getHours()).padStart(2, '0'))"
            "                 .replace('%M', String(now.getMinutes()).padStart(2, '0'))"
            "                 .replace('%S', String(now.getSeconds()).padStart(2, '0'));"
            "  }"
            "  function updateClock() {"
            "    var now = new Date();"
            "    document.getElementById('clock-time').innerText = formatTime(now, timeFormat);"
            "  }"
            "  updateClock();"
            f"  setInterval(updateClock, {refresh_interval});"
            "</script>"
        )
        return html

    def update(self):
        """Update the module's state.

        This method can be overridden if dynamic updates are required.
        For this clock module, no additional action is performed.
        """
        pass


def get_module():
    """Factory function to create and return an instance of ClockModule.

    Returns:
        ClockModule: An instance of ClockModule.
    """
    return ClockModule()

