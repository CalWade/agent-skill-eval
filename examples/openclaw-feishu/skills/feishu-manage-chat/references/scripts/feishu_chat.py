"""
飞书群组管理 Python 封装
支持：创建群、添加/移除成员、修改群信息、发消息、获取群列表
"""
import json
import subprocess


def _curl(method, url, token=None, body=None):
    cmd = ['curl', '-s', '-X', method, url]
    if token:
        cmd += ['-H', f'Authorization: Bearer {token}']
    cmd += ['-H', 'Content-Type: application/json']
    if body:
        cmd += ['-d', json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def get_token(app_id, app_secret):
    """获取 tenant_access_token"""
    d = _curl('POST',
              'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
              body={'app_id': app_id, 'app_secret': app_secret})
    return d['tenant_access_token']


def create_chat(token, name, description='', owner_open_id=None, member_open_ids=None):
    """
    创建群组，返回 chat_id
    owner_open_id: 群主 Open ID（可选）
    member_open_ids: 初始成员列表（可选）
    """
    body = {'name': name, 'description': description}
    if owner_open_id:
        body['owner_id'] = owner_open_id
        body['owner_id_type'] = 'open_id'
    if member_open_ids:
        body['user_id_list'] = member_open_ids
    d = _curl('POST', 'https://open.feishu.cn/open-apis/im/v1/chats', token=token, body=body)
    return d['data']['chat_id']


def add_members(token, chat_id, open_ids):
    """添加成员，返回是否成功"""
    d = _curl('POST',
              f'https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members',
              token=token,
              body={'member_id_type': 'open_id', 'id_list': open_ids})
    return d.get('code') == 0, d.get('msg', '')


def remove_members(token, chat_id, open_ids):
    """移除成员，返回是否成功"""
    d = _curl('DELETE',
              f'https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members',
              token=token,
              body={'member_id_type': 'open_id', 'id_list': open_ids})
    return d.get('code') == 0, d.get('msg', '')


def update_chat(token, chat_id, name=None, description=None):
    """修改群名称或描述"""
    body = {}
    if name:
        body['name'] = name
    if description:
        body['description'] = description
    d = _curl('PATCH',
              f'https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}',
              token=token,
              body=body)
    return d.get('code') == 0, d.get('msg', '')


def send_message(token, chat_id, text):
    """发送文本消息到群"""
    d = _curl('POST',
              'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id',
              token=token,
              body={
                  'receive_id': chat_id,
                  'msg_type': 'text',
                  'content': json.dumps({'text': text})
              })
    return d.get('code') == 0, d.get('msg', '')


def list_chats(token, page_size=20):
    """获取 Bot 所在的群列表"""
    cmd = ['curl', '-s', '-X', 'GET',
           f'https://open.feishu.cn/open-apis/im/v1/chats?page_size={page_size}',
           '-H', f'Authorization: Bearer {token}']
    r = subprocess.run(cmd, capture_output=True, text=True)
    d = json.loads(r.stdout)
    return d.get('data', {}).get('items', [])


# ---- 使用示例 ----
if __name__ == '__main__':
    APP_ID = 'YOUR_APP_ID'
    APP_SECRET = 'YOUR_APP_SECRET'
    OWNER_OPEN_ID = 'ou_xxxxxxxxxxxxxxxx'
    MEMBERS = ['ou_aaa', 'ou_bbb']

    token = get_token(APP_ID, APP_SECRET)

    # 创建群
    chat_id = create_chat(token, name='项目启动群', description='自动建群',
                          owner_open_id=OWNER_OPEN_ID, member_open_ids=MEMBERS)
    print(f'群已创建: {chat_id}')

    # 发欢迎消息
    ok, msg = send_message(token, chat_id, '欢迎加入项目群！🎉')
    print('消息已发送' if ok else f'发送失败: {msg}')

    # 查看群列表
    chats = list_chats(token)
    for c in chats:
        print(f"  {c['name']} → {c['chat_id']}")
