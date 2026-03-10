# Block 类型速查

飞书文档 Block 结构参考，用于 `write_blocks` 时构造 children 数组。

## 文本 / 标题（block_type=2）

```json
{
  "block_type": 2,
  "text": {
    "elements": [{"text_run": {"content": "标题文字"}}],
    "style": {"headingLevel": 1}
  }
}
```

- `headingLevel`：1=一级标题，2=二级标题，3=三级标题，不填=正文

## 有序列表（block_type=3）

```json
{
  "block_type": 3,
  "text": {
    "elements": [{"text_run": {"content": "列表项"}}]
  }
}
```

## 无序列表（block_type=4）

```json
{
  "block_type": 4,
  "text": {
    "elements": [{"text_run": {"content": "列表项"}}]
  }
}
```

## 代码块（block_type=14）

```json
{
  "block_type": 14,
  "code": {
    "elements": [{"text_run": {"content": "print('hello')"}}],
    "style": {"language": 2}
  }
}
```

语言编号：1=Go，2=Python，3=Shell，4=JavaScript，5=TypeScript，9=JSON

## 完整示例（标题 + 正文 + 代码块）

```json
[
  {
    "block_type": 2,
    "text": {
      "elements": [{"text_run": {"content": "一、介绍"}}],
      "style": {"headingLevel": 1}
    }
  },
  {
    "block_type": 2,
    "text": {
      "elements": [{"text_run": {"content": "这是一段正文内容。"}}]
    }
  },
  {
    "block_type": 14,
    "code": {
      "elements": [{"text_run": {"content": "echo 'Hello World'"}}],
      "style": {"language": 3}
    }
  }
]
```
