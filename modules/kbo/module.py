# modules/today.py

import os
from datetime import datetime

import requests
from pytz import timezone

from module import APIModule
from config import MODULE_LAYOUT


class KBOModule(APIModule):
    """Module that displays KBO with dynamic updates."""

    KBO_BASE_URL = (
        'https://sports.daum.net/prx/hermes/api/game/schedule.json?leagueCode=kbo&toDate='
    )
    KBO_RANK_URL = 'https://sports.daum.net/prx/hermes/api/team/rank.json?leagueCode=kbo'

    @property
    def name(self):
        """Get the unique name of the module.

        Returns:
            str: The module name 'kbo'.
        """
        return 'kbo'

    def render(self):
        """Render the module's UI as an HTML string with dynamic meal updates.

        Returns:
            str: HTML content representing KOB score board.
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
            KBO_info=self.api()
        )

    def api(self):
        """Return API data for the module.

        Modules that expose backend API endpoints must implement this method
        to return a dictionary containing the API data.

        Returns:
            dict: API data for the module.
        """
        return {
            'score': self.get_kbo_info(),
            'rank': self.get_kbo_rank(),
        }

    def get_kbo_info(self):
        now = datetime.now(timezone('Asia/Seoul'))
        noon = now.replace(hour=12, minute=0, second=0, microsecond=0)

        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(f'{self.KBO_BASE_URL}{now.strftime("%Y%m%d")}', headers=headers)
            data = response.json()['schedule']
            keys = sorted(
                (k for k in data if k.isdigit()), 
                reverse=True
            )
            if (now >= noon) or (now.strftime('%Y%m%d') >= keys[0]):
                games = data[keys[0]]
            else:
                games = data[keys[1]]
            result = []
            for game in games:
                game_data = {
                    'game_status': game.get('gameStatus'),
                    'game_inning': game.get('periodType'),
                    'field_name': game.get('fieldName'),
                    'start_date': game.get('startDate'),
                    'start_time': game.get('startTime'),
                    'away_point': game.get('awayResult'),
                    'away_sp': game.get('awayStartPitcher'),
                    'away_team': game.get('awayTeamName'),
                    'away_team_img': game.get('awayTeamImageUrl'),
                    'away_wlt': game.get('awayWlt'),
                    'home_point': game.get('homeResult'),
                    'home_sp': game.get('homeStartPitcher'),
                    'home_team': game.get('homeTeamName'),
                    'home_team_img': game.get('homeTeamImageUrl'),
                    'home_wlt': game.get('homeWlt'),
                    'win_pitcher': game.get('winPitcher', ''),
                    'lose_pitcher': game.get('losePitcher', ''),
                }
                result.append(game_data)
            return result
        except Exception as e:
            print('KBO Info Error:', e)
            return []

    def get_kbo_rank(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(self.KBO_RANK_URL, headers=headers)
            data = response.json()['list']
            result = []
            for game in data:
                rank = game.get('rank', {})
                rank_data = {
                    'rank': rank.get('rank'),
                    'team_img': game.get('imageUrl'),
                    'team_name': game.get('shortName'),
                    'game': rank.get('game'),
                    'win': rank.get('win'),
                    'draw': rank.get('draw'),
                    'loss': rank.get('loss'),
                    'wpct': rank.get('wpct'),
                    'gb': rank.get('gb'),
                    'streak': rank.get('streak'),
                }
                result.append(rank_data)
            return result
        except Exception as e:
            print('KBO Info Error:', e)
            return []

def get_module():
    """Factory function to create and return an instance of KBOModule.

    Returns:
        KBOModule: An instance of KBOModule.
    """
    return KBOModule()
