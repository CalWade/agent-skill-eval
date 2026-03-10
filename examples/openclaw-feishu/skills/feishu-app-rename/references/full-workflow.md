# 端到端操作脚本

`feishu-app-rename` 技能的完整伪代码流程。

```bash
APP_ID="cli_xxxxxxxxxxxxxxxx"
NEW_NAME="新的应用名称"
VERSION="1.x.x"

# Step 1: 打开登录页，登录后自动跳转到应用基本信息页
browser open "https://accounts.feishu.cn/accounts/page/login?app_id=7&redirect_uri=https://open.feishu.cn/app/${APP_ID}/baseinfo"

# Step 2: 截图二维码，发送给管理员，等待扫码
browser screenshot /tmp/qr.png
# → 通过飞书消息 API 将 /tmp/qr.png 发送给管理员
# → 等待管理员用手机飞书扫码（浏览器自动跳转）

# Step 3: 确认登录成功
browser get url
# 预期结果: https://open.feishu.cn/app/${APP_ID}/baseinfo

# Step 4: 枚举所有 input，确认名称字段序号
browser eval "
  const inputs = Array.from(document.querySelectorAll('input'));
  inputs.map((el, i) => i + ': value=' + el.value + ' / placeholder=' + el.placeholder.substring(0,30))
"

# Step 5: 注入新名称（根据上一步确认 input 序号，通常为 1）
browser eval "
  const input = document.querySelectorAll('input')[1];
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, '${NEW_NAME}');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
"

# Step 6: 保存
browser eval "
  const btns = Array.from(document.querySelectorAll('button'));
  btns.find(b => b.textContent.trim() === 'Save')?.click();
"
# 等待黄色提示条: "The changes will take effect after the current version is published."

# Step 7: 创建新版本
browser eval "
  const btns = Array.from(document.querySelectorAll('button'));
  btns.find(b => b.textContent.trim() === 'Create Version')?.click();
"

# Step 8: 填写版本号和更新说明
browser eval "
  (() => {
    const vInput = document.querySelectorAll('input')[0];
    const textarea = document.querySelector('textarea');
    const iS = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const tS = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    iS.call(vInput, '${VERSION}');
    vInput.dispatchEvent(new Event('input', {bubbles: true}));
    tS.call(textarea, '更新应用名称为 ${NEW_NAME}');
    textarea.dispatchEvent(new Event('input', {bubbles: true}));
  })()
"

# Step 9: 保存版本（button[6] 为版本对话框中的 Save 按钮）
browser eval "document.querySelectorAll('button')[6].click()"

# Step 10: 发布
browser eval "
  const btns = Array.from(document.querySelectorAll('button'));
  btns.find(b => b.textContent.trim() === 'Publish')?.click();
"

# Step 11: 截图确认结果
browser screenshot /tmp/result.png
# 预期: 绿色提示 "The current changes have been published"，版本状态 = "Released"
```
