---
name: feishu-permission-setup
description: |
  通过浏览器自动化为飞书自建应用申请并发布 Tenant token 权限。如果浏览器 session 已登录且未超时，全程自动完成；否则需要人工扫码一次。
  触发场景：
  - 飞书 API 返回错误码 99991672（权限不足）
  - 用户说「开通飞书权限」「申请飞书文档权限」「为什么 API 没有权限」
  - 需要给飞书应用添加新的 API scope
  前置条件：需持有飞书 App 的管理员权限，需要能使用浏览器工具。

---

# 飞书权限开通（浏览器自动化）

通过浏览器自动化操控飞书开放平台，完成权限申请与版本发布。

**优先检查 session 状态**：先查看浏览器当前 tabs。如果已有 `open.feishu.cn/app/` 页面且标题包含 Developer Console，说明登录 session 有效，**跳过扫码直接从 Step 3 开始**。只有在被重定向到登录页时才需要人工扫码。

## 核心流程

共 6 步。只有 session 过期时 Step 2 才需要人工介入，其余全自动。

---

### Step 1：从 API 报错提取所需权限

直接调用目标飞书 API。如果缺权限，响应中会明确告知：

```
错误码: 99991672
msg: 应用尚未开通所需的应用身份权限：[docx:document:create]
```

**提取方括号内的权限名**，如 `docx:document:create`。这比猜测权限名高效得多。

如果用户已经知道要开什么权限，跳过此步。

---

### Step 2：（仅 session 失效时）浏览器打开登录页 + 人工扫码

如果 Step 1 之前检查 tabs 发现已登录，**跳过此步**。

飞书开放平台强制扫码登录，无法绕过。

1. 用浏览器工具打开飞书开放平台登录页：

   ```
   https://open.feishu.cn/app/{APP_ID}/auth
   ```

   > `{APP_ID}` 替换为实际的飞书应用 ID（如 `cli_xxxx`）。如果不知道，问用户。

2. 页面会显示二维码。**截图发给用户**，请用户用飞书 App 扫码。

3. **等待用户确认扫码完成**，然后用浏览器确认页面已跳转到权限管理页（URL 应包含 `/auth`）。

> ⚠️ 这是整个流程中**唯一需要人工介入**的步骤。

---

### Step 3：在 Tenant token scopes 标签页添加权限

登录成功后，应该已经在权限管理页面。

**关键：必须在「Tenant token scopes」标签页下操作，不是 User token scopes。**

- Tenant token = 应用自身身份，后台 API 调用用这个
- User token = 代表用户身份，两者不可混用

操作步骤：

1. **关闭可能出现的说明弹窗**：查找 "Got It" 按钮并点击（如果存在）
2. **点击 "Add permission scopes to app"** 按钮
3. **确认在 "Tenant token scopes" 标签页下**（如果不是，点击切换）
4. **在搜索框中输入权限名**（如 `docx:document:create`）
5. **勾选搜索结果中的对应权限**
6. **点击 "Add Scopes"** 按钮确认

如果需要添加多个权限，重复步骤 2-6。

> 💡 也可以使用「Batch import/export scopes」一次性添加多个权限（JSON 格式）。

---

### Step 4：发布新版本使权限生效

**权限变更不会实时生效，必须发布新版本。**

1. 页面顶部应有黄色提示条，点击 **"Create Version"**
2. 填写版本号（如 `1.0.1`）和版本说明（如 `Add docx:document:create`）
3. 点击 **"Save"**
4. 点击 **"Publish"**

> ⚠️ React 输入框注意事项：如果普通 fill/type 无法输入，需用原生 setter 注入：
>
> ```javascript
> (() => {
> const iS = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
> const tS = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
> const v = document.querySelectorAll('input')[0];
> const t = document.querySelector('textarea');
> iS.call(v, '版本号');
> v.dispatchEvent(new Event('input', {bubbles: true}));
> tS.call(t, '版本说明');
> t.dispatchEvent(new Event('input', {bubbles: true}));
> })()
> ```

企业内部 App 通常无需管理员审核，Publish 后立即 Released。

---

### Step 5：验证权限

重新调用 Step 1 中失败的 API，确认不再返回 99991672 错误。

如果仍然报错：

- 确认添加的是 **Tenant token** 而非 User token 类型的权限
- 确认版本已发布成功（状态为 Released）
- 等待几秒后重试（极少数情况有短暂延迟）

---

### Step 6：告知用户结果

权限开通成功后，告知用户：

- 已添加的权限列表
- 发布的版本号
- 现在可以使用的 API 能力

---

## 常用飞书 Tenant token 权限速查

| 权限                       | 用途              |
| -------------------------- | ----------------- |
| `docx:document:create`     | 创建文档          |
| `docx:document:write_only` | 写入/编辑文档内容 |
| `docx:document:readonly`   | 读取文档内容      |
| `drive:drive`              | 云盘操作          |
| `im:message:send_as_bot`   | 机器人发送消息    |

## 注意事项

- **浏览器 session 会超时**：每次操作前先确认当前 URL，如果被踢回登录页需重新扫码
- **一个 scope 对应一种能力**：不确定需要哪些 scope 时，先调 API 让飞书告诉你
- **此流程可推广**：同样的浏览器自动化 + 人工扫码模式适用于其他 Web 控制台（云平台、SaaS 设置等）
