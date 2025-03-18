# modules/today.py

import re
from datetime import datetime

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
        style = " ".join(f"{key}: {value};" for key, value in options.items())

        html = (
            f"<div class='hyu-meal-module' class='hyu-meal' style='{style}'>"
            "  <h3>식단표</h3>"
            "  <table>"
            "    <tr>"
            "      <th>요일</th>"
            "      <th>월요일</th>"
            "      <th>화요일</th>"
            "      <th>수요일</th>"
            "      <th>목요일</th>"
            "      <th>금요일</th>"
            "    </tr>"
            "    <tr id='meal_bi_row'>"
            "      <td>창업보육지원센터</td>"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "    </tr>"
            "    <tr id='meal_sc_row_1'>"
            "      <td rowspan='2'>교직원식당</td>"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "    </tr>"
            "    <tr id='meal_sc_row_2'>"
            "      <!-- <td>2</td> -->"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "      <td></td>"
            "    </tr>"
            "  </table>"
            "</div>"
            "<script>"
            "  function updateMealData() {"
            "    fetch('/api/meal-data')"
            "      .then(response => response.json())"
            "      .then(data => {"
            "        const mealBiRow = document.getElementById('meal_bi_row');"
            "        const mealScRow1 = document.getElementById('meal_sc_row_1');"
            "        const mealScRow2 = document.getElementById('meal_sc_row_2');"
            "        mealBiRow.innerHTML = '<td>창업보육지원센터</td>';"
            "        mealScRow1.innerHTML = '<td rowspan=`2`>교직원식당</td>';"
            "        mealScRow2.innerHTML = '<!-- <td>2</td> -->';"
            "        data.meal_bi_info.forEach(meal => {"
            "          mealBiRow.innerHTML += `<td>${meal[0] || ''}</td>`;"
            "        });"
            "        data.meal_sc_info.forEach(meal => {"
            "          mealScRow1.innerHTML += `<td>${meal[0] || ''}</td>`;"
            "          mealScRow2.innerHTML += `<td>${meal[1] || ''}</td>`;"
            "        });"
            "      })"
            "      .catch(error => console.error('Error fetching meal data:', error));"
            "  }"
            "  updateMealData();"
            f"  setInterval(updateMealData, {refresh_interval});"
            "</script>"
        )
        return html

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
            meal_section = soup.select_one('#_foodView_WAR_foodportlet_tab_2 > div.box.tables-board-wrap > table > tbody > tr:nth-child(1)')
            
            if meal_section:
                meal_data = []
                cols = meal_section.find_all('td')
                for col_section in cols[1:-1]:
                    col_group = col_section.find_all('li')
                    meal_list = [re.sub(r'^\[[^]]+\]\s*', '', col.get_text(strip=True)) for col in col_group]
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
            meal_section = soup.select_one('#_foodView_WAR_foodportlet_tab_2 > div.box.tables-board-wrap > table > tbody > tr:nth-child(3)')
            
            if meal_section:
                meal_data = []
                cols = meal_section.find_all('td')
                for col_section in cols[1:-1]:
                    col_group = col_section.find_all('li')
                    meal_list = [re.sub(r'^\[[^]]+\]\s*', '', col.get_text(strip=True)) for col in col_group]
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
