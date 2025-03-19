# modules/today.py

import os
import re

import requests
from bs4 import BeautifulSoup

from module import APIModule
from config import MODULE_LAYOUT


class HYUMealModule(APIModule):
    """Module that displays Hanyang University's meal with dynamic updates."""

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
        refresh_interval = meal_config.get('refresh_interval', 3600000)
        options = meal_config.get('options', {})
        style = ' '.join(f'{key}: {value};' for key, value in options.items())
        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            style=style,
            refresh_interval=refresh_interval
        )

    def api(self):
        """Return API data for the module.

        Modules that expose backend API endpoints must implement this method
        to return a dictionary containing the API data.

        Returns:
            dict: API data for the module.
        """
        meal_bi_info = self.get_meal_bi_info()
        meal_sc_info = self.get_meal_sc_info()
        
        return {
            'meal_bi_info': meal_bi_info,
            'meal_sc_info': meal_sc_info,
        }

    @staticmethod
    def get_meal_bi_info():
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get('https://www.hanyang.ac.kr/web/www/re15', headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            meal_section = soup.select_one(
                '#_foodView_WAR_foodportlet_tab_2 > div.box.tables-board-wrap > '
                'table > tbody > tr:nth-child(1)'
            )
            
            if meal_section:
                meal_data = []
                cols = meal_section.find_all('td')
                for col_section in cols[1:-1]:
                    col_group = col_section.find_all('li')
                    meal_list = [
                        re.sub(r'^\[[^]]+\]\s*', '', col.get_text(strip=True))
                        for col in col_group
                    ]
                    meal_data.append(meal_list)
                return meal_data
            else:
                return []
        except Exception as e:
            print('Meal BI Info Error:', e)
            return []

    @staticmethod
    def get_meal_sc_info():
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get('https://www.hanyang.ac.kr/web/www/re11', headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            meal_section = soup.select_one(
                '#_foodView_WAR_foodportlet_tab_2 > div.box.tables-board-wrap > '
                'table > tbody > tr:nth-child(3)'
            )
            
            if meal_section:
                meal_data = []
                cols = meal_section.find_all('td')
                for col_section in cols[1:-1]:
                    col_group = col_section.find_all('li')
                    meal_list = [
                        re.sub(r'^\[[^]]+\]\s*', '', col.get_text(strip=True))
                        for col in col_group
                    ]
                    meal_data.append(meal_list)
                return meal_data
            else:
                return []
        except Exception as e:
            print('Meal SC Info Error:', e)
            return []


def get_module():
    """Factory function to create and return an instance of HYUMealModule.

    Returns:
        HYUMealModule: An instance of HYUMealModule.
    """
    return HYUMealModule()
