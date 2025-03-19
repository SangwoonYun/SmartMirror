# modules/clock.py

import os

from config import MODULE_LAYOUT
from module import BaseModule


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
        """
        Render the module's UI as an HTML string with real-time clock updates and configurable
        style.

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
        style = ' '.join(f'{key}: {value};' for key, value in options.items())
        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            style=style,
            time_format=time_format,
            refresh_interval=refresh_interval
        )


def get_module():
    """Factory function to create and return an instance of ClockModule.

    Returns:
        ClockModule: An instance of ClockModule.
    """
    return ClockModule()

