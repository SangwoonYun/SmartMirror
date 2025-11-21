# modules/today.py

import os

from config import MODULE_LAYOUT
from module import BaseModule


class TodayModule(BaseModule):
    """Today module that displays the current date with real-time updates and configurable styling.

    This module inherits from BaseModule and implements the render method to return
    an HTML formatted string. The style of the today (e.g., text size, font family) is
    configurable via the configuration file.

    성능 최적화:
        - 기본 refresh_interval: 60000ms (1분 단위 업데이트)
        - ISO 계산: lazy 실행 (필요할 때만)
        - 공통 포맷터 사용: datetime_formatter.js
    """

    # 상수 정의
    DEFAULT_REFRESH_INTERVAL = 60000  # 1분 (밀리초)

    @property
    def name(self):
        """Get the unique name of the module.

        Returns:
            str: The module name 'today'.
        """
        return 'today'

    def render(self):
        """
        Render the module's UI as an HTML string with real-time date updates and configurable
        style.

        Retrieves the text size and font family from the configuration and applies them
        as inline styles to the today container. Also includes a JavaScript snippet that
        updates the date periodically.

        Returns:
            str: HTML content representing the today with real-time updates.
        """
        # Retrieve the today configuration
        today_config = MODULE_LAYOUT.get(self.name, {})
        date_format = today_config.get('date_format', '%Y-%m-%d')
        refresh_interval = today_config.get('refresh_interval', self.DEFAULT_REFRESH_INTERVAL)
        options = today_config.get('options', {})
        style = ' '.join(f'{key}: {value};' for key, value in options.items())
        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            style=style,
            date_format=date_format,
            refresh_interval=refresh_interval
        )


def get_module():
    """Factory function to create and return an instance of TodayModule.

    Returns:
        TodayModule: An instance of TodayModule.
    """
    return TodayModule()

