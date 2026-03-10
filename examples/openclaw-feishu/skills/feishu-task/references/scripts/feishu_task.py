"""
飞书任务（Task v2）Python 封装
⚠️ 必须使用 User Access Token，不支持 Tenant token
支持：创建/分配/查询/更新/标记完成/重新打开任务
"""
import json
import subprocess
import time
from base64 import b64encode


BASE = 'https://open.feishu.cn/open-apis'


def _curl(method, url, token=None, body=None, params=None, auth_basic=None):
    cmd = ['curl', '-s', '-X', method]
    if params:
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        url = f'{url}?{qs}'
    cmd.append(url)
    if token:
        cmd += ['-H', f'Authorization: Bearer {token}']
    if auth_basic:
        cmd += ['-H', f'Authorization: Basic {auth_basic}']
    if body is not None:
        cmd += ['-H', 'Content-Type: application/json', '-d', json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def get_user_access_token(app_id, app_secret, code):
    """
    OAuth 2.0：用授权码换取 user_access_token
    code 来自 OAuth 回调 URL 参数
    """
    basic = b64encode(f'{app_id}:{app_secret}'.encode()).decode()
    d = _curl('POST', f'{BASE}/authen/v1/access_token',
              auth_basic=basic,
              body={'grant_type': 'authorization_code', 'code': code})
    return d['data']['access_token']


def create_task(uat, summary, description='', due_ms=None, is_all_day=False):
    """
    创建任务
    due_ms: Unix 毫秒时间戳（int），可选
    返回 task_guid
    """
    body = {
        'summary': summary,
        'description': description,
        'origin': {'platform_i18n_name': '{"zh_cn": "我的应用"}'},
    }
    if due_ms is not None:
        body['due'] = {
            'timestamp': str(due_ms),   # ⚠️ 必须是字符串
            'is_all_day': is_all_day,
        }
    d = _curl('POST', f'{BASE}/task/v2/tasks', token=uat, body=body)
    return d['data']['task']['guid']


def add_members(uat, task_guid, open_ids, role='assignee'):
    """
    添加负责人（或协作者）
    open_ids: list of open_id strings
    role: 'assignee'（负责人）| 'follower'（关注人）
    """
    members = [{'id': oid, 'type': 'user', 'role': role} for oid in open_ids]
    d = _curl('POST', f'{BASE}/task/v2/tasks/{task_guid}/add_members',
              token=uat,
              body={'members': members, 'user_id_type': 'open_id'})
    return d


def list_tasks(uat, completed=False, page_size=20):
    """
    查询当前用户任务列表
    completed: False=未完成 | True=已完成
    """
    d = _curl('GET', f'{BASE}/task/v2/tasks',
              token=uat,
              params={'page_size': page_size, 'completed': str(completed).lower()})
    return d['data'].get('items', [])


def get_task(uat, task_guid):
    """获取单个任务详情"""
    d = _curl('GET', f'{BASE}/task/v2/tasks/{task_guid}', token=uat)
    return d['data']['task']


def update_task(uat, task_guid, fields: dict, update_fields: list):
    """
    更新任务字段
    fields: 要更新的字段 dict（如 {"summary": "新标题"}）
    update_fields: 字段名列表（如 ["summary"]）
    """
    d = _curl('PATCH', f'{BASE}/task/v2/tasks/{task_guid}',
              token=uat,
              body={'task': fields, 'update_fields': update_fields})
    return d


def complete_task(uat, task_guid):
    """标记任务为已完成"""
    ms = str(int(time.time() * 1000))
    return update_task(uat, task_guid, {'completed_at': ms}, ['completed_at'])


def reopen_task(uat, task_guid):
    """重新打开已完成的任务"""
    return update_task(uat, task_guid, {'completed_at': '0'}, ['completed_at'])


def delete_task(uat, task_guid):
    """删除任务"""
    d = _curl('DELETE', f'{BASE}/task/v2/tasks/{task_guid}', token=uat)
    return d


# ---- 使用示例 ----
if __name__ == '__main__':
    # ⚠️ 替换为真实 user_access_token
    # （通过 OAuth 授权流程获取，不能用 tenant_access_token）
    UAT = 'YOUR_USER_ACCESS_TOKEN'
    ASSIGNEE = 'ou_your_open_id'

    # 创建任务（7 天后截止）
    due = int((time.time() + 7 * 86400) * 1000)
    guid = create_task(UAT, '完成 API 文档', '详细描述', due_ms=due)
    print(f'任务创建成功，guid: {guid}')

    # 添加负责人
    add_members(UAT, guid, [ASSIGNEE])
    print(f'已分配给 {ASSIGNEE}')

    # 查询未完成任务
    tasks = list_tasks(UAT, completed=False)
    print(f'未完成任务数: {len(tasks)}')
    for t in tasks:
        print(f"  [{t['guid'][:8]}...] {t['summary']}")

    # 标记完成
    complete_task(UAT, guid)
    print('任务已标记完成')

    # 重新打开
    reopen_task(UAT, guid)
    print('任务已重新打开')
