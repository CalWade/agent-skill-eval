"""
飞书云文档：创建 + 写入 + 授权
Python 封装，可直接复用
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
    """获取 tenant_access_token（有效期 2 小时）"""
    d = _curl('POST',
              'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
              body={'app_id': app_id, 'app_secret': app_secret})
    return d['tenant_access_token']


def create_doc(token, title):
    """创建文档，返回 document_id"""
    d = _curl('POST',
              'https://open.feishu.cn/open-apis/docx/v1/documents',
              token=token,
              body={'title': title})
    return d['data']['document']['document_id']


def write_blocks(token, doc_id, blocks, index=0):
    """写入内容块，返回是否成功"""
    d = _curl('POST',
              f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
              token=token,
              body={'children': blocks, 'index': index})
    return d.get('code') == 0


def grant_permission(token, doc_id, open_id, perm='full_access'):
    """
    授权给指定用户
    perm: 'view'（只读）/ 'edit'（编辑）/ 'full_access'（完全控制）
    """
    cmd = [
        'curl', '-s', '-X', 'POST',
        f'https://open.feishu.cn/open-apis/drive/v1/permissions/{doc_id}/members?type=docx',
        '-H', f'Authorization: Bearer {token}',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            'member_type': 'openid',
            'member_id': open_id,
            'perm': perm,
            'perm_type': 'container'
        })
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    d = json.loads(r.stdout)
    return d['code'] == 0, d.get('msg', '')


def create_doc_with_permission(app_id, app_secret, title, blocks, owner_open_id, perm='full_access'):
    """
    一步完成：创建文档 + 写入内容 + 授权给主人
    返回文档链接
    """
    token = get_token(app_id, app_secret)
    doc_id = create_doc(token, title)
    write_blocks(token, doc_id, blocks)
    ok, msg = grant_permission(token, doc_id, owner_open_id, perm)
    if not ok:
        print(f'⚠️ 授权失败: {msg}')
    url = f'https://bytedance.larkoffice.com/docx/{doc_id}'
    return url, doc_id


# ---- 使用示例 ----
if __name__ == '__main__':
    APP_ID = 'YOUR_APP_ID'
    APP_SECRET = 'YOUR_APP_SECRET'
    OWNER_OPEN_ID = 'ou_xxxxxxxxxxxxxxxx'

    blocks = [
        {
            'block_type': 2,
            'text': {
                'elements': [{'text_run': {'content': '一、介绍'}}],
                'style': {'headingLevel': 1}
            }
        },
        {
            'block_type': 2,
            'text': {
                'elements': [{'text_run': {'content': '这是正文内容。'}}]
            }
        }
    ]

    url, doc_id = create_doc_with_permission(
        APP_ID, APP_SECRET,
        title='测试文档',
        blocks=blocks,
        owner_open_id=OWNER_OPEN_ID
    )
    print(f'✅ 文档链接：{url}')
