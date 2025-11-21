# modules/anti_burnin.py

import os

from module import BaseModule
from config import MODULE_LAYOUT


class AntiBurnInModule(BaseModule):
    """OLED 화면의 번인(burn-in) 방지를 위한 모듈.

    주기적으로 화면 전체를 랜덤하게 이동시켜 같은 위치에
    픽셀이 고정되는 것을 방지합니다.

    설정:
        - max_step: 최대 이동 거리(픽셀)
        - refresh_interval: 이동 주기(밀리초)
    """

    # 상수 정의
    DEFAULT_MAX_STEP = 30  # 최대 이동 거리 (픽셀)
    DEFAULT_REFRESH_INTERVAL = 300000  # 5분 (밀리초)

    @property
    def name(self):
        """모듈 이름 반환."""
        return 'anti_burnin'

    def render(self):
        """모듈 UI를 HTML로 렌더링.

        Returns:
            str: 번인 방지 스크립트를 포함한 HTML
        """
        config = MODULE_LAYOUT.get(self.name, {})
        max_step = config.get('max_step', self.DEFAULT_MAX_STEP)
        refresh_interval = config.get('refresh_interval', self.DEFAULT_REFRESH_INTERVAL)

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
