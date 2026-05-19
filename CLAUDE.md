# Zepp Health 数据分析项目

通过 Zepp/Amazfit API 拉取健康数据，进行归一化处理和健康评分分析。

## 技术栈

- Python >= 3.10
- httpx — HTTP 客户端
- pydantic v2 — 数据模型和验证
- rich — 终端格式化输出
- python-dotenv — 环境变量管理

## 目录结构

- `zepp_health/` — 主包
  - `config.py` — 配置加载 + cookie 解析
  - `client.py` — API 客户端
  - `models.py` — Pydantic 数据模型
  - `scoring.py` — 健康评分算法
  - `analysis.py` — 分析流水线
  - `report.py` — 输出格式化
  - `cli.py` — CLI 入口
- `preference/` — 参考项目（只读，不修改）

## 命名约定

- 模块内函数用 snake_case
- 类用 PascalCase
- 常量用 UPPER_SNAKE_CASE
- 注释用中文

## API 认证

从 cookie 字符串解析 apptoken/userid，中国区默认 host: api-mifit-cn3.zepp.com

## 评分算法

参考 Athlytic app，基于 HRV/RHR 的 60 天滚动基线对比做恢复评分。
