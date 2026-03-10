"""
飞书多维表格（Bitable）Python 封装
支持：创建多维表格、获取 table_id、管理字段、批量写入/查询/更新/删除记录
"""
import json
import subprocess
import time


def _curl(method, url, token=None, body=None, params=None):
    cmd = ['curl', '-s', '-X', method]
    if params:
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        url = f'{url}?{qs}'
    cmd.append(url)
    if token:
        cmd += ['-H', f'Authorization: Bearer {token}']
    if body is not None:
        cmd += ['-H', 'Content-Type: application/json', '-d', json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


BASE = 'https://open.feishu.cn/open-apis'


def get_token(app_id, app_secret):
    """获取 tenant_access_token"""
    d = _curl('POST', f'{BASE}/auth/v3/tenant_access_token/internal',
              body={'app_id': app_id, 'app_secret': app_secret})
    return d['tenant_access_token']


def create_bitable(token, name='工作日志'):
    """
    创建多维表格
    返回 app_token
    """
    d = _curl('POST', f'{BASE}/bitable/v1/apps', token=token, body={'name': name})
    return d['data']['app']['app_token']


def get_table_id(token, app_token, index=0):
    """获取指定 index 的 table_id（默认第一张数据表）"""
    d = _curl('GET', f'{BASE}/bitable/v1/apps/{app_token}/tables', token=token)
    return d['data']['items'][index]['table_id']


def create_field(token, app_token, table_id, field_name, field_type, property=None):
    """
    创建字段
    field_type: 1=文本 2=数字 3=单选 4=多选 5=日期 11=人员 15=超链接
    property 示例（单选）: {"options": [{"name": "进行中", "color": 1}]}
    """
    body = {'field_name': field_name, 'type': field_type}
    if property:
        body['property'] = property
    d = _curl('POST', f'{BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields',
              token=token, body=body)
    return d['data']['field']


def list_fields(token, app_token, table_id):
    """获取字段列表"""
    d = _curl('GET', f'{BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields',
              token=token)
    return d['data']['items']


def batch_create_records(token, app_token, table_id, records):
    """
    批量写入记录
    records: list of dicts, 每个 dict 是 fields 键值对
    示例: [{"任务名称": "完成API对接", "状态": {"text": "进行中"}}]

    注意：
    - 日期字段传 Unix 毫秒时间戳（int）
    - 超链接字段传 {"link": "https://...", "text": "显示文字"}
    - 单选字段传 {"text": "选项名"} 或 {"text": "选项名", "id": "optXxx"}
    """
    payload = {'records': [{'fields': r} for r in records]}
    d = _curl('POST',
              f'{BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create',
              token=token, body=payload)
    return d['data']['records']


def list_records(token, app_token, table_id, page_size=20, filter=None, sort=None):
    """
    查询记录
    filter 示例: 'AND(CurrentValue.[状态]="进行中")'
    sort 示例: [{"field_name":"完成时间","desc":true}]
    """
    params = {'page_size': page_size}
    if filter:
        params['filter'] = filter
    if sort:
        params['sort'] = json.dumps(sort)
    d = _curl('GET',
              f'{BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records',
              token=token, params=params)
    return d['data'].get('items', [])


def update_record(token, app_token, table_id, record_id, fields):
    """更新单条记录"""
    d = _curl('PATCH',
              f'{BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}',
              token=token, body={'fields': fields})
    return d


def delete_record(token, app_token, table_id, record_id):
    """删除单条记录"""
    d = _curl('DELETE',
              f'{BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}',
              token=token)
    return d


def clear_empty_rows(token, app_token, table_id):
    """清除新建表格时自动生成的空行"""
    records = list_records(token, app_token, table_id, page_size=50)
    deleted = 0
    for r in records:
        if not r.get('fields'):
            delete_record(token, app_token, table_id, r['record_id'])
            deleted += 1
    return deleted


# ---- 使用示例 ----
if __name__ == '__main__':
    APP_ID = 'YOUR_APP_ID'
    APP_SECRET = 'YOUR_APP_SECRET'

    token = get_token(APP_ID, APP_SECRET)

    # 创建多维表格
    app_token = create_bitable(token, '工作日志')
    print(f'app_token: {app_token}')
    print(f'表格链接: https://feishu.cn/base/{app_token}')

    # 获取 table_id
    table_id = get_table_id(token, app_token)
    print(f'table_id: {table_id}')

    # 清除默认空行
    n = clear_empty_rows(token, app_token, table_id)
    print(f'清除 {n} 条空行')

    # 创建「状态」单选字段
    create_field(token, app_token, table_id, '状态', 3, {
        'options': [
            {'name': '进行中', 'color': 1},
            {'name': '已完成', 'color': 2},
            {'name': '待处理', 'color': 0},
        ]
    })
    print('字段「状态」创建成功')

    # 批量写入记录
    now_ms = int(time.time() * 1000)
    records = batch_create_records(token, app_token, table_id, [
        {'多行文本': '完成 API 对接', '状态': {'text': '进行中'}},
        {'多行文本': '编写技术文档', '状态': {'text': '已完成'}},
        {'多行文本': '部署上线', '状态': {'text': '待处理'}},
    ])
    print(f'写入 {len(records)} 条记录')

    # 查询验证
    items = list_records(token, app_token, table_id)
    for item in items:
        print(item['record_id'], '|', item.get('fields', {}))
