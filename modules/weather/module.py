# modules/today.py

import os
import re

import toml
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from module import APIModule
from config import MODULE_LAYOUT


class WeatherModule(APIModule):
    """Module that displays Weather with dynamic updates."""

    WEATHER_URL = 'https://weather.naver.com'
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )
    selector: dict = {}
    img_rex = re.compile(r'^ico(?:_animation)?_wt\d+$')
    temp_rex = re.compile(r'-?(?:\d+\.\d+|\d+)')

    @property
    def name(self):
        """Get the unique name of the module.

        Returns:
            str: The module name 'hyu_meal'.
        """
        return 'hyu_meal'

    def render(self):
        """Render the module's UI as an HTML string with dynamic meal updates.

        Returns:
            str: HTML content representing hanyang university's meal.
        """
        # Retrieve today's module configuration
        meal_config = MODULE_LAYOUT.get(self.name, {})
        refresh_interval = meal_config.get('refresh_interval', 1500000)
        options = meal_config.get('options', {})
        style = ' '.join(f'{key}: {value};' for key, value in options.items())
        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            style=style,
            refresh_interval=refresh_interval,
            weather_info=self.api()
        )

    def api(self):
        """Return API data for the module.

        Modules that expose backend API endpoints must implement this method
        to return a dictionary containing the API data.

        Returns:
            dict: API data for the module.
        """
        self.driver.get(self.WEATHER_URL)
        self.load_tag_selector(f'{os.path.dirname(os.path.abspath(__file__))}/tag.toml')
        return {
            'location': self.get_location(),
            'alarm': self.get_alarm(),
            'weather': self.get_weather(),
            'weekly': self.get_weekly(),
        }

    def load_tag_selector(self, file_path):
        with open(file_path, 'r') as file:
            self.selector = toml.load(file)

    def get_location(self):
        selector = self.selector['location']['location']
        soup = self.get_soup(selector)
        return soup.select_one(selector).get_text()
    
    def get_alarm(self):
        selector = self.selector['alarm']['alarm']
        soup = self.get_soup(selector)
        alarm_list = soup.select(selector)
        return [alarm.get_text(strip=True) for alarm in alarm_list if alarm.get_text(strip=True)]
    
    def get_weather(self):
        selector = self.selector['weather']
        soup = self.get_soup(selector['now_img'])
        # now_img
        now_img_tag = soup.select_one(selector['now_img'])
        now_img_class_list = now_img_tag.get('class', [])
        now_img = self.get_img_url(now_img_class_list)
        # now_weather
        now_weather_tag = soup.select_one(selector['now_weather'])
        now_weather = now_weather_tag.get_text()
        # now_temperature
        now_temp_tag = soup.select_one(selector['now_temperature'])
        now_temperature = self.parse_decimal(now_temp_tag.get_text(strip=True, separator=' '))
        # quick_humidity
        quick_humidity_tag = soup.select_one(selector['quick_humidity'])
        quick_humidity = quick_humidity_tag.get_text()
        # quick_apparent_temperature
        quick_app_temperature_tag = soup.select_one(selector['quick_apparent_temperature'])
        quick_apparent_temperature = self.parse_decimal(quick_app_temperature_tag.get_text())
        # quick_wind_direction
        quick_wind_direction_tag = soup.select_one(selector['quick_wind_direction'])
        quick_wind_direction = quick_wind_direction_tag.get_text()
        # quick_wind_speed
        quick_wind_speed_tag = soup.select_one(selector['quick_wind_speed'])
        quick_wind_speed = quick_wind_speed_tag.get_text()
        # quick_pm10
        quick_pm10_tag = soup.select_one(selector['quick_pm10'])
        quick_pm10 = quick_pm10_tag.get_text()
        # quick_pm25
        quick_pm25_tag = soup.select_one(selector['quick_pm25'])
        quick_pm25 = quick_pm25_tag.get_text()
        # quick_sun
        quick_sun_tag = soup.select_one(selector['quick_sun'])
        quick_sun = quick_sun_tag.get_text()
        # quick_suntime
        quick_suntime_tag = soup.select_one(selector['quick_suntime'])
        quick_suntime = quick_suntime_tag.get_text()
        return {
            'now_img': now_img,
            'now_weather': now_weather,
            'now_temperature': now_temperature,
            'quick_humidity': quick_humidity,
            'quick_apparent_temperature': quick_apparent_temperature,
            'quick_wind_direction': quick_wind_direction,
            'quick_wind_speed': quick_wind_speed,
            'quick_pm10': quick_pm10,
            'quick_pm25': quick_pm25,
            'quick_sun': quick_sun,
            'quick_suntime': quick_suntime,
        }

    def get_weekly(self):
        selector = self.selector['weekly']
        soup = self.get_soup(selector['weekly_list'])
        weekly: list[dict] = []
        for week in soup.select(selector['weekly_list']):
            data = {}
            data['weekly_day'] = week.find('strong', class_='day').get_text()
            data['weekly_date'] = week.find('span', class_='date').get_text()
            for p, ico in enumerate(week.find_all('i', class_='ico')):
                data[f'weekly_{'ap' if p else 'am'}_img'] = self.get_img_url(ico.get('class', []))
            for p, sapn in enumerate(week.find_all('span', class_='rainfall')):
                data[f'weekly_{'ap' if p else 'am'}_rainfall'] = self.parse_decimal(sapn.get_text())
            data[f'weekly_low_temperature'] = self.parse_decimal(
                week.find('span', class_='lowest').get_text()
            )
            data[f'weekly_high_temperature'] = self.parse_decimal(
                week.find('span', class_='highest').get_text()
            )
            weekly.append(data)
        return weekly

    def get_soup(self, css_selector):
        WebDriverWait(self.driver, timeout=30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        return BeautifulSoup(self.driver.page_source, 'html.parser')

    def get_img_url(self, class_list):
        img_index = [
            self.img_rex.match(hcls)[0] for hcls in class_list if self.img_rex.match(hcls)
        ][0]
        return f'https://ssl.pstatic.net/static/weather/image/icon_weather/{img_index}.svg'

    def parse_decimal(self, temp_text):
        temperature = re.search(self.temp_rex, temp_text)
        return temperature.group() if temperature else ''


def get_module():
    """Factory function to create and return an instance of WeatherModule.

    Returns:
        WeatherModule: An instance of WeatherModule.
    """
    return WeatherModule()
