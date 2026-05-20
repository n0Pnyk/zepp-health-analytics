# Zepp Health Analytics

Zepp/Amazfit 可穿戴设备的开源健康评分引擎。通过逆向工程 API 获取数据，使用循证算法计算评分。

## Tech Stack

- Python >= 3.10
- httpx — HTTP client
- pydantic v2 — Data models and validation
- rich — Terminal formatting
- python-dotenv — Environment variable management

## Directory Structure

- `zepp_health/` — 核心包
  - `config.py` — 配置加载 + cookie 解析
  - `client.py` — API 客户端
  - `models.py` — Pydantic 数据模型
  - `scoring.py` — 评分算法（恢复、睡眠、训练负荷）
  - `analysis.py` — 分析流水线（数据拉取 + 评分编排）
  - `report.py` — 输出格式化
  - `cli.py` — CLI 入口
- `scripts/` — 辅助脚本
- `references/` — 分析参考文档
- `preference/` — 参考项目（只读）

## 关联仓库

- GitHub CLI 仓库：`n0Pnyk/zepp-health-analytics`
- GitHub Skill 仓库：`n0Pnyk/zepp-health-skill`
- Skill 本地目录：`~/.hermes/skills/smart-home/zepp-health/`
- Skill 临时目录：`/tmp/zepp-health-skill/`

修改 `scoring.py`、`analysis.py`、`models.py` 后必须同步到 skill 仓库和 hermes 目录。

## Naming Conventions

- Functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- 注释用中文

## API Authentication

Parse apptoken/userid from cookie string. China region default host: api-mifit-cn3.zepp.com

## Scoring Algorithm

- **Recovery**: 7-day HRV/RHR average vs 60-day personal baseline, z-score mapped to 0-100
- **Sleep Quality**: 7 dimensions (duration, deep%, REM%, efficiency, interruption, onset latency, consistency)
- **Exertion**: Heart Rate Reserve method, personalized max HR from 28-day workouts, WHO targets (150-300 min/week)
- **Overall**: Recovery 0.35 + Sleep 0.30 + Exertion 0.15 + Stress 0.10 + SpO2 0.10

详细算法和参考文献见 README.md。

## Hermes Skill 目录

`~/.hermes/skills/smart-home/zepp-health/` 的 SKILL.md 有本地补充内容（配置说明、故障排查、首次安装指引等），同步时不要盲目覆盖，用 diff 对比后再决定。
