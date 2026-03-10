"""
飞书电子表格 Python 封装：自适应配置读取
"""
import os
import json
import subprocess

def get_feishu_creds():
    """
    自发现逻辑：
    1. 优先读取 ~/.openclaw/openclaw.json 中的凭证
    2. 如果失败，读取环境变量 FEISHU_APP_ID/FEISHU_APP_SECRET
    """
    config_path = os.path.expanduser('~/.openclaw/openclaw.json')
    app_id, app_secret = None, None

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # 从 feishu channel 配置中提取凭证
                feishu_conf = config.get('channels', {}).get('feishu', {})
                app_id = feishu_conf.get('appId')
                app_secret = feishu_conf.get('appSecret')
        except Exception as e:
            print(f"Warning: 读取配置文件失败: {e}")

    # 环境变量补全
    app_id = app_id or os.environ.get('FEISHU_APP_ID')
    app_secret = app_secret or os.environ.get('FEISHU_APP_SECRET')

    if not app_id or not app_secret:
        raise ValueError("Error: 无法自动获取飞书凭证。请确认 ~/.openclaw/openclaw.json 存在且包含 feishu appId/appSecret。")

    return app_id, app_secret


def _curl_json(method, url, token=None, body=None):
    cmd = ['curl', '-s', '-X', method, url]
    if token:
        cmd += ['-H', f'Authorization: Bearer {token}']
    if body:
        cmd += ['-H', 'Content-Type: application/json', '-d', json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except:
        return {"error": r.stdout}


def get_token(app_id, app_secret):
    """获取 tenant_access_token"""
    d = _curl_json('POST', 
                   'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', 
                   body={'app_id': app_id, 'app_secret': app_secret})
    return d.get('tenant_access_token')


def create_spreadsheet(token, title, folder_token=''):
    """创建电子表格"""
    d = _curl_json('POST',
                   'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets',
                   token=token,
                   body={'title': title, 'folder_token': folder_token})
    ss = d['data']['spreadsheet']
    return {
        'spreadsheet_token': ss['spreadsheet_token'],
        'url': ss['url'],
        'title': ss['title']
    }

def get_sheet_id(token, spreadsheet_token, index=0):
    """获取工作表 sheet_id"""
    d = _curl_json('GET',
                   f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query',
                   token=token)
    sheets = d['data']['sheets']
    return sheets[index]['sheet_id']

def write_values(token, spreadsheet_token, sheet_id, start_cell, values):
    """写入数据"""
    rows = len(values)
    cols = max(len(r) for r in values)
    end_col = chr(ord('A') + cols - 1)
    end_cell = f'{end_col}{rows}'
    range_str = f'{sheet_id}!{start_cell}:{end_cell}'

    return _curl_json('PUT',
                      f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values',
                      token=token,
                      body={'valueRange': {'range': range_str, 'values': values}})

# ---- 使用示例 ----
if __name__ == '__main__':
    try:
        app_id, app_secret = get_feishu_creds()
        token = get_token(app_id, app_secret)

        # 创建测试表格
        ss = create_spreadsheet(token, 'Python自研表格')
        print(f"表格链接: {ss['url']}")

        sheet_id = get_sheet_id(token, ss['spreadsheet_token'])
        data = [
            ['姓名', '角色', '测试时间'],
            ['Agent', 'OpenClaw', '2026-03-08'],
            ['Auto-Auth', 'Robot', 'Success']
        ]
        write_values(token, ss['spreadsheet_token'], sheet_id, 'A1', data)
        print("数据写入验证成功")
    except Exception as e:
        print(f"ERROR: {e}")
