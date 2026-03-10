"""
飞书审批（Approval v4）Python 封装
支持：获取 token、查看审批定义、发起/查询/通过/拒绝/取消审批
使用 Tenant Access Token（区别于 Task API 的 User token）
"""
import json
import subprocess
import time


BASE = 'https://open.feishu.cn/open-apis'


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


def get_tenant_token(app_id, app_secret):
    """获取 Tenant Access Token"""
    d = _curl('POST', f'{BASE}/auth/v3/tenant_access_token/internal',
              body={'app_id': app_id, 'app_secret': app_secret})
    return d['tenant_access_token']


def get_approval_definition(token, approval_code):
    """
    获取审批定义（表单字段结构）
    发起审批前调用，确认 form 中需要填写哪些 widget
    """
    d = _curl('GET', f'{BASE}/approval/v4/approvals/{approval_code}', token=token)
    return d.get('data', {})


def create_instance(token, approval_code, user_open_id, form_widgets):
    """
    发起审批实例
    form_widgets: list of dict, 如 [{"id": "widget1", "type": "input", "value": "请假原因"}]
    ⚠️ form 在 API 中是 JSON 字符串，此函数自动序列化
    """
    body = {
        'approval_code': approval_code,
        'user_id': user_open_id,
        'user_id_type': 'open_id',
        'form': json.dumps(form_widgets),  # ⚠️ 序列化为字符串
    }
    d = _curl('POST', f'{BASE}/approval/v4/instances', token=token, body=body)
    if d.get('code') != 0:
        raise RuntimeError(f"发起审批失败: {d}")
    return d['data']['instance_id']


def get_instance(token, instance_id):
    """
    查询审批实例详情
    返回 dict，关键字段：
    - status: PENDING / APPROVED / REJECTED / CANCELED
    - task_list: 当前待审批任务列表（含 task_id）
    """
    d = _curl('GET', f'{BASE}/approval/v4/instances/{instance_id}', token=token)
    return d.get('data', {})


def get_pending_task_id(token, instance_id):
    """获取当前待处理任务的 task_id（审批通过/拒绝时必需）"""
    instance = get_instance(token, instance_id)
    tasks = instance.get('task_list', [])
    if not tasks:
        raise RuntimeError("没有待处理任务，审批可能已完成或已取消")
    return tasks[0]['id']


def approve(token, instance_id, approver_open_id, comment='同意'):
    """审批通过"""
    task_id = get_pending_task_id(token, instance_id)
    d = _curl('POST', f'{BASE}/approval/v4/instances/{instance_id}/approve',
              token=token,
              body={
                  'user_id': approver_open_id,
                  'task_id': task_id,
                  'comment': comment,
                  'user_id_type': 'open_id',
              })
    if d.get('code') != 0:
        raise RuntimeError(f"审批通过失败: {d}")
    return d


def reject(token, instance_id, approver_open_id, comment='不符合条件，请重新提交'):
    """审批拒绝"""
    task_id = get_pending_task_id(token, instance_id)
    d = _curl('POST', f'{BASE}/approval/v4/instances/{instance_id}/reject',
              token=token,
              body={
                  'user_id': approver_open_id,
                  'task_id': task_id,
                  'comment': comment,
                  'user_id_type': 'open_id',
              })
    if d.get('code') != 0:
        raise RuntimeError(f"审批拒绝失败: {d}")
    return d


def cancel(token, instance_id, user_open_id):
    """撤销审批实例（仅申请人可撤销，且状态为 PENDING）"""
    d = _curl('POST', f'{BASE}/approval/v4/instances/{instance_id}/cancel',
              token=token,
              body={'user_id': user_open_id, 'user_id_type': 'open_id'})
    return d


def poll_until_done(token, instance_id, max_wait=60, interval=5):
    """
    轮询直到审批完成（非 PENDING）
    max_wait: 最长等待秒数
    interval: 轮询间隔秒数
    返回最终 status
    """
    elapsed = 0
    while elapsed < max_wait:
        instance = get_instance(token, instance_id)
        status = instance.get('status', 'UNKNOWN')
        print(f"  [{elapsed}s] 当前状态: {status}")
        if status != 'PENDING':
            return status
        time.sleep(interval)
        elapsed += interval
    return 'TIMEOUT'


# ---- 使用示例 ----
if __name__ == '__main__':
    APP_ID = 'YOUR_APP_ID'
    APP_SECRET = 'YOUR_APP_SECRET'
    APPROVAL_CODE = 'YOUR_APPROVAL_CODE'   # 审批定义 code
    APPLICANT = 'ou_applicant_open_id'     # 申请人
    APPROVER = 'ou_approver_open_id'       # 审批人

    # 1. 获取 token
    token = get_tenant_token(APP_ID, APP_SECRET)
    print(f"Token: {token[:20]}...")

    # 2. 查看审批定义（确认 form 字段）
    defn = get_approval_definition(token, APPROVAL_CODE)
    print(f"审批名称: {defn.get('approval_name')}")

    # 3. 发起审批（form 字段需与定义一致）
    form = [{'id': 'widget1', 'type': 'input', 'value': '测试请假：2025-01-01 至 2025-01-03'}]
    instance_id = create_instance(token, APPROVAL_CODE, APPLICANT, form)
    print(f"审批实例 ID: {instance_id}")

    # 4. 查询当前状态
    instance = get_instance(token, instance_id)
    print(f"当前状态: {instance['status']}")

    # 5. 自动审批通过
    approve(token, instance_id, APPROVER, comment='自动通过')
    print("审批已通过")

    # 6. 确认最终状态
    final = get_instance(token, instance_id)
    print(f"最终状态: {final['status']}")
