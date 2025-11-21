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
    # 'hyu_meal': {
    #     'position': 'top-right',
    #     'width': '1300px',
    #     'height': '400px',
    #     'refresh_interval': 3600000,
    #     'api_endpoint': '/api/meal-data',
    #     'options': {
    #         'font-size': '18px',
    #         'font-family': 'Arial, sans-serif',
    #         'text-align': 'center',
    #         'min-width': '60px',
    #     },
    # },
    # 'kbo': {
    #     'position': 'top-right',
    #     'width': '1300px',
    #     'height': '500px',
    #     'refresh_interval': 3600000,
    #     'api_endpoint': '/api/kbo-data',
    #     'options': {
    #         'font-size': '18px',
    #         'font-family': 'Arial, sans-serif',
    #         'text-align': 'center',
    #         'min-width': '60px',
    #     },
    # },
    'anti_burnin': {
        'max_step': 30,
        'refresh_interval': 300000,
    },
    'cloudwatch': {
        'position': 'top-right',
        'width': '1300px',
        'height': '900px',
        'api_endpoint': '/api/cloudwatch-data',
        'refresh_interval': 900000,
        'time_range_hours': 8,
        'period': 900,
        'title': 'AWS CloudWatch',
        'region': 'us-west-2',
        'dashboard_name': 'Production',

        # 병렬 처리 설정
        'parallel_mode': 'threading',  # 'threading' 또는 'async'
        'max_workers': 24,  # threading 모드에서 사용할 스레드 수 (기본값: 위젯 개수)

        # 옵션 1: AWS에서 대시보드 가져오기 (dashboard_name 사용)

        # 옵션 2: 대시보드 JSON을 직접 정의 (dashboard_body 사용)
        # 'dashboard_body': {
        #     'widgets': [
        #         {
        #             'type': 'metric',
        #             'x': 0,
        #             'y': 0,
        #             'width': 12,
        #             'height': 6,
        #             'properties': {
        #                 'metrics': [
        #                     # 예시: RDS CPU 사용률
        #                     # ['AWS/RDS', 'CPUUtilization', 'DBInstanceIdentifier', 'my-db', {'stat': 'Average'}],
        #                     # 예시: EC2 CPU 사용률
        #                     # ['AWS/EC2', 'CPUUtilization', 'InstanceId', 'i-1234567890abcdef0', {'stat': 'Average'}],
        #                 ],
        #                 'period': 900,  # 15분 간격 (설정하지 않으면 default_period 값 사용)
        #                 'stat': 'Average',
        #                 'region': 'us-west-2',
        #                 'title': 'Sample Metrics'
        #             }
        #         }
        #     ]
        # },

        'options': {
            'font-family': 'Arial, sans-serif',
            'text-align': 'center',
        },
    },
    # Additional module configurations can be added here.
}
