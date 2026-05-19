# Zepp Health CLI

通过 Zepp/Amazfit API 拉取健康数据，进行归一化处理和健康评分分析。

## 功能

- 拉取 Zepp 全量健康数据：步数、睡眠、心率、压力、血氧、身体电量、准备度、HRV、呼吸频率、运动记录
- 数据归一化处理，与 Zepp app 显示值对齐
- 基于运动科学的独立健康评分算法（参考 Athlytic 思路）
- 多维度健康分析：恢复评分、睡眠质量、训练负荷
- 三种输出格式：JSON、终端格式化、自然语言早报

## 安装

```bash
cd zepp-health
pip install -e .
```

## 配置

从 Zepp 网页端（app.zepp.com）登录后，从浏览器开发者工具复制 Cookie 字符串。

**方式一：config.json**

```bash
cp config.example.json config.json
# 编辑 config.json，填入 app_token、user_id
```

**方式二：环境变量**

```bash
cp .env.example .env
# 编辑 .env
```

**方式三：CLI 参数**

```bash
zepp-health --cookie "your_cookie_string" report
```

配置优先级：CLI 参数 > cookie 解析 > config.json > 环境变量

## CLI 用法

```bash
# 每日健康报告
zepp-health report [--date YYYY-MM-DD] [--json] [-o file]

# 健康早报（自然语言，适合推送）
zepp-health briefing [--date YYYY-MM-DD] [--json]

# LLM 分析用数据快照（含 7 天趋势）
zepp-health snapshot [--date YYYY-MM-DD] [--json]

# 原始数据查看
zepp-health daily [--days N] [--json]      # 每日汇总
zepp-health sleep [--days N] [--json]      # 睡眠
zepp-health stress [--days N] [--json]     # 压力
zepp-health spo2 [--days N] [--json]       # 血氧
zepp-health readiness [--days N] [--json]  # 准备度
zepp-health workouts [--days N] [--json]   # 运动
zepp-health hrv [--days N] [--json]        # HRV

# 配置
zepp-health config         # 显示当前配置
zepp-health config --path  # 显示配置文件搜索路径
```

## 评分算法

### 恢复评分（Recovery）

基于 HRV 和静息心率（RHR）与 60 天滚动基线的 z-score 对比。

- HRV 权重 0.6：高于基线 = 恢复好
- RHR 权重 0.4：低于基线 = 恢复好
- 疲劳信号检测：连续 3 天 HRV 低于基线且 RHR 高于基线
- 趋势分析：7 天线性回归斜率

### 睡眠质量评分（Sleep Quality）

多维度加权评估：

| 维度 | 权重 | 目标 |
|------|------|------|
| 时长 | 0.25 | 7-9 小时 |
| 深睡占比 | 0.25 | 15-20% |
| REM 占比 | 0.20 | 20-25% |
| 睡眠效率 | 0.15 | ≥85% |
| 中断惩罚 | 0.15 | 醒来次数+清醒时长 |

### 训练负荷评分（Exertion）

基于急性（7天）/ 慢性（28天）训练负荷比率：

| 区间 | 比率 | 含义 |
|------|------|------|
| detraining | <0.8 | 训练不足 |
| maintaining | 0.8-1.0 | 维持状态 |
| productive | 1.0-1.3 | 有效提升 |
| overreaching | 1.3-1.5 | 负荷偏高 |
| high_risk | >1.5 | 过度训练风险 |

### 综合健康分

加权组合：恢复 0.35 + 睡眠 0.30 + 训练负荷 0.15 + 压力 0.10 + 血氧 0.10

## 数据验证状态

| 数据项 | 与 app 对比 |
|--------|------------|
| 步数/距离/卡路里 | 完全一致 |
| 睡眠（深睡/浅睡/REM/醒来次数） | 完全一致 |
| 睡眠评分 | 完全一致 |
| 静息心率 | 完全一致 |
| 压力 | 个位数偏差（取整方式不同） |
| 血氧 | 平均值差 1（计算方式不同） |
| 身体电量 | 完全一致（+3 偏移修正） |
| 准备度 | 完全一致 |
| HRV | 完全一致 |
| 皮肤温度 | 完全一致（calibrated/100） |
| 连续心率 | API 限制，不可用 |

## 技术栈

- Python >= 3.10
- httpx — HTTP 客户端
- pydantic v2 — 数据模型和验证
- rich — 终端格式化输出
- python-dotenv — 环境变量管理

## Skill 版本

如需 LLM 驱动的个性化健康分析（适合 OpenClaw / hermes-agent），请使用 [zepp-health-skill](https://github.com/n0Pnyk/zepp-health-skill)。

## 免责声明

本工具仅供健康数据参考，不构成医疗建议。如有健康问题请咨询专业医生。

## 许可证

[MIT License](LICENSE)
