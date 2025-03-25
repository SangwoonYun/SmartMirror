# config.py

"""
Configuration settings for the Smart Mirror project.

This file contains layout and positioning settings for modules.
"""

MODULE_LAYOUT = {
    'today': {
        'position': 'top-left',
        'width': '1000px',
        'date_format': '%Y년 %m월 %d일 %K요일',
        'refresh_interval': 100,
        'options': {
            'font-size': '82px',
            'font-family': 'Arial, sans-serif',
            'font-weight': 'bold',
        },
    },
    'clock': {
        'position': 'top-left',
        'width': '1000px',
        'time_format': '%P %I:%M:%S',
        'refresh_interval': 100,
        'options': {
            'font-size': '150px',
            'font-family': 'Arial, sans-serif',
            'font-weight': 'bold',
        },
    },
    'weather': {
        'position': 'top-left',
        'width': '1000px',
        'refresh_interval': 3600000,
        'api_endpoint': '/api/weather-data',
        'options': {
            'font-size': '20px',
            'font-family': 'Arial, sans-serif',
            'text-align': 'center',
        },
    },
    'hyu_meal': {
        'position': 'top-right',
        'width': '1300px',
        'height': '400px',
        'refresh_interval': 3600000,
        'api_endpoint': '/api/meal-data',
        'options': {
            'font-size': '18px',
            'font-family': 'Arial, sans-serif',
            'text-align': 'center',
            'min-width': '60px',
        },
    },
    'kbo': {
        'position': 'top-right',
        'width': '1300px',
        'height': '500px',
        'refresh_interval': 600000,
        'api_endpoint': '/api/kbo-data',
        'options': {
            'font-size': '18px',
            'font-family': 'Arial, sans-serif',
            'text-align': 'center',
            'min-width': '60px',
        },
    },
    'anti_burnin': {
        'max_step': 30,
        'refresh_interval': 300000,
    },
    # Additional module configurations can be added here.
}
