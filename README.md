# Data Agent · SQL RAG Project

基于 **RAG（检索增强生成）+ Text-to-SQL** 的数据智能体项目。用户通过自然语言提问，系统结合元数据检索与大语言模型，自动生成并执行 SQL，返回数据分析结果。

---

## 一、项目简介

本项目面向数据分析场景，构建了一个「自然语言 → SQL → 数据结果」的智能问答链路：

1. **理解问题**：解析用户的自然语言查询意图。
2. **检索元数据**：从元数据库、全文索引、向量库中检索相关的表、列、指标信息。
3. **生成 SQL**：将检索到的上下文与用户问题一起交给大模型，生成可执行的 SQL。
4. **执行与返回**：在数据仓库上执行 SQL，并将结果返回给用户。

---

## 二、技术栈

| 分类 | 技术选型 |
| --- | --- |
| 语言 / 运行时 | Python >= 3.11 |
| 包管理 | [uv](https://github.com/astral-sh/uv) |
| Web 框架 | FastAPI |
| 智能体编排 | LangChain、LangGraph |
| 大语言模型 | DeepSeek（`langchain-deepseek`） |
| 关系型数据库 | MySQL 8.0（SQLAlchemy 2.x + asyncmy 异步驱动） |
| 全文检索 | Elasticsearch 8.19（IK 中文分词插件） |
| 向量数据库 | Qdrant v1.16 |
| 向量模型 | BGE-large-zh-v1.5（通过 HuggingFace TEI 部署） |
| 中文分词 | jieba |
| 配置管理 | OmegaConf + PyYAML |
| 日志 | Loguru |
| 容器化 | Docker / Docker Compose |

---

## 三、目录结构

```
data-agent 根目录
├── app/                        # 代码目录
│   ├── agent/                  # 智能体：LangGraph 工作流编排
│   ├── api/                    # 接口层：FastAPI 路由
│   ├── clients/                # 数据库客户端：MySQL / ES / Qdrant / Embedding 连接封装
│   ├── conf/                   # 配置类：配置加载与解析
│   ├── core/                   # 基础设施：通用能力、异常、日志等
│   ├── models/                 # 数据库实体类：ORM 模型定义
│   ├── prompt/                 # 提示词工具：Prompt 模板与加载逻辑
│   ├── repositories/           # Repo 层：负责数据库底层查询
│   ├── scripts/                # 脚本：数据初始化、索引构建等
│   └── services/               # Service 层：负责具体的业务逻辑
├── conf/                       # 配置文件（YAML 等）
├── docker/                     # 开发环境
│   ├── elasticsearch/          # ES 镜像构建（含 IK 分词插件）
│   ├── embedding/              # BGE-large-zh-v1.5 向量模型
│   ├── mysql/                  # MySQL 初始化脚本（dw.sql / meta.sql）
│   └── docker-compose.yaml     # 一键编排所有依赖服务
├── logs/                       # 日志目录
├── prompts/                    # 提示词目录
├── pyproject.toml              # 项目依赖与构建配置
└── README.md
```

### 分层说明

- **api**：对外 HTTP 接口，只负责请求解析与响应封装。
- **services**：核心业务逻辑编排，衔接智能体、检索与数据访问。
- **repositories**：数据库底层查询，屏蔽 SQL / ORM 细节。
- **clients**：各类外部数据源（MySQL、Elasticsearch、Qdrant、Embedding 服务）的连接客户端。
- **agent**：基于 LangGraph 的智能体流程，负责问题理解、检索、SQL 生成与校验。
- **models**：数据库实体（ORM）映射。
- **prompt / prompts**：提示词模板的管理与加载。

---

## 四、快速开始

### 1. 环境要求

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv)
- Docker & Docker Compose

### 2. 启动依赖服务

在项目根目录执行：

```bash
docker compose -f docker/docker-compose.yaml up -d
```

启动后将提供以下服务：

| 服务 | 说明 | 端口 |
| --- | --- | --- |
| MySQL | 关系型数据库（`dw` 数据仓库 + `meta` 元数据库） | `3306` |
| Elasticsearch | 全文检索（内置 IK 中文分词） | `9200` |
| Kibana | ES 可视化控制台 | `5601` |
| Qdrant | 向量数据库（HTTP `6333` / gRPC `6334`） | `6333`、`6334` |
| Embedding | BGE-large-zh-v1.5 向量服务（TEI） | `8081` |

> MySQL 默认账号：`atguigu` / `Atguigu.123`，root 密码：`Atguigu.123`。
> 首次启动时，`docker/mysql` 下的 `dw.sql`、`meta.sql` 会自动执行完成建库建表与初始数据导入。

### 3. 安装 Python 依赖

```bash
uv sync
```

### 4. 运行项目

```bash
uv run sql-rag-project
```

---

## 五、数据模型

项目包含两个数据库：

### 1. `dw` — 数据仓库（业务数据）

采用维度建模（星型模型），包含以下表：

| 表名 | 类型 | 说明 |
| --- | --- | --- |
| `fact_order` | 事实表 | 订单事实：订单编号、客户、商品、日期、地区、数量、金额 |
| `dim_region` | 维度表 | 地区维度：省份、区域、国家 |
| `dim_customer` | 维度表 | 客户维度：姓名、性别、会员等级 |
| `dim_product` | 维度表 | 商品维度：名称、品类、品牌 |
| `dim_date` | 维度表 | 日期维度：年、季度、月、日 |

### 2. `meta` — 元数据库（供 RAG 检索）

用于描述数据仓库的结构，为 Text-to-SQL 提供上下文：

| 表名 | 说明 |
| --- | --- |
| `table_info` | 表信息：表编号、名称、类型（fact/dim）、描述 |
| `column_info` | 列信息：列名、数据类型、角色（主键/外键/度量/维度）、示例、别名、所属表 |
| `metric_info` | 指标信息：指标编码、名称、描述、关联列、别名 |
| `column_metric` | 列与指标的关联关系 |

---

## 六、配置说明

- 应用配置位于 `conf/` 目录（YAML 格式），通过 OmegaConf 加载。
- 提示词模板位于 `prompts/` 目录。
- 运行日志输出至 `logs/` 目录。

---

## 七、核心链路示意

```
用户自然语言提问
      │
      ▼
 [agent] 意图理解
      │
      ▼
 检索元数据 ──► Elasticsearch（全文/IK 分词）
      │     └─► Qdrant（BGE 向量语义检索）
      │     └─► MySQL meta（结构化元数据）
      ▼
 [prompt] 组装上下文
      │
      ▼
 DeepSeek 生成 SQL
      │
      ▼
 [repositories] 在 dw 数据仓库执行 SQL
      │
      ▼
 返回数据分析结果
```
