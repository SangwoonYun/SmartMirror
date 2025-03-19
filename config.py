# config.py

"""
Configuration settings for the Smart Mirror project.

This file contains layout and positioning settings for modules.
"""

MODULE_LAYOUT = {
    'today': {
        'position': 'top-left',
        'width': '1000px',
        'height': '200px',
        'date_format': '%Y년 %m월 %d일',
        'refresh_interval': 100,
        'options': {
            'font-size': '120px',
            'font-family': 'Arial, sans-serif',
            'font-weight': 'bold',
        },
    },
    'clock': {
        'position': 'top-left',
        'width': '1000px',
        'height': '200px',
        'time_format': '%H:%M:%S',
        'refresh_interval': 100,
        'options': {
            'font-size': '230px',
            'font-family': 'Arial, sans-serif',
            'font-weight': 'bold',
        },
    },
    'hyu_meal': {
        'position': 'top-right',
        'width': '1660px',
        'height': '500px',
        'refresh_interval': 3600000,
        'api_endpoint': '/api/meal-data',
        'options': {
            'font-size': '20px',
            'font-family': 'Arial, sans-serif',
            'text-align': 'center',
            'min-width': '60px',
        },
    },
    # Additional module configurations can be added here.
}
