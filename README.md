<div align="center">
<h1>语析 Yuxi</h1>

<p><strong>多租户 Harness + 企业知识库</strong><br/>让企业知识可被智能体检索、推理与交付</p>

[![](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=ffffff)](https://github.com/xerrors/Yuxi/blob/main/docker-compose.yml)
[![](https://img.shields.io/github/issues/xerrors/Yuxi?color=F48D73)](https://github.com/xerrors/Yuxi/issues)
[![License](https://img.shields.io/github/license/bitcookies/winrar-keygen.svg?logo=github)](https://github.com/xerrors/Yuxi/blob/main/LICENSE)
[![DeepWiki](https://img.shields.io/badge/DeepWiki-blue.svg)](https://deepwiki.com/xerrors/Yuxi)
[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/xerrors/Yuxi)
[![demo](https://img.shields.io/badge/demo-00A1D6.svg?style=flat&logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1DF14BTETq/)


<a href="https://trendshift.io/repositories/24335" target="_blank"><img src="https://trendshift.io/api/badge/repositories/24335" alt="xerrors%2FYuxi | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

[[文档]](https://xerrors.github.io/Yuxi) · [[English]](README.en.md)

</div>

![arch](https://xerrors.oss-cn-shanghai.aliyuncs.com/github/gpt-iamge-2-arch.png)


**图由 GPT-Image-2 生成*

## 简介

语析（Yuxi）是一个基于大模型的智能知识库与知识图谱智能体开发平台。它把 **RAG 检索**、**Milvus 知识库内知识图谱** 与 **LangGraph 多智能体编排** 整合进统一的多租户工作台：管理员配置知识库、模型与权限，用户在类 ChatGPT 的界面中与可挂载 Skills、MCP、子智能体和沙盒工具的智能体对话，并获得带引用来源、知识图谱推理与可交付产物的回答。

## 核心特性

- 🤖 **智能体开发** —— 基于 LangGraph 构建，支持子智能体（SubAgents）、Skills、MCP、Tools 与中间件机制；长耗时任务由后台 worker 异步执行，配套沙盒文件系统支持工具产物落盘、预览与下载。
- 📚 **知识库（RAG）** —— 多格式文档解析（MinerU / PaddleX / OCR），可配置 Embedding 与 Rerank 模型，支持知识库评估与 PDF / 图片在线预览，检索来源回填到对话引用。
- 🕸️ **知识图谱** —— 在 Milvus 知识库内构建、展示和检索实体关系图谱，并与 chunk 检索结果融合参与智能体推理。
- 🏢 **多租户与权限** —— 用户 / 部门级权限管理，模型供应商统一配置，支持 API Key 认证供外部系统集成调用。
- ⚙️ **平台与工程化** —— Vue + FastAPI 架构，开箱即用的 Docker Compose 部署，支持暗黑模式、LITE 轻量启动与生产级编排。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 · Vite · Pinia |
| 后端 | FastAPI · LangGraph · ARQ (异步 worker) |
| 存储 | PostgreSQL · Redis · MinIO · Milvus · Neo4j |
| 文档解析 | MinerU · PaddleX · RapidOCR |
| 部署 | Docker Compose |

![image-20260606190609377](https://xerrors.oss-cn-shanghai.aliyuncs.com/github/image-20260606190609377.png)

## 最新动态


<details open>
<summary>[2026/06] v0.7.0 开发中（重要不兼容变更）</summary>


</details>

### 重大变更

- **模型配置收敛**：移除旧版 v1 模型配置与 Ollama 支持，运行时统一使用 `provider_id:model_id` 与独立 provider 模块，自定义 provider 迁移到数据库
- **智能体运行时收敛**：用户可见的 `AgentConfig` 收敛为数据库持久化的一级 `Agent`，新增 `/api/agent` 管理与运行接口，前端只提交 `agent_id`
- **知识库能力收敛**：以 Yuxi 自研的 Milvus 知识库/图谱构建、展示、检索链路替换历史 LightRAG 集成，并移除 Upload 类型；知识库类型收敛为 **Milvus** 与只读连接器（**Dify**、**Notion**），减少历史集成带来的兼容性问题
- **Skill 安装与权限收敛**：以 `source_type / share_config / enabled` 表达来源、生效范围与启用状态；内置 Skill 启动自动入库并默认全局启用，上传/远程统一改为「解析草稿 → 确认安装」
- **用户身份命名收敛**：业务登录标识统一为字符串 `uid`



详见 [changelog](docs/develop-guides/changelog.md)。
<details>
<summary>[2026/04/01] v0.6.0 版本发布</summary>

详见 [changelog](docs/develop-guides/changelog.md)

</details>

<details>
<summary>[2026/03/01] v0.5.0 版本发布</summary>

详见 [changelog](docs/develop-guides/changelog.md)

</details>

<details>
<summary>[2025/12/19] v0.4.0 版本发布</summary>

详见 [changelog](docs/develop-guides/changelog.md)

</details>

<details>
<summary>[2025/11/05] v0.3.0 版本发布</summary>

详见 [changelog](docs/develop-guides/changelog.md)

</details>

## 快速开始

**前置要求**：已安装 [Docker](https://docs.docker.com/get-docker/) 与 Docker Compose，并准备至少一个兼容 OpenAI 接口的大模型 API。

**1. 克隆代码并初始化**

```bash
git clone --branch v0.7.0.beta1 --depth 1 https://github.com/xerrors/Yuxi.git
cd Yuxi

# Linux/macOS
./scripts/init.sh

# Windows PowerShell
.\scripts\init.ps1
```

**2. 使用 Docker 启动**

```bash
docker compose up --build
```

**3. 访问平台**

等待启动完成后，浏览器打开 `http://localhost:5173`，使用初始化时生成的管理员账户登录即可。

> 💡 不需要知识库 / 知识图谱等重依赖时，可使用 `make up-lite` 以 LITE 轻量模式启动，加快冷启动速度。更多部署说明见 [项目文档](https://xerrors.github.io/Yuxi)。

## 示例与演示

<table>
  <tr>
    <td align="center">
      <img src="https://xerrors.oss-cn-shanghai.aliyuncs.com/github/image-20260604203514048.png" width="100%" alt="对话工作台"/>
      <br/>
      <strong>对话工作台</strong>
    </td>
    <td align="center">
      <img src="https://xerrors.oss-cn-shanghai.aliyuncs.com/github/image-20260604203704426.png" width="100%" alt="沙盒文件系统"/>
      <br/>
      <strong>沙盒文件系统</strong>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="https://xerrors.oss-cn-shanghai.aliyuncs.com/github/image-20260604205342546.png" width="100%" alt="Agentic RAG"/>
      <br/>
      <strong>Agentic RAG</strong>
    </td>
    <td align="center">
      <img src="https://xerrors.oss-cn-shanghai.aliyuncs.com/github/image-20260604204056298.png" width="100%" alt="知识图谱"/>
      <br/>
      <strong>知识图谱</strong>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="https://xerrors.oss-cn-shanghai.aliyuncs.com/github/image-20260604210111977.png" width="100%" alt="检索评估"/>
      <br/>
      <strong>检索评估</strong>
    </td>
    <td align="center">
      <img src="https://xerrors.oss-cn-shanghai.aliyuncs.com/github/image-20260604205611168.png" width="100%" alt="多知识源接入"/>
      <br/>
      <strong>多知识源接入</strong>
    </td>
  </tr>
</table>



## 致谢

本项目参考并引用了以下优秀开源项目，在此致以诚挚的感谢：

- [LightRAG](https://github.com/HKUDS/LightRAG) - 早期版本曾参考其图谱构建与检索思路；当前 Yuxi 已实现自研 Milvus 知识库/图谱链路以替换历史集成，降低兼容性问题
- [DeepAgents](https://github.com/langchain-ai/deepagents) - 直接引入作为深度智能体框架
- [DeerFlow](https://github.com/bytedance/deer-flow) - 参考了其 Sandbox 智能体架构的实现思路
- [RAGflow](https://github.com/infiniflow/ragflow) - 参考了其文档 Text Chunking 的分块策略
- [LangGraph](https://github.com/langchain-ai/langgraph) - 多智能体编排框架，本项目的核心架构基础
- [QwenPaw](https://github.com/agentscope-ai/QwenPaw) - 参考模型配置与个人文件区域设计

## 参与贡献

感谢所有贡献者的支持！

<a href="https://github.com/xerrors/Yuxi/contributors">
  <img src="https://contrib.rocks/image?repo=xerrors/Yuxi&max=100&columns=10" />
</a>


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=xerrors/Yuxi)](https://star-history.com/#xerrors/Yuxi)

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

<div align="center">

**如果这个项目对您有帮助，请不要忘记给我们一个 ⭐️**

</div>
