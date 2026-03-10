"""
飞书消息读取 Python 封装
支持：读取消息内容、解析 @提及 用户、下载图片/文件附件
"""
import json
import subprocess


def _curl(method, url, token=None, output_file=None):
    cmd = ['curl', '-s', '-X', method, url]
    if token:
        cmd += ['-H', f'Authorization: Bearer {token}']
    if output_file:
        cmd += ['-o', output_file]
        subprocess.run(cmd)
        return None
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)


def get_token(app_id, app_secret):
    """获取 tenant_access_token"""
    d = _curl('POST',
              'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal')
    # 直接用 curl 带 body
    cmd = ['curl', '-s', '-X', 'POST',
           'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
           '-H', 'Content-Type: application/json',
           '-d', json.dumps({'app_id': app_id, 'app_secret': app_secret})]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)['tenant_access_token']


def read_message(token, message_id):
    """
    读取消息，返回 dict，包含：
      - msg_type: 消息类型
      - content: 消息内容（已解析为 dict）
      - sender_id: 发送人 open_id
      - mentions: 被 @ 用户列表 [{"id", "name", "key"}]
    """
    d = _curl('GET',
              f'https://open.feishu.cn/open-apis/im/v1/messages/{message_id}',
              token=token)
    item = d['data']['items'][0]
    return {
        'msg_type': item['msg_type'],
        'content': json.loads(item['body']['content']),
        'sender_id': item['sender']['id'],
        'mentions': [
            {'id': m['id'], 'name': m['name'], 'key': m['key']}
            for m in item.get('mentions', [])
        ],
        '_raw': item
    }


def download_image(token, message_id, image_key, save_path='/tmp/feishu_image.jpg'):
    """
    下载图片附件
    ⚠️ 必须同时传 message_id + image_key，不能只用 image_key
    """
    url = f'https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{image_key}?type=image'
    cmd = ['curl', '-s', '-o', save_path, url, '-H', f'Authorization: Bearer {token}']
    subprocess.run(cmd)
    return save_path


def download_file(token, message_id, file_key, save_path='/tmp/feishu_file'):
    """下载文件附件"""
    url = f'https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}?type=file'
    cmd = ['curl', '-s', '-o', save_path, url, '-H', f'Authorization: Bearer {token}']
    subprocess.run(cmd)
    return save_path


# ---- 使用示例 ----
if __name__ == '__main__':
    APP_ID = 'YOUR_APP_ID'
    APP_SECRET = 'YOUR_APP_SECRET'
    MSG_ID = 'om_xxxxxxxx'  # 来自 webhook 回调的 message.message_id

    token = get_token(APP_ID, APP_SECRET)

    # 读取消息
    msg = read_message(token, MSG_ID)
    print(f"消息类型: {msg['msg_type']}")
    print(f"消息内容: {msg['content']}")
    print(f"发送人: {msg['sender_id']}")

    # 解析 @提及
    for m in msg['mentions']:
        print(f"@提及: {m['name']} → {m['id']}")

    # 下载图片（如果是图片消息）
    if msg['msg_type'] == 'image':
        img_key = msg['content'].get('image_key')
        if img_key:
            path = download_image(token, MSG_ID, img_key, '/tmp/feishu_img.jpg')
            print(f"图片已保存: {path}")

    # 下载文件（如果是文件消息）
    if msg['msg_type'] == 'file':
        file_key = msg['content'].get('file_key')
        if file_key:
            path = download_file(token, MSG_ID, file_key, '/tmp/feishu_file')
            print(f"文件已保存: {path}")
