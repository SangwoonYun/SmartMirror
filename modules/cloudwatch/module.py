# modules/cloudwatch/module.py

import os
import json
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config import MODULE_LAYOUT
from module import APIModule


class CloudWatchModule(APIModule):
    """AWS CloudWatch 대시보드를 표시하는 모듈.

    이 모듈은 AWS CloudWatch API를 통해 대시보드 정의를 가져오고,
    각 위젯에 정의된 메트릭 데이터를 조회하여 프론트엔드에서 차트로 렌더링합니다.
    """

    def __init__(self):
        super().__init__()
        # CloudWatch 클라이언트 초기화
        cloudwatch_config = MODULE_LAYOUT.get('cloudwatch', {})
        region = cloudwatch_config.get('region', 'us-east-1')

        try:
            self.cloudwatch_client = boto3.client('cloudwatch', region_name=region)
        except (NoCredentialsError, Exception) as e:
            print(f'CloudWatch client initialization error: {e}')
            self.cloudwatch_client = None

    @property
    def name(self):
        """모듈의 고유한 이름을 반환합니다.

        Returns:
            str: 모듈 이름 'cloudwatch'.
        """
        return 'cloudwatch'

    def render(self):
        """모듈의 UI를 HTML 문자열로 렌더링합니다.

        Returns:
            str: CloudWatch 대시보드를 표시하는 HTML 콘텐츠.
        """
        # CloudWatch 설정 가져오기
        cloudwatch_config = MODULE_LAYOUT.get(self.name, {})

        # 새로고침 간격 (밀리초, 기본값 15분)
        refresh_interval = cloudwatch_config.get('refresh_interval', 900000)

        # 스타일 옵션
        options = cloudwatch_config.get('options', {})
        style = ' '.join(f'{key}: {value};' for key, value in options.items())

        # 대시보드 제목 (대시보드 이름 포함)
        dashboard_name = cloudwatch_config.get('dashboard_name', '')
        title = cloudwatch_config.get('title', 'AWS CloudWatch')
        if dashboard_name:
            title += f' - {dashboard_name}'

        # 템플릿 렌더링
        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            style=style,
            refresh_interval=refresh_interval,
            title=title
        )

    def api(self):
        """CloudWatch 대시보드 데이터를 반환하는 API 엔드포인트.

        대시보드 JSON 정의를 파싱하고, 각 위젯의 메트릭 데이터를 조회합니다.

        Returns:
            dict: 대시보드 위젯 정보와 메트릭 데이터.
        """
        if not self.cloudwatch_client:
            return {
                'error': 'CloudWatch client not initialized. Check AWS credentials.',
                'widgets': []
            }

        cloudwatch_config = MODULE_LAYOUT.get(self.name, {})
        dashboard_name = cloudwatch_config.get('dashboard_name', '')
        dashboard_body = cloudwatch_config.get('dashboard_body', None)

        # 대시보드 정의 가져오기
        if dashboard_body:
            # config.py에 직접 정의된 경우
            dashboard_def = dashboard_body
        elif dashboard_name:
            # AWS에서 대시보드 가져오기
            dashboard_def = self.get_dashboard_definition(dashboard_name)
        else:
            return {
                'error': 'No dashboard_name or dashboard_body configured.',
                'widgets': []
            }

        if not dashboard_def or 'widgets' not in dashboard_def:
            return {
                'error': 'Invalid dashboard definition.',
                'widgets': []
            }

        # 각 위젯의 메트릭 데이터 조회 (병렬 처리)
        widgets = dashboard_def.get('widgets', [])
        widgets_with_data = []

        # ThreadPoolExecutor로 병렬 처리 (최대 10개 스레드)
        max_workers = min(10, len(widgets))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 위젯을 병렬로 처리
            future_to_widget = {
                executor.submit(self.process_widget, widget): widget
                for widget in widgets
            }

            # 완료된 순서대로 결과 수집
            for future in as_completed(future_to_widget):
                try:
                    widget_data = future.result()
                    if widget_data:
                        widgets_with_data.append(widget_data)
                except Exception as e:
                    print(f"Error processing widget: {e}")

        # 원본 순서대로 정렬 (y, x 좌표 기준)
        widgets_with_data.sort(key=lambda w: (w.get('y', 0), w.get('x', 0)))

        return {
            'widgets': widgets_with_data,
            'error': None
        }

    def get_dashboard_definition(self, dashboard_name):
        """AWS CloudWatch에서 대시보드 정의를 가져옵니다.

        Args:
            dashboard_name (str): 대시보드 이름.

        Returns:
            dict: 대시보드 JSON 정의.
        """
        try:
            response = self.cloudwatch_client.get_dashboard(
                DashboardName=dashboard_name
            )
            dashboard_body = response.get('DashboardBody', '{}')
            return json.loads(dashboard_body)
        except ClientError as e:
            print(f'Error fetching dashboard: {e}')
            return None

    def process_widget(self, widget):
        """위젯 정의를 처리하고 메트릭 데이터를 조회합니다.

        Args:
            widget (dict): 위젯 정의.

        Returns:
            dict: 위젯 정보와 메트릭 데이터.
        """
        widget_type = widget.get('type', 'metric')
        properties = widget.get('properties', {})

        # 위젯 기본 정보
        widget_info = {
            'type': widget_type,
            'x': widget.get('x', 0),
            'y': widget.get('y', 0),
            'width': widget.get('width', 6),
            'height': widget.get('height', 6),
            'title': properties.get('title', 'Untitled'),
            'region': properties.get('region', 'us-east-1'),
        }

        # metric 타입 위젯만 처리
        if widget_type == 'metric':
            metrics = properties.get('metrics', [])
            # config.py에서 기본 period 설정 가져오기 (기본값: 900초 = 15분)
            cloudwatch_config = MODULE_LAYOUT.get(self.name, {})
            period = cloudwatch_config.get('period', 900)
            stat = properties.get('stat', 'Average')

            # y축 설정 추출
            yAxis = properties.get('yAxis', {})
            if yAxis:
                widget_info['yAxis'] = yAxis

            # annotations 설정 추출 (가로선 임계값 등)
            annotations = properties.get('annotations', {})
            if annotations:
                widget_info['annotations'] = annotations

            # 메트릭 데이터 조회
            metric_data = self.get_metric_data(metrics, period, stat)
            widget_info['data'] = metric_data
        else:
            # 다른 타입의 위젯은 기본 정보만 반환
            widget_info['data'] = []

        return widget_info

    def get_metric_data(self, metrics, period, default_stat='Average'):
        """메트릭 데이터를 CloudWatch에서 조회합니다 (수학 표현식 지원).

        Args:
            metrics (list): 메트릭 정의 리스트.
            period (int): 데이터 포인트 간격 (초).
            default_stat (str): 기본 통계 유형.

        Returns:
            list: 메트릭 데이터 리스트.
        """
        cloudwatch_config = MODULE_LAYOUT.get(self.name, {})
        time_range = cloudwatch_config.get('time_range_hours', 8)  # 기본값: 8시간

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range)

        # GetMetricData API를 사용하여 일반 메트릭과 수학 표현식을 모두 조회
        metric_data_queries = []
        metric_labels = {}  # ID -> label, color 매핑 (내부용)
        metric_order = {}  # ID -> 순서 매핑 (JSON 순서 유지용)
        previous_dimensions = {}  # 점 표기법(.)을 위한 이전 차원 값 저장
        previous_namespace = None  # 점 표기법(.)을 위한 이전 namespace 저장
        previous_metric_name = None  # 점 표기법(.)을 위한 이전 metric name 저장

        for idx, metric_def in enumerate(metrics):
            if not isinstance(metric_def, list):
                continue

            # 수학 표현식인 경우 (첫 번째 요소가 dict)
            if len(metric_def) > 0 and isinstance(metric_def[0], dict):
                math_expr = metric_def[0]

                expression = math_expr.get('expression')
                label = math_expr.get('label', f'Expression {idx}')
                metric_id = math_expr.get('id', f'e{idx}')
                visible = math_expr.get('visible', True)
                color = math_expr.get('color')

                if expression:
                    # API 쿼리 (Color는 AWS API에서 지원하지 않음)
                    metric_data_queries.append({
                        'Id': metric_id,
                        'Expression': expression,
                        'Label': label,
                        'ReturnData': True  # 모든 표현식 데이터를 가져옴 (다른 표현식이 참조할 수 있음)
                    })
                    # 색상과 visible 정보는 별도로 저장
                    metric_labels[metric_id] = {'label': label, 'color': color, 'visible': visible}
                    metric_order[metric_id] = idx  # JSON 순서 저장
                continue

            # 일반 메트릭인 경우
            if len(metric_def) < 2:
                continue

            namespace = metric_def[0]
            metric_name = metric_def[1]

            # 점 표기법 처리: Namespace와 MetricName
            if namespace == '.' and previous_namespace:
                namespace = previous_namespace
            if metric_name == '.' and previous_metric_name:
                metric_name = previous_metric_name

            # 차원(Dimensions) 파싱
            dimensions = []
            i = 2
            while i < len(metric_def):
                if isinstance(metric_def[i], str) and i + 1 < len(metric_def):
                    if isinstance(metric_def[i + 1], str):
                        dim_name = metric_def[i]
                        dim_value = metric_def[i + 1]

                        # 점 표기법(.) 처리: 이전 메트릭의 같은 차원 값 사용
                        if dim_name == '.' and previous_dimensions:
                            # 이전 차원에서 같은 위치의 차원 이름 가져오기
                            dim_index = len(dimensions)
                            if dim_index < len(previous_dimensions):
                                dim_name = previous_dimensions[dim_index]['Name']

                        if dim_value == '.' and previous_dimensions:
                            # 이전 차원에서 같은 이름의 차원 값 가져오기
                            for prev_dim in previous_dimensions:
                                if prev_dim['Name'] == dim_name:
                                    dim_value = prev_dim['Value']
                                    break

                        # 점이 아닌 경우에만 추가
                        if dim_name != '.' and dim_value != '.':
                            dimensions.append({
                                'Name': dim_name,
                                'Value': dim_value
                            })

                        i += 2
                    elif isinstance(metric_def[i + 1], dict):
                        # 다음이 dict이면 차원 파싱 종료
                        break
                    else:
                        i += 1
                else:
                    i += 1

            # 현재 메트릭의 정보를 다음 메트릭을 위해 저장 (점 표기법 처리용)
            if dimensions:
                previous_dimensions = dimensions
            previous_namespace = namespace
            previous_metric_name = metric_name

            # 통계 유형, 라벨, visible, id, color 속성 파싱 (마지막 dict에서)
            stat = default_stat
            label = None
            visible = True  # 기본값은 true
            metric_id = f'm{idx}'
            color = None
            for item in metric_def:
                if isinstance(item, dict):
                    if 'stat' in item:
                        stat = item['stat']
                    if 'label' in item:
                        label = item['label']
                    if 'visible' in item:
                        visible = item['visible']
                    if 'id' in item:
                        metric_id = item['id']
                    if 'color' in item:
                        color = item['color']

            # MetricStat 쿼리 추가
            # 주의: visible이 false여도 수학 표현식에서 참조될 수 있으므로 모든 메트릭을 API 호출에 포함
            query = {
                'Id': metric_id,
                'MetricStat': {
                    'Metric': {
                        'Namespace': namespace,
                        'MetricName': metric_name,
                        'Dimensions': dimensions
                    },
                    'Period': period,
                    'Stat': stat
                },
                'ReturnData': True  # 모든 메트릭 데이터를 가져옴 (수학 표현식 계산에 필요)
            }

            # Label은 MetricStat 밖에 있어야 함
            if label:
                query['Label'] = label

            metric_data_queries.append(query)
            metric_labels[metric_id] = {
                'label': label or f'{metric_name} ({stat})',
                'color': color,
                'visible': visible  # visible 정보 저장
            }
            metric_order[metric_id] = idx  # JSON 순서 저장

        # 쿼리가 없으면 빈 리스트 반환
        if not metric_data_queries:
            return []

        # GetMetricData API 호출 (재시도 로직 포함)
        all_metric_data = []
        max_retries = 3
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                response = self.cloudwatch_client.get_metric_data(
                    MetricDataQueries=metric_data_queries,
                    StartTime=start_time,
                    EndTime=end_time
                )

                # 각 메트릭 결과 처리
                for result in response.get('MetricDataResults', []):
                    metric_id = result.get('Id')
                    metric_info = metric_labels.get(metric_id, {})

                    # metric_info가 dict인 경우와 아닌 경우 모두 처리
                    if isinstance(metric_info, dict):
                        label = result.get('Label') or metric_info.get('label', metric_id)
                        color = metric_info.get('color')
                        visible = metric_info.get('visible', True)
                    else:
                        label = result.get('Label') or metric_info
                        color = None
                        visible = True

                    timestamps = result.get('Timestamps', [])
                    values = result.get('Values', [])

                    # visible이 false인 메트릭은 차트에 표시하지 않음 (수학 표현식 계산용으로만 사용)
                    if not visible:
                        continue

                    # 타임스탬프 순으로 정렬
                    if timestamps and values:
                        sorted_data = sorted(zip(timestamps, values), key=lambda x: x[0])
                        timestamps, values = zip(*sorted_data)

                    formatted_data = {
                        'metric_id': metric_id,
                        'metric_name': metric_id,
                        'label': label,
                        'stat': 'Data',
                        'timestamps': [ts.isoformat() for ts in timestamps],
                        'values': list(values),
                        'unit': '',
                        'color': color  # 색상 정보 추가
                    }

                    all_metric_data.append(formatted_data)

                # JSON에 정의된 순서대로 정렬
                all_metric_data.sort(key=lambda x: metric_order.get(x['metric_id'], 999999))

                break  # 성공 시 재시도 루프 종료

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')

                if error_code == 'AccessDenied':
                    print(f'❌ AccessDenied: IAM 사용자에게 cloudwatch:GetMetricData 권한이 필요합니다.')
                    break
                elif error_code == 'Throttling' and attempt < max_retries - 1:
                    print(f'⚠️  Throttled, retrying ({attempt + 1}/{max_retries})...')
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    if attempt == max_retries - 1:
                        print(f'❌ Error fetching metric data after {max_retries} attempts: {e}')
                    else:
                        print(f'⚠️  Error fetching metric data (attempt {attempt + 1}): {e}')
                        time.sleep(retry_delay)
                        continue

            except Exception as e:
                print(f'❌ Unexpected error fetching metric data: {e}')
                break

        return all_metric_data


def get_module():
    """CloudWatchModule 인스턴스를 생성하고 반환하는 팩토리 함수.

    Returns:
        CloudWatchModule: CloudWatchModule의 인스턴스.
    """
    return CloudWatchModule()
