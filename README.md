# ExpForge

> 将工作经验系统性地内化为可复用的工作流（SOP）和结构化知识库。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 核心理念

工作中的很多能力都藏在“做过的项目”和“踩过的坑”里。**ExpForge** 提供了一条从“零散经验”到“可复用资产”的渐进式路径：

```
原始经验 (experiences/)
    ↓ 复盘与提炼
工作流 / SOP (workflows/)
    ↓ 抽象与系统化
知识库 (knowledge/)
    ↓ 关联与检索
持续复用与升级
```

## 快速开始

### 安装与使用

无需安装，仅需 Python 3.7+：

```bash
git clone https://github.com/<your-username>/expforge.git
cd expforge

# 1. 记录一次经验
python expforge.py capture

# 2. 从经验提炼工作流
python expforge.py distill <经验文件名>

# 3. 将概念/方法录入知识库
python expforge.py know

# 4. 建立关联
python expforge.py link

# 5. 搜索与统计
python expforge.py search <关键词>
python expforge.py list
python expforge.py stats
```

## MCP Server - 让 Agent 直接调用你的知识库

ExpForge 提供了两个版本的 **MCP (Model Context Protocol) Server**，你可以选择任意一种接入支持 MCP 的 Agent（如 Claude Desktop、Cursor、Kimi 等）：

| 版本 | 文件 | 特点 |
|------|------|------|
| **Python** | `mcp_server.py` | 零外部依赖，Python 3.7+ 即可运行 |
| **TypeScript** | `ts/mcp-server.ts` → `dist/mcp-server.js` | 基于官方 MCP SDK，Node.js 18+ |

两者暴露的 **Tools** 和 **Resources** 完全一致。

### 暴露的能力

| Tool | 说明 |
|------|------|
| `search_items` | 按关键词搜索经验 / 工作流 / 知识 |
| `get_item` | 读取某个 Markdown 文件的完整内容 |
| `list_items` | 列出所有条目 |
| `capture_experience` | 创建新经验记录 |
| `add_knowledge` | 添加知识条目 |
| `distill_workflow` | 从经验提炼工作流 |
| `link_items` | 建立经验与工作流/知识的关联 |

同时支持 **Resources**，Agent 可以直接通过 `expforge://workflows/<filename>` 这类 URI 读取文件。

### 配置示例

#### Python 版本

**Claude Desktop** (`%APPDATA%\Claude\settings.json`):
```json
{
  "mcpServers": {
    "expforge": {
      "command": "python",
      "args": [
        "/path/to/expforge/mcp_server.py"
      ]
    }
  }
}
```

#### TypeScript 版本

先安装依赖并构建：
```bash
cd expforge
npm install
npm run build
```

**Claude Desktop**:
```json
{
  "mcpServers": {
    "expforge": {
      "command": "node",
      "args": [
        "/path/to/expforge/dist/mcp-server.js"
      ]
    }
  }
}
```

开发时可直接用 `tsx` 热运行（无需手动 build）：
```bash
npm run dev
```

#### Cursor

Python:
```json
{
  "mcpServers": {
    "expforge": {
      "command": "python",
      "args": [
        "/path/to/expforge/mcp_server.py"
      ]
    }
  }
}
```

TypeScript:
```json
{
  "mcpServers": {
    "expforge": {
      "command": "node",
      "args": [
        "/path/to/expforge/dist/mcp-server.js"
      ]
    }
  }
}
```

#### 其他支持 stdio MCP 的客户端

参考 `mcp_config.example.json` 中的通用配置。

### 在 Agent 中的使用示例

一旦配置完成，你可以直接对 Agent 说：

> "请搜索我的知识库中关于 API 超时的内容，并按其中的 SOP 帮我诊断这个问题。"

Agent 会自动调用 `search_items` → `get_item` → 按工作流步骤给出方案。

你也可以让 Agent 主动记录：

> "我刚才排查了一个 Redis 缓存穿透问题，请帮我把这次经验记录到 ExpForge 中。"

Agent 会调用 `capture_experience` 工具，按模板生成 Markdown 文件到你的 `experiences/` 目录。

## 目录结构

```
expforge/
├── expforge.py           # CLI 入口
├── mcp_server.py         # MCP Server（stdio，Python 3.7+）
├── ts/
│   └── mcp-server.ts     # MCP Server（TypeScript）
├── dist/                 # TS 编译输出（npm run build 生成）
├── package.json
├── tsconfig.json
├── mcp_config.example.json
├── README.md
├── LICENSE
├── .gitignore
├── experiences/          # 原始经验记录（Markdown）
├── workflows/            # 提炼出的工作流 / SOP
├── knowledge/            # 结构化知识条目
└── templates/            # Markdown 模板（可自定义）
```

## 设计原则

- **纯文件系统**：无数据库、无服务端依赖，所有内容均为 Markdown
- **渐进式沉淀**：经验可以先粗糙记录，后续再逐步提炼为工作流和知识
- **模板驱动**：修改 `templates/` 下的文件即可定制记录格式
- **MCP 原生**：知识库可直接被外部 Agent 读取、搜索、甚至自动更新
- **可版本控制**：整个目录可放入 Git，追踪个人或团队的知识演化

## 工作流程示例

### 记录一次排查经历

```bash
$ python expforge.py capture
经验标题: 排查线上 API 超时问题
分类: engineering
标签（逗号分隔）: troubleshooting,api,performance
...
```

生成的 `experiences/20260417-pai-cha-xian-shang-api-chao-shi-wen-ti.md`：

```markdown
---
title: "排查线上 API 超时问题"
date: 2026-04-17 01:25
tags: [troubleshooting, api, performance]
status: raw
category: engineering
---

# 背景
...
# 过程
...
# 结果
...
# 反思
...
# 关联
- workflows:
- knowledge:
```

### 提炼为标准工作流

```bash
$ python expforge.py distill 20260417-pai-cha-xian-shang-api-chao-shi-wen-ti.md
工作流标题: API 超时排查 SOP
...
```

生成的 `workflows/20260417-api-chao-shi-pai-cha-sop.md` 将包含：
- 适用场景
- 前置条件
- 执行步骤
- 检查清单
- 常见问题

## 自定义模板

你可以直接编辑 `templates/` 下的 `.md` 文件，增加或删除字段。支持的占位符例如：

- `{{title}}`、`{{date}}`、`{{tags}}`、`{{category}}`
- `{{context}}`、`{{process}}`、`{{result}}`、`{{reflection}}`
- `{{scenario}}`、`{{prerequisites}}`、`{{steps}}`、`{{faq}}`
- `{{concept}}`、`{{detail}}`、`{{examples}}`、`{{references}}`

## 许可证

MIT License © 2026 ExpForge Contributors
