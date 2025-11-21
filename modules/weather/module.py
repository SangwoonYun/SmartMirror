# modules/weather/module.py

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

import toml
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from module import APIModule
from config import MODULE_LAYOUT


class WeatherModule(APIModule):
    """네이버 날씨 정보를 표시하는 모듈.

    Selenium을 사용하여 네이버 날씨 페이지를 크롤링하고,
    현재 날씨, 주간 예보, 미세먼지 정보를 수집합니다.

    성능 최적화:
        - 필요할 때만 WebDriver 생성
        - 병렬 처리로 날씨/미세먼지 동시 조회
        - Context Manager로 리소스 자동 정리
    """

    # 상수 정의
    WEATHER_URL = 'https://weather.naver.com?cpName=ACCUWEATHER'
    AIR_URL = 'https://weather.naver.com/air'
    WAIT_TIMEOUT = 5
    DEFAULT_REFRESH_INTERVAL = 1500000

    # 정규 표현식
    IMG_PATTERN = re.compile(r'^ico(?:_animation)?_wt\d+$')
    TEMP_PATTERN = re.compile(r'-?(?:\d+\.\d+|\d+)')

    def __init__(self):
        super().__init__()
        self._selector = None
        self._chrome_options = None

    @property
    def name(self):
        """모듈 이름 반환."""
        return 'weather'

    @property
    def chrome_options(self):
        """Chrome 옵션 lazy 생성."""
        if self._chrome_options is None:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-logging')
            options.add_argument('--log-level=3')
            self._chrome_options = options
        return self._chrome_options

    @property
    def selector(self):
        """Selector lazy 로딩."""
        if self._selector is None:
            tag_path = f'{os.path.dirname(os.path.abspath(__file__))}/tag.toml'
            with open(tag_path, 'r') as file:
                self._selector = toml.load(file)
        return self._selector

    def render(self):
        """모듈 UI를 HTML로 렌더링."""
        config = MODULE_LAYOUT.get(self.name, {})
        refresh_interval = config.get('refresh_interval', self.DEFAULT_REFRESH_INTERVAL)
        options = config.get('options', {})
        style = ' '.join(f'{key}: {value};' for key, value in options.items())

        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            style=style,
            refresh_interval=refresh_interval
        )

    def api(self):
        """날씨 API 데이터 반환.

        날씨 정보와 미세먼지 정보를 병렬로 조회하여 성능을 최적화합니다.

        Returns:
            dict: 날씨 데이터
                {
                    'location': str,
                    'alarm': list,
                    'weekly': list,
                    'weather': dict (미세먼지 정보 포함)
                }
        """
        # 병렬 처리로 날씨와 미세먼지 정보 동시 조회
        with ThreadPoolExecutor(max_workers=2) as executor:
            weather_future = executor.submit(self._fetch_weather_data)
            air_future = executor.submit(self._fetch_air_data)

            weather_result = weather_future.result()
            air_result = air_future.result()

        # 미세먼지 정보를 날씨 데이터에 병합
        weather_result['weather'].update(**air_result)
        return weather_result

    def _fetch_weather_data(self):
        """날씨 데이터 조회 (위치, 알림, 주간예보, 현재날씨)."""
        with self._create_driver_context() as driver:
            driver.get(self.WEATHER_URL)
            soup = self._get_soup(self.selector['location']['location'], driver)

            # 하나의 soup으로 모든 데이터 추출
            return {
                'location': self._extract_location(soup),
                'alarm': self._extract_alarm(soup),
                'weekly': self._extract_weekly(soup),
                'weather': self._extract_weather(soup),
            }

    def _fetch_air_data(self):
        """미세먼지 데이터 조회."""
        with self._create_driver_context() as driver:
            driver.get(self.AIR_URL)
            soup = self._get_soup(
                self.selector['weather']['quick_air_check'],
                driver
            )
            return self._extract_air(soup)

    @contextmanager
    def _create_driver_context(self):
        """WebDriver context manager (자동 정리)."""
        driver = None
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=self.chrome_options
            )
            yield driver
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    print(f"Error closing driver: {e}")

    def _get_soup(self, css_selector, driver, timeout=None):
        """페이지 로드 대기 후 BeautifulSoup 반환."""
        timeout = timeout or self.WAIT_TIMEOUT
        try:
            WebDriverWait(driver, timeout=timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
        except WebDriverException:
            pass
        return BeautifulSoup(driver.page_source, 'html.parser')

    def _extract_location(self, soup):
        """위치 정보 추출."""
        selector = self.selector['location']['location']
        element = soup.select_one(selector)
        return element.get_text() if element else ''

    def _extract_alarm(self, soup):
        """알림 정보 추출."""
        selector = self.selector['alarm']['alarm']
        alarm_list = soup.select(selector)
        return [
            a.get_text(strip=True)
            for alarm in alarm_list
            for a in alarm.select('a.common_item_text')
            if a.get_text(strip=True)
        ]

    def _extract_weather(self, soup):
        """현재 날씨 정보 추출."""
        selector = self.selector['weather']

        # 날씨 아이콘
        now_img_tag = soup.select_one(selector['now_img'])
        now_img = self._get_img_url(now_img_tag.get('class', []))

        # 날씨 상태
        now_weather_tag = soup.select_one(selector['now_weather'])
        now_weather = now_weather_tag.get_text() if now_weather_tag else ''

        # 현재 온도
        now_temp_tag = soup.select_one(selector['now_temperature'])
        now_temperature = self._parse_decimal(
            now_temp_tag.get_text(strip=True, separator=' ')
        ) if now_temp_tag else ''

        # 강수량
        quick_rain_tag = soup.select_one(selector['quick_rain'])
        if quick_rain_tag:
            now_weather += f' {quick_rain_tag.get_text()}mm'

        # 습도
        quick_humidity_tag = soup.select_one(selector['quick_humidity'])
        quick_humidity = quick_humidity_tag.get_text() if quick_humidity_tag else ''

        # 체감온도
        quick_app_temp_tag = soup.select_one(selector['quick_apparent_temperature'])
        quick_apparent_temperature = self._parse_decimal(
            quick_app_temp_tag.get_text()
        ) if quick_app_temp_tag else ''

        # 풍향
        quick_wind_dir_tag = soup.select_one(selector['quick_wind_direction'])
        quick_wind_direction = quick_wind_dir_tag.get_text() if quick_wind_dir_tag else ''

        # 풍속
        quick_wind_speed_tag = soup.select_one(selector['quick_wind_speed'])
        quick_wind_speed = quick_wind_speed_tag.get_text() if quick_wind_speed_tag else ''

        # UV 지수
        quick_uv = self._extract_uv(soup, selector)

        return {
            'now_img': now_img,
            'now_weather': now_weather,
            'now_temperature': now_temperature,
            'quick_humidity': quick_humidity,
            'quick_apparent_temperature': quick_apparent_temperature,
            'quick_wind_direction': quick_wind_direction,
            'quick_wind_speed': quick_wind_speed,
            'quick_uv': quick_uv,
            'quick_uv_color': self._get_uv_state(quick_uv),
        }

    def _extract_uv(self, soup, selector):
        """UV 지수 추출."""
        quick_base_tag = soup.select_one(selector['quick_tags'])
        if not quick_base_tag:
            return ''

        for uv_child in quick_base_tag.find_all('div', recursive=False):
            span = uv_child.find('span')
            if span and span.get_text(strip=True) == 'UV':
                quick_uv_tag = uv_child.select_one(selector['quick_uv'])
                return quick_uv_tag.get_text() if quick_uv_tag else ''
        return ''

    def _extract_weekly(self, soup):
        """주간 예보 정보 추출."""
        selector = self.selector['weekly']
        weekly = []

        for week in soup.select(selector['weekly_list']):
            day_tag = week.find('strong', class_='day')
            date_tag = week.find('span', class_='date')

            data = {
                'weekly_day': day_tag.get_text() if day_tag else '',
                'weekly_date': date_tag.get_text() if date_tag else '',
            }

            # AM/PM 아이콘
            for idx, ico in enumerate(week.find_all('i', class_='ico')):
                key = f'weekly_{"ap" if idx else "am"}_img'
                data[key] = self._get_img_url(ico.get('class', []))

            # AM/PM 강수량
            for idx, span in enumerate(week.find_all('span', class_='rainfall')):
                key = f'weekly_{"ap" if idx else "am"}_rainfall'
                data[key] = self._parse_decimal(span.get_text())

            # 최저/최고 온도
            lowest_tag = week.find('span', class_='lowest')
            highest_tag = week.find('span', class_='highest')

            data['weekly_low_temperature'] = self._parse_decimal(
                lowest_tag.get_text()
            ) if lowest_tag else ''
            data['weekly_high_temperature'] = self._parse_decimal(
                highest_tag.get_text()
            ) if highest_tag else ''

            weekly.append(data)

        return weekly

    def _extract_air(self, soup):
        """미세먼지 정보 추출."""
        air_soup = soup.select_one(self.selector['weather']['quick_air'])
        if not air_soup:
            return {
                'quick_pm10': '',
                'quick_pm10_color': [],
                'quick_pm25': '',
                'quick_pm25_color': [],
            }

        tags = air_soup.find_all('div', class_='card_data_item')
        if len(tags) < 2:
            return {
                'quick_pm10': '',
                'quick_pm10_color': [],
                'quick_pm25': '',
                'quick_pm25_color': [],
            }

        # PM 10
        pm10_value = tags[0].find('span', class_='dount_value_text')
        pm10 = pm10_value.get_text() if pm10_value else ''
        pm10_color = tags[0].get('class', [])

        # PM 2.5
        pm25_value = tags[1].find('span', class_='dount_value_text')
        pm25 = pm25_value.get_text() if pm25_value else ''
        pm25_color = tags[1].get('class', [])

        return {
            'quick_pm10': pm10,
            'quick_pm10_color': pm10_color,
            'quick_pm25': pm25,
            'quick_pm25_color': pm25_color,
        }

    def _get_img_url(self, class_list):
        """클래스 리스트에서 날씨 이미지 URL 생성."""
        matches = [cls for cls in class_list if self.IMG_PATTERN.match(cls)]
        if not matches:
            return ''

        img_index = matches[0]
        return f'https://ssl.pstatic.net/static/weather/image/icon_weather/{img_index}.svg'

    def _parse_decimal(self, text):
        """텍스트에서 숫자 추출."""
        if not text:
            return ''
        match = re.search(self.TEMP_PATTERN, text)
        return match.group() if match else ''

    @staticmethod
    def _get_uv_state(quick_uv):
        """UV 지수에 따른 상태 반환."""
        if not quick_uv:
            return 'level4_1'

        try:
            uv = int(quick_uv)
        except (ValueError, TypeError):
            return 'level4_1'

        if uv >= 11:
            return 'level4_5'
        elif uv >= 8:
            return 'level4_4'
        elif uv >= 6:
            return 'level4_3'
        elif uv >= 3:
            return 'level4_2'
        else:
            return 'level4_1'


def get_module():
    """WeatherModule 인스턴스를 생성하고 반환하는 팩토리 함수.

    Returns:
        WeatherModule: WeatherModule의 인스턴스
    """
    return WeatherModule()
