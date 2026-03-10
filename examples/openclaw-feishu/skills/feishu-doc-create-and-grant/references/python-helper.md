# Python 封装示例

适用于复杂多章节文档，推荐用于生产场景。

```python
import json
import subprocess

def get_token(app_id, app_secret):
    r = subprocess.run(
        ['curl', '-s', '-X', 'POST',
         'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps({'app_id': app_id, 'app_secret': app_secret})],
        capture_output=True, text=True
    )
    return json.loads(r.stdout)['tenant_access_token']


def create_doc(token, title):
    r = subprocess.run(
        ['curl', '-s', '-X', 'POST',
         'https://open.feishu.cn/open-apis/docx/v1/documents',
         '-H', f'Authorization: Bearer {token}',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps({'title': title})],
        capture_output=True, text=True
    )
    return json.loads(r.stdout)['data']['document']['document_id']


def write_blocks(token, doc_id, blocks, index=0):
    r = subprocess.run(
        ['curl', '-s', '-X', 'POST',
         f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
         '-H', f'Authorization: Bearer {token}',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps({'children': blocks, 'index': index})],
        capture_output=True, text=True
    )
    result = json.loads(r.stdout)
    return result.get('code') == 0


def clear_doc(token, doc_id, end_index=50):
    """清空文档内容，end_index 填实际 block 数量"""
    subprocess.run(
        ['curl', '-s', '-X', 'DELETE',
         f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children/batch_delete',
         '-H', f'Authorization: Bearer {token}',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps({'start_index': 0, 'end_index': end_index})],
        capture_output=True, text=True
    )


# ── Block 构建函数 ──────────────────────────────────────────

def h1(text):
    return {"block_type": 2, "text": {"elements": [{"text_run": {"content": text}}], "style": {"headingLevel": 1}}}

def h2(text):
    return {"block_type": 2, "text": {"elements": [{"text_run": {"content": text}}], "style": {"headingLevel": 2}}}

def h3(text):
    return {"block_type": 2, "text": {"elements": [{"text_run": {"content": text}}], "style": {"headingLevel": 3}}}

def p(text):
    return {"block_type": 2, "text": {"elements": [{"text_run": {"content": text}}]}}

def code(text, lang=3):
    """lang: 1=Go 2=Python 3=Shell 4=JavaScript 49=Bash"""
    return {"block_type": 14, "code": {"elements": [{"text_run": {"content": text}}], "style": {"language": lang}}}

def ol(text):
    return {"block_type": 3, "ordered": {"elements": [{"text_run": {"content": text}}]}}

def ul(text):
    return {"block_type": 4, "bullet": {"elements": [{"text_run": {"content": text}}]}}


# ── 使用示例 ────────────────────────────────────────────────

if __name__ == '__main__':
    APP_ID = 'YOUR_APP_ID'
    APP_SECRET = 'YOUR_APP_SECRET'

    token = get_token(APP_ID, APP_SECRET)
    doc_id = create_doc(token, '龙虾机器人自动生成的文档')

    blocks = [
        h1('第一章：概述'),
        p('本文档由龙虾机器人自动生成。'),
        h2('1.1 背景'),
        p('飞书云文档支持通过 REST API 全自动创建和写入。'),
        h2('1.2 示例代码'),
        code('echo "Hello from Agent"', lang=3),
        h1('第二章：使用方法'),
        ul('步骤一：获取 token'),
        ul('步骤二：创建文档'),
        ul('步骤三：写入内容'),
    ]

    success = write_blocks(token, doc_id, blocks)
    print(f'写入{"成功" if success else "失败"}')
    print(f'文档链接：https://bytedance.larkoffice.com/docx/{doc_id}')
```
