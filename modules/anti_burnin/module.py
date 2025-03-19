# modules/anti_burnin.py

import os

from module import BaseModule
from config import MODULE_LAYOUT


class AntiBurnInModule(BaseModule):
    """
    """

    @property
    def name(self):
        """Get the unique name of the module.

        Returns:
            str: The module name 'anti_burnin'.
        """
        return 'anti_burnin'

    def render(self):
        """
        Returns:
            str: HTML content representing the clock with real-time updates.
        """
        # Retrieve the clock configuration
        anti_burnin_config = MODULE_LAYOUT.get(self.name, {})
        max_step = anti_burnin_config.get('max_step', 30)
        refresh_interval = anti_burnin_config.get('refresh_interval', 300000)
        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            max_step=max_step,
            refresh_interval=refresh_interval
        )


def get_module():
    """Factory function to create and return an instance of AntiBurnInModule.

    Returns:
        AntiBurnInModule: An instance of AntiBurnInModule.
    """
    return AntiBurnInModule()
