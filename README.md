# Zepp Health CLI

[English](#english) | [中文](#中文)

---

## English

Fetch health data from Zepp/Amazfit API, normalize it, and compute health scores.

### Features

- Full health data: steps, sleep, heart rate, stress, SpO2, body battery, readiness, HRV, respiratory rate, workouts
- Data normalization aligned with the Zepp app display values
- Independent health scoring algorithm (inspired by Athlytic)
- Multi-dimensional analysis: recovery, sleep quality, training load
- Three output formats: JSON, terminal, natural language briefing

### Installation

```bash
cd zepp-health
pip install -e .
```

### Configuration

#### Get your credentials

1. Open the Zepp privacy data page and log in:
   ```
   https://user.huami.com/privacy2/index.html?loginPlatform=web&platform_app=com.xiaomi.hm.health
   ```
2. Open browser Developer Tools (F12) → Network tab
3. Refresh the page (or click any page action)
4. Find a request to `api-mifit*.zepp.com`
5. Copy `apptoken` from request headers
6. Copy `userid` from the request URL or query parameters

> Token expires after ~30 days. When data returns null, re-extract a new token.

**Option 1: config.json**

```bash
cp config.example.json config.json
# Edit config.json with your app_token and user_id
```

**Option 2: Environment variables**

```bash
cp .env.example .env
# Edit .env
```

**Option 3: CLI arguments**

```bash
zepp-health --cookie "your_cookie_string" report
```

Priority: CLI args > cookie parsing > config.json > environment variables

### CLI Usage

```bash
# Daily health report
zepp-health report [--date YYYY-MM-DD] [--json] [-o file]

# Morning briefing (natural language, good for push notifications)
zepp-health briefing [--date YYYY-MM-DD] [--json]

# LLM analysis snapshot (includes 7-day trends)
zepp-health snapshot [--date YYYY-MM-DD] [--json]

# Raw data
zepp-health daily [--days N] [--json]      # Daily summary
zepp-health sleep [--days N] [--json]      # Sleep
zepp-health stress [--days N] [--json]     # Stress
zepp-health spo2 [--days N] [--json]       # SpO2
zepp-health readiness [--days N] [--json]  # Readiness
zepp-health workouts [--days N] [--json]   # Workouts
zepp-health hrv [--days N] [--json]        # HRV

# Config
zepp-health config         # Show current config
zepp-health config --path  # Show config file search paths
```

### Scoring Algorithm

**Recovery Score** — Based on z-score comparison of HRV and resting heart rate (RHR) against a 60-day rolling baseline. HRV weight 0.6, RHR weight 0.4. Fatigue detection: 3 consecutive days of HRV below baseline and RHR above baseline.

**Sleep Quality Score** — Multi-dimensional weighted evaluation: duration (0.25, target 7-9h), deep sleep % (0.25, target 15-20%), REM % (0.20, target 20-25%), sleep efficiency (0.15, target ≥85%), interruption penalty (0.15).

**Exertion Score** — Based on acute (7-day) / chronic (28-day) training load ratio: <0.8 detraining, 0.8-1.0 maintaining, 1.0-1.3 productive, 1.3-1.5 overreaching, >1.5 high risk.

**Overall Health Score** — Weighted: Recovery 0.35 + Sleep 0.30 + Exertion 0.15 + Stress 0.10 + SpO2 0.10.

### Data Validation

| Data Point | vs Zepp App |
|------------|-------------|
| Steps / distance / calories | Exact match |
| Sleep (deep/light/REM/wake count) | Exact match |
| Sleep score | Exact match |
| Resting heart rate | Exact match |
| Stress | Minor rounding difference |
| SpO2 | Avg differs by 1 (calculation method) |
| Body battery | Exact match (+3 offset correction) |
| Readiness | Exact match |
| HRV | Exact match |
| Skin temperature | Exact match (calibrated/100) |
| Continuous HR | API limitation, unavailable |

### Tech Stack

Python >= 3.10, httpx, pydantic v2, rich, python-dotenv

### Skill Version

For LLM-driven personalized health analysis (for OpenClaw / hermes-agent), see [zepp-health-skill](https://github.com/n0Pnyk/zepp-health-skill).

### Disclaimer

This tool is for informational purposes only and does not constitute medical advice. Consult a healthcare professional for any health concerns.

### License

[MIT License](LICENSE)

---

## 中文

通过 Zepp/Amazfit API 拉取健康数据，进行归一化处理和健康评分分析。

### 功能

- 拉取 Zepp 全量健康数据：步数、睡眠、心率、压力、血氧、身体电量、准备度、HRV、呼吸频率、运动记录
- 数据归一化处理，与 Zepp app 显示值对齐
- 基于运动科学的独立健康评分算法（参考 Athlytic 思路）
- 多维度健康分析：恢复评分、睡眠质量、训练负荷
- 三种输出格式：JSON、终端格式化、自然语言早报

### 安装

```bash
cd zepp-health
pip install -e .
```

### 配置

#### 获取认证信息

1. 打开 Zepp 隐私数据页面并登录：
   ```
   https://user.huami.com/privacy2/index.html?loginPlatform=web&platform_app=com.xiaomi.hm.health
   ```
2. 打开浏览器开发者工具（F12）→ Network 标签
3. 刷新页面（或点击页面任意操作）
4. 找到发往 `api-mifit*.zepp.com` 的请求
5. 从请求头复制 `apptoken`
6. 从请求 URL 或参数中复制 `userid`

> Token 约 30 天过期。数据返回 null 时，重新提取 token 即可。

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

### CLI 用法

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

### 评分算法

**恢复评分** — 基于 HRV 和静息心率（RHR）与 60 天滚动基线的 z-score 对比。HRV 权重 0.6，RHR 权重 0.4。疲劳信号检测：连续 3 天 HRV 低于基线且 RHR 高于基线。

**睡眠质量评分** — 多维度加权评估：时长（0.25，目标 7-9 小时）、深睡占比（0.25，目标 15-20%）、REM 占比（0.20，目标 20-25%）、睡眠效率（0.15，目标 ≥85%）、中断惩罚（0.15）。

**训练负荷评分** — 基于急性（7天）/ 慢性（28天）训练负荷比率：<0.8 训练不足，0.8-1.0 维持，1.0-1.3 有效提升，1.3-1.5 负荷偏高，>1.5 过度训练风险。

**综合健康分** — 加权组合：恢复 0.35 + 睡眠 0.30 + 训练负荷 0.15 + 压力 0.10 + 血氧 0.10。

### 数据验证

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

### 技术栈

Python >= 3.10, httpx, pydantic v2, rich, python-dotenv

### Skill 版本

如需 LLM 驱动的个性化健康分析（适合 OpenClaw / hermes-agent），请使用 [zepp-health-skill](https://github.com/n0Pnyk/zepp-health-skill)。

### 免责声明

本工具仅供健康数据参考，不构成医疗建议。如有健康问题请咨询专业医生。

### 许可证

[MIT License](LICENSE)
