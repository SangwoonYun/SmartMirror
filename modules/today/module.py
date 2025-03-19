# modules/today.py

import os
from datetime import datetime

from module import BaseModule
from config import MODULE_LAYOUT


class TodayModule(BaseModule):
    """Module that displays today's date with dynamic updates.

    This module inherits from BaseModule and implements the render method to return
    an HTML formatted string that shows today's date. The style of the module, including
    any additional CSS options, is configurable via the configuration file.
    """

    @property
    def name(self):
        """Get the unique name of the module.

        Returns:
            str: The module name 'today'.
        """
        return 'today'

    def render(self):
        """Render the module's UI as an HTML string with dynamic date updates.

        Retrieves style settings (text size, font family, and additional CSS options)
        from the configuration and applies them as inline styles. The module displays
        today's date and updates it every minute.

        Returns:
            str: HTML content representing today's date.
        """
        # Retrieve today's module configuration
        today_config = MODULE_LAYOUT.get(self.name, {})
        date_format = today_config.get('date_format', '%Y-%m-%d')
        refresh_interval = today_config.get('refresh_interval', 100)
        options = today_config.get('options', {})
        style = " ".join(f"{key}: {value};" for key, value in options.items())
        today_date = datetime.now().strftime(date_format)
        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            style=style,
            date_format=today_date,
            refresh_interval=refresh_interval
        )

    def update(self):
        """Update the module's state.

        This method can be overridden if dynamic updates are required.
        For this today module, no additional action is performed.
        """
        pass


def get_module():
    """Factory function to create and return an instance of TodayModule.

    Returns:
        TodayModule: An instance of TodayModule.
    """
    return TodayModule()

