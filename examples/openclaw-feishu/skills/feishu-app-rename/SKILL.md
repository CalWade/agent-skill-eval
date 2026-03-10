---
name: feishu-app-rename
description: 通过浏览器自动化给飞书自建应用改名。Use when user asks to rename a Feishu/Lark app, change bot display name, update app name in Feishu Open Platform, or modify bot name. 飞书开放平台不提供改名 API，需通过 Web 控制台操作。改名后自动创建并发布新版本使变更生效。
---

# feishu-app-rename

通过浏览器自动化修改飞书自建应用的名称。飞书开放平台不提供改名 API，所有操作必须通过 Web 控制台完成。

**自动化逻辑：** 优先检查当前浏览器 Session 是否有效。如果已登录，全程自动完成；如果未登录，则截图二维码并发给管理员扫码。

## 前提条件

- **飞书 App ID**：优先从系统配置（如 `openclaw.json`）中自动获取，无需用户提供。
- **应用名称**：用户提供的新名称。
- **权限**：若未登录，应用 Owner 或管理员需扫码登录一次。

## 操作流程

### Step 1 — 确认环境并访问

1. 获取当前机器人的 `APP_ID`（从配置中读取）。
2. 使用浏览器访问应用基本信息页：
   ```
   https://open.feishu.cn/app/{APP_ID}/baseinfo
   ```
3. **关键判断**：检查当前 URL 和页面元素。
   - 若重定向至 `accounts.feishu.cn`（登录页）：执行 **Step 2 (扫码)**。
   - 若直接进入 `open.feishu.cn/app/.../baseinfo`：跳过扫码，直接执行 **Step 3 (改名)**。

### Step 2 — 扫码登录（仅在未登录时执行）

1. 截图页面二维码。
2. 发送截图给用户，说明需要扫码登录。
3. 轮询页面状态，等待跳转至应用基本信息页。

### Step 3 — 修改应用名称

名称输入框位于「多语言应用详情」区域，由于存在内部滚动和 React 状态同步，使用以下 JS 注入方式：

```js
(() => {
  // 找到名称输入框（通常是多语言区域的第一个或指定语言的 input）
  const input = document.querySelector('input[placeholder*="Name"]') || document.querySelectorAll('input')[1]; 
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, '新的应用名称');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  
  // 点击保存
  const btns = Array.from(document.querySelectorAll('button'));
  btns.find(b => b.textContent.trim() === 'Save')?.click();
})()
```

### Step 4 — 创建版本并发布

名称变更需发布新版本生效：

1. **点击创建版本**：
   ```js
   const btns = Array.from(document.querySelectorAll('button'));
   btns.find(b => b.textContent.trim() === 'Create Version')?.click();
   ```
2. **填写版本信息并提交**：
   - 自动递增版本号（例如从 1.0.2 变为 1.0.3）。
   - 填写更新说明：`Update app name`。
   - 点击 **Publish/Submit**。
3. **确认发布成功**：
   - 检查是否有“Released”状态或绿色成功提示。

## 常见问题

- **App ID 哪里找？** 自动从 `openclaw.json` 的 `channels.feishu.appId` 中提取。
- **多语言处理**：如果应用开启了多语言，需要对每个语言对应的 input 执行修改逻辑。
