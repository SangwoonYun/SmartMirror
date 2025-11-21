# modules/cloudwatch/module.py

import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import aioboto3
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config import MODULE_LAYOUT
from module import APIModule


class CloudWatchModule(APIModule):
    """AWS CloudWatch 대시보드를 표시하는 모듈.

    이 모듈은 AWS CloudWatch API를 통해 대시보드 정의를 가져오고,
    각 위젯에 정의된 메트릭 데이터를 조회하여 프론트엔드에서 차트로 렌더링합니다.

    병렬 처리 모드:
        - threading: ThreadPoolExecutor를 사용한 멀티스레딩 (기본값, 빠른 성능)
        - async: asyncio/aioboto3를 사용한 비동기 처리 (리소스 효율적)
    """

    # 상수 정의
    DEFAULT_REGION = 'us-west-2'
    DEFAULT_PERIOD = 900  # 15분
    DEFAULT_TIME_RANGE_HOURS = 8
    DEFAULT_REFRESH_INTERVAL = 900000  # 15분 (밀리초)
    MAX_RETRIES = 2
    RETRY_DELAY = 0.3
    MAX_SORT_ORDER = 999999  # 정렬 시 최대값

    def __init__(self):
        super().__init__()
        config = self._get_config()

        self.region = config.get('region', self.DEFAULT_REGION)
        self.parallel_mode = config.get('parallel_mode', 'threading')
        self.max_workers = config.get('max_workers', None)

        # parallel_mode에 따라 클라이언트/세션 초기화
        if self.parallel_mode == 'async':
            self.session = aioboto3.Session()
            self.cloudwatch_client = None
        else:
            self.session = None
            self.cloudwatch_client = boto3.client('cloudwatch', region_name=self.region)

    @property
    def name(self):
        """모듈 이름 반환."""
        return 'cloudwatch'

    def _get_config(self):
        """CloudWatch 설정 조회."""
        return MODULE_LAYOUT.get('cloudwatch', {})

    def render(self):
        """모듈 UI를 HTML로 렌더링."""
        config = self._get_config()

        refresh_interval = config.get('refresh_interval', self.DEFAULT_REFRESH_INTERVAL)
        options = config.get('options', {})
        style = ' '.join(f'{key}: {value};' for key, value in options.items())

        dashboard_name = config.get('dashboard_name', '')
        title = config.get('title', 'AWS CloudWatch')
        if dashboard_name:
            title += f' - {dashboard_name}'

        return self.render_template(
            f'{os.path.dirname(os.path.abspath(__file__))}/templates/base.html',
            style=style,
            refresh_interval=refresh_interval,
            title=title
        )

    def api(self):
        """CloudWatch 대시보드 데이터를 반환하는 API 엔드포인트.

        parallel_mode 설정에 따라 threading 또는 async 방식으로 처리합니다.

        Returns:
            dict: 대시보드 위젯 정보와 메트릭 데이터
                {
                    'widgets': [...],
                    'error': None or str
                }
        """
        if self.parallel_mode == 'async':
            return asyncio.run(self._api_async())
        return self._api_threading()

    def _api_threading(self):
        """멀티스레딩으로 대시보드 데이터 조회."""
        dashboard_def = self._get_dashboard()
        if isinstance(dashboard_def, dict) and 'error' in dashboard_def:
            return dashboard_def

        widgets = dashboard_def.get('widgets', [])
        max_workers = self.max_workers or len(widgets)

        widgets_result = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_widget = {
                executor.submit(self._process_widget_sync, widget): widget
                for widget in widgets
            }

            for future in as_completed(future_to_widget):
                try:
                    widget_data = future.result()
                    if widget_data:
                        widgets_result.append(widget_data)
                except Exception as e:
                    print(f"Error processing widget: {e}")

        widgets_result.sort(key=lambda w: (w.get('y', 0), w.get('x', 0)))

        return {
            'widgets': widgets_result,
            'error': None
        }

    async def _api_async(self):
        """비동기로 대시보드 데이터 조회."""
        config = self._get_config()
        dashboard_name = config.get('dashboard_name', '')
        dashboard_body = config.get('dashboard_body', None)

        if dashboard_body:
            dashboard_def = dashboard_body
        elif dashboard_name:
            dashboard_def = await self._get_dashboard_definition_async(dashboard_name)
        else:
            return self._error_response('No dashboard_name or dashboard_body configured.')

        if not dashboard_def or 'widgets' not in dashboard_def:
            return self._error_response('Invalid dashboard definition.')

        widgets = dashboard_def.get('widgets', [])
        tasks = [self._process_widget_async(widget) for widget in widgets]
        widgets_with_data = await asyncio.gather(*tasks, return_exceptions=True)

        widgets_result = []
        for i, result in enumerate(widgets_with_data):
            if isinstance(result, Exception):
                print(f"Error processing widget {i}: {result}")
            elif result:
                widgets_result.append(result)

        widgets_result.sort(key=lambda w: (w.get('y', 0), w.get('x', 0)))

        return {
            'widgets': widgets_result,
            'error': None
        }

    def _get_dashboard(self):
        """대시보드 정의 가져오기 (동기)."""
        config = self._get_config()
        dashboard_name = config.get('dashboard_name', '')
        dashboard_body = config.get('dashboard_body', None)

        if dashboard_body:
            return dashboard_body
        if dashboard_name:
            dashboard_def = self.get_dashboard_definition(dashboard_name)
            if not dashboard_def or 'widgets' not in dashboard_def:
                return self._error_response('Invalid dashboard definition.')
            return dashboard_def
        return self._error_response('No dashboard_name or dashboard_body configured.')

    def _error_response(self, error_msg):
        """에러 응답 생성."""
        return {
            'error': error_msg,
            'widgets': []
        }

    async def _get_dashboard_definition_async(self, dashboard_name):
        """AWS CloudWatch에서 대시보드 정의를 비동기로 가져오기."""
        try:
            async with self.session.client('cloudwatch', region_name=self.region) as client:
                response = await client.get_dashboard(DashboardName=dashboard_name)
                dashboard_body = response.get('DashboardBody', '{}')
                return json.loads(dashboard_body)
        except ClientError as e:
            print(f'Error fetching dashboard: {e}')
            return None

    def get_dashboard_definition(self, dashboard_name):
        """AWS CloudWatch에서 대시보드 정의 가져오기."""
        if self.parallel_mode == 'async':
            return asyncio.run(self._get_dashboard_definition_async(dashboard_name))

        try:
            response = self.cloudwatch_client.get_dashboard(DashboardName=dashboard_name)
            dashboard_body = response.get('DashboardBody', '{}')
            return json.loads(dashboard_body)
        except ClientError as e:
            print(f'Error fetching dashboard: {e}')
            return None

    def _process_widget_sync(self, widget):
        """위젯 처리 (동기)."""
        widget_info = self._extract_widget_info(widget)

        if widget_info['type'] == 'metric':
            properties = widget.get('properties', {})
            metrics = properties.get('metrics', [])
            config = self._get_config()
            period = config.get('period', self.DEFAULT_PERIOD)
            stat = properties.get('stat', 'Average')

            widget_info['data'] = self.get_metric_data(metrics, period, stat)
        else:
            widget_info['data'] = []

        return widget_info

    async def _process_widget_async(self, widget):
        """위젯 처리 (비동기)."""
        widget_info = self._extract_widget_info(widget)

        if widget_info['type'] == 'metric':
            properties = widget.get('properties', {})
            metrics = properties.get('metrics', [])
            config = self._get_config()
            period = properties.get('period', config.get('period', self.DEFAULT_PERIOD))
            stat = properties.get('stat', 'Average')

            widget_info['data'] = await self._get_metric_data_async(metrics, period, stat)
        else:
            widget_info['data'] = []

        return widget_info

    def _extract_widget_info(self, widget):
        """위젯에서 기본 정보 추출."""
        widget_type = widget.get('type', 'metric')
        properties = widget.get('properties', {})

        widget_info = {
            'type': widget_type,
            'x': widget.get('x', 0),
            'y': widget.get('y', 0),
            'width': widget.get('width', 6),
            'height': widget.get('height', 6),
            'title': properties.get('title', 'Untitled'),
            'region': properties.get('region', self.DEFAULT_REGION),
        }

        # y축 설정
        y_axis = properties.get('yAxis')
        if y_axis:
            widget_info['yAxis'] = y_axis

        # annotations 설정 (임계값 선 등)
        annotations = properties.get('annotations')
        if annotations:
            widget_info['annotations'] = annotations

        return widget_info

    async def _get_metric_data_async(self, metrics, period, default_stat='Average'):
        """메트릭 데이터를 비동기로 조회 (수학 표현식 지원)."""
        queries, labels, order = self._build_metric_queries(metrics, period, default_stat)

        if not queries:
            return []

        config = self._get_config()
        time_range = config.get('time_range_hours', self.DEFAULT_TIME_RANGE_HOURS)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range)

        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.session.client('cloudwatch', region_name=self.region) as client:
                    response = await client.get_metric_data(
                        MetricDataQueries=queries,
                        StartTime=start_time,
                        EndTime=end_time
                    )
                    return self._process_metric_results(response, labels, order)

            except ClientError as e:
                if not self._handle_api_error(e, attempt):
                    break
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))

            except Exception as e:
                print(f'Unexpected error fetching metric data: {e}')
                break

        return []

    def get_metric_data(self, metrics, period, default_stat='Average'):
        """메트릭 데이터를 동기로 조회 (수학 표현식 지원)."""
        queries, labels, order = self._build_metric_queries(metrics, period, default_stat)

        if not queries:
            return []

        config = self._get_config()
        time_range = config.get('time_range_hours', self.DEFAULT_TIME_RANGE_HOURS)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range)

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.cloudwatch_client.get_metric_data(
                    MetricDataQueries=queries,
                    StartTime=start_time,
                    EndTime=end_time
                )
                return self._process_metric_results(response, labels, order)

            except ClientError as e:
                if not self._handle_api_error(e, attempt):
                    break
                time.sleep(self.RETRY_DELAY * (attempt + 1))

            except Exception as e:
                print(f'Unexpected error fetching metric data: {e}')
                break

        return []

    def _build_metric_queries(self, metrics, period, default_stat):
        """메트릭 쿼리 빌드.

        Returns:
            tuple: (queries, labels, order)
                - queries: CloudWatch API용 쿼리 리스트
                - labels: 메트릭 ID별 메타데이터
                - order: 메트릭 ID별 순서
        """
        queries = []
        labels = {}
        order = {}

        # 점 표기법(.) 처리를 위한 이전 값 추적
        previous_namespace = None
        previous_metric_name = None
        previous_dimensions = {}

        for idx, metric_def in enumerate(metrics):
            if not isinstance(metric_def, list):
                continue

            # 수학 표현식 처리
            if len(metric_def) > 0 and isinstance(metric_def[0], dict):
                expr_query, expr_label = self._build_expression_query(metric_def[0], idx)
                if expr_query:
                    queries.append(expr_query)
                    labels[expr_query['Id']] = expr_label
                    order[expr_query['Id']] = idx
                continue

            # 일반 메트릭 처리
            if len(metric_def) < 2:
                continue

            namespace, metric_name, dimensions = self._parse_metric_definition(
                metric_def, previous_namespace, previous_metric_name, previous_dimensions
            )

            # 이전 값 업데이트
            previous_namespace = namespace
            previous_metric_name = metric_name
            if dimensions:
                previous_dimensions = dimensions

            # 메트릭 속성 파싱
            stat, label, visible, metric_id, color = self._parse_metric_attributes(
                metric_def, default_stat, idx, metric_name
            )

            # 쿼리 생성
            query = self._build_metric_stat_query(
                metric_id, namespace, metric_name, dimensions, period, stat, label
            )

            queries.append(query)
            labels[metric_id] = {
                'label': label or f'{metric_name} ({stat})',
                'color': color,
                'visible': visible
            }
            order[metric_id] = idx

        return queries, labels, order

    def _build_expression_query(self, math_expr, idx):
        """수학 표현식 쿼리 빌드."""
        expression = math_expr.get('expression')
        if not expression:
            return None, None

        metric_id = math_expr.get('id', f'e{idx}')
        label = math_expr.get('label', f'Expression {idx}')
        visible = math_expr.get('visible', True)
        color = math_expr.get('color')

        query = {
            'Id': metric_id,
            'Expression': expression,
            'Label': label,
            'ReturnData': True
        }

        label_info = {
            'label': label,
            'color': color,
            'visible': visible
        }

        return query, label_info

    def _parse_metric_definition(self, metric_def, prev_namespace, prev_metric_name, prev_dimensions):
        """메트릭 정의에서 namespace, metric_name, dimensions 파싱.

        점 표기법(.)을 지원하여 이전 값을 재사용합니다.
        """
        namespace = metric_def[0]
        metric_name = metric_def[1]

        # 점 표기법 처리
        if namespace == '.' and prev_namespace:
            namespace = prev_namespace
        if metric_name == '.' and prev_metric_name:
            metric_name = prev_metric_name

        # 차원 파싱
        dimensions = []
        i = 2
        while i < len(metric_def):
            if isinstance(metric_def[i], str) and i + 1 < len(metric_def):
                if isinstance(metric_def[i + 1], str):
                    dim_name = metric_def[i]
                    dim_value = metric_def[i + 1]

                    # 점 표기법 처리
                    if dim_name == '.' and prev_dimensions:
                        dim_index = len(dimensions)
                        if dim_index < len(prev_dimensions):
                            dim_name = prev_dimensions[dim_index]['Name']

                    if dim_value == '.' and prev_dimensions:
                        for prev_dim in prev_dimensions:
                            if prev_dim['Name'] == dim_name:
                                dim_value = prev_dim['Value']
                                break

                    if dim_name != '.' and dim_value != '.':
                        dimensions.append({
                            'Name': dim_name,
                            'Value': dim_value
                        })

                    i += 2
                elif isinstance(metric_def[i + 1], dict):
                    break
                else:
                    i += 1
            else:
                i += 1

        return namespace, metric_name, dimensions

    def _parse_metric_attributes(self, metric_def, default_stat, idx, metric_name):
        """메트릭 속성 파싱 (stat, label, visible, id, color)."""
        stat = default_stat
        label = None
        visible = True
        metric_id = f'm{idx}'
        color = None

        for item in metric_def:
            if isinstance(item, dict):
                stat = item.get('stat', stat)
                label = item.get('label', label)
                visible = item.get('visible', visible)
                metric_id = item.get('id', metric_id)
                color = item.get('color', color)

        return stat, label, visible, metric_id, color

    def _build_metric_stat_query(self, metric_id, namespace, metric_name, dimensions, period, stat, label):
        """MetricStat 쿼리 생성."""
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
            'ReturnData': True
        }

        if label:
            query['Label'] = label

        return query

    def _process_metric_results(self, response, labels, order):
        """CloudWatch API 응답 처리."""
        results = []

        for result in response.get('MetricDataResults', []):
            metric_id = result.get('Id')
            metric_info = labels.get(metric_id, {})

            if isinstance(metric_info, dict):
                label = result.get('Label') or metric_info.get('label', metric_id)
                color = metric_info.get('color')
                visible = metric_info.get('visible', True)
            else:
                label = result.get('Label') or metric_info
                color = None
                visible = True

            # visible=false인 메트릭은 수학 표현식 계산용으로만 사용
            if not visible:
                continue

            timestamps = result.get('Timestamps', [])
            values = result.get('Values', [])

            # 타임스탬프 순으로 정렬
            if timestamps and values:
                sorted_data = sorted(zip(timestamps, values), key=lambda x: x[0])
                timestamps, values = zip(*sorted_data)

            results.append({
                'metric_id': metric_id,
                'metric_name': metric_id,
                'label': label,
                'stat': 'Data',
                'timestamps': [ts.isoformat() for ts in timestamps],
                'values': list(values),
                'unit': '',
                'color': color
            })

        # JSON에 정의된 순서대로 정렬
        results.sort(key=lambda x: order.get(x['metric_id'], self.MAX_SORT_ORDER))
        return results

    def _handle_api_error(self, error, attempt):
        """API 에러 처리.

        Returns:
            bool: 재시도 여부 (True면 재시도)
        """
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')

        if error_code == 'AccessDenied':
            print('AccessDenied: IAM user needs cloudwatch:GetMetricData permission')
            return False

        if error_code == 'Throttling' and attempt < self.MAX_RETRIES - 1:
            print(f'Throttled, retrying ({attempt + 1}/{self.MAX_RETRIES})...')
            return True

        if attempt == self.MAX_RETRIES - 1:
            print(f'Error fetching metric data after {self.MAX_RETRIES} attempts: {error}')
        else:
            print(f'Error fetching metric data (attempt {attempt + 1}): {error}')
            return True

        return False


def get_module():
    """CloudWatchModule 인스턴스를 생성하고 반환하는 팩토리 함수.

    Returns:
        CloudWatchModule: CloudWatchModule의 인스턴스
    """
    return CloudWatchModule()
