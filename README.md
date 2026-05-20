# Zepp Health

[English](#english) | [中文](#中文)

---

## English

Open-source health scoring engine for Zepp/Amazfit wearables. Fetches health data via reverse-engineered API, computes personalized scores using evidence-based algorithms, and outputs structured reports.

### Features

- **Recovery scoring** — z-score comparison of 7-day HRV/RHR average against 60-day personal baseline
- **Sleep quality** — 7-dimension scoring including sleep onset latency (PSQI standard) and schedule consistency (circular std dev)
- **Training load** — Heart Rate Reserve method with personalized max HR from workout data, WHO-based targets
- **Cross-metric analysis** — HRV + stress + SpO2 + sleep + training correlation
- **Data export** — full JSON with all raw metrics and 7-day trends
- **Structured snapshot** — LLM-ready output for AI-powered health insights

### Installation

```bash
git clone https://github.com/n0Pnyk/zepp-health.git
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

All scores are computed from raw API data using transparent, auditable formulas. No black boxes.

#### Recovery Score (0-100)

Compares your **7-day HRV/RHR average** against your **60-day personal baseline** using z-scores.

```
z = (7d_avg - 60d_mean) / 60d_std
score = 50 + (z / 3) × 50, clamped to [0, 100]
```

- HRV weight: 0.6 (higher is better)
- RHR weight: 0.4 (lower is better, z-score inverted)
- Fatigue signal: triggered when HRV < baseline AND RHR > baseline for 3 consecutive days
- Fallback: if insufficient history, uses Zepp's built-in readiness score

**Why 7-day average?** Single-day values are noisy (alcohol, poor sleep, stress). The 7-day rolling average filters out daily fluctuations and reflects your true recovery trend. This approach is used by Garmin HRV Status, AI Endurance, and HRV4Training (Altini, 2013).

#### Sleep Quality Score (0-100)

Seven dimensions, weighted:

| Dimension | Weight | Target | Source |
|---|---|---|---|
| Duration | 0.20 | 7-9 hours (age-adjusted) | NSF guidelines |
| Deep sleep % | 0.20 | 15-20% | Berry et al., 2024 |
| REM sleep % | 0.15 | 20-25% | Berry et al., 2024 |
| Sleep efficiency | 0.12 | ≥ 85% | PSQI standard |
| Interruption penalty | 0.12 | wake_count × 12 + wake_minutes × 1.5 | |
| **Onset latency** | 0.11 | 10-20 min normal, >30 min penalty | DIAMOND measures, 2024 |
| **Schedule consistency** | 0.10 | Circular std dev of sleep/wake times | SRI concept, Fischer et al., 2024 |

Onset latency scoring (clinical threshold):
- ≤ 20 min: 100 (normal)
- 20-30 min: gradual penalty
- \> 30 min: steep penalty (possible insomnia indicator)

Consistency scoring uses circular standard deviation of 7-day sleep start and wake times, mapped to 0-100 (lower std = higher score).

#### Exertion Score (0-100)

Uses the **Heart Rate Reserve (HRR)** method instead of the Acute:Chronic Workload Ratio (ACWR).

ACWR was widely used in sports science but has been criticized for lack of predictive power. Studies showed that when data is treated continuously (not bucketed), the ACWR-injury relationship disappears (Impellizzeri et al., 2019; Wang et al., 2020). The original authors also expressed regret at using "predicts" in their paper (Hulin & Gabbett, 2018).

Our approach:

```
max_hr = max(your 28-day workout heart rates), fallback to 220 - age
HRR = max_hr - resting_hr
threshold = resting_hr + HRR × 0.45
```

Score is based on weekly minutes above threshold vs WHO recommended range (150-300 min/week of moderate-to-vigorous activity):

| Zone | Minutes/week | Score |
|---|---|---|
| Inactive | 0 | 0 |
| Detraining | < 75 | 0-30 |
| Low | 75-150 | 30-50 |
| Productive | 150-300 | 50-80 |
| Overreaching | 300-450 | 80-95 |
| High risk | > 450 | 95-100 |

Target exertion zone is adaptive — recommended range adjusts based on your recovery score.

#### Overall Score (0-100)

Weighted composite: Recovery 0.35 + Sleep 0.30 + Exertion 0.15 + Stress 0.10 + SpO2 0.10. Weights are redistributed proportionally when data is missing.

### Data Validation

| Data Point | vs Zepp App |
|---|---|
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

### References

#### HRV Recovery and Baseline

- Altini, M. (2013). Heart Rate Variability (HRV) for guided training. HRV4Training.
- Plews, D. J., Laursen, P. B., et al. (2013). Training adaptation and HRV in elite endurance athletes. *Sports Medicine*, 43(7), 539-552.
- Nuuttila, O.-P., et al. (2022). Reliability and sensitivity of nocturnal HR and HRV in monitoring individual responses to training load. *Int J Sports Physiol Perform*, 17(8), 1296.
- Nature Scientific Reports (2025). Individual training prescribed by HRV, HR and well-being scores in experienced cyclists. *Sci Rep*, 15, 13540.
- Frontiers in Sports and Active Living (2025). Mapping HRV in sports science: from monitoring to machine learning.
- Terra Research (2025). Descriptive HRV using z-scores: analysis of 100,000 HRV records.
- ScienceDirect (2025). Interpreting wearable-derived HRV, sleep, and workload in recovery capacity.

#### Training Load (ACWR Criticism)

- Hulin, B. T., & Gabbett, T. J. (2018). Indeed association does not equal prediction. *Br J Sports Med*, 53(3), 144.
- Impellizzeri, F. M., et al. (2019). Acute to chronic workload ratio: is there scientific evidence? *Br J Sports Med*.
- Wang, C., et al. (2020). Acute:chronic workload ratio and injury risk in sports: a systematic review. *Sports Medicine*.
- MDPI Applied Sciences (2024). A systematic review on utilizing the acute to chronic workload ratio.

#### Sleep Quality and Consistency

- Fischer, D., et al. (2024). Sleep regularity index as an emerging digital measure. DIAMOND / DATAcc.
- MIT Media Lab / BHI'25 (2025). Associations between circadian sleep alignment, sleep regularity, and well-being: evidence from wearable data.
- MIT M.Eng. Thesis (2024). Predicting changes in individual wellbeing scores using sleep data from wearables.
- Frontiers in Pain Research (2025). Comparing self-reported sleep quality and wearable-derived sleep metrics.
- Sleep Advances / Oxford (2025). Performance validation of six commercial wrist-worn wearable sleep trackers.
- PSQI: Buysse, D. J., et al. (1989). The Pittsburgh Sleep Quality Index. *Psychiatry Research*, 28(2), 193-213.

#### Open Source Algorithms

- Open Wearables (2025). Open-source health scoring algorithms for wearable data. MIT License. github.com/the-momentum/open-wearables
- AI Endurance (2022-2025). Personalized HRV recovery model. aiendurance.com

### Tech Stack

Python >= 3.10, httpx, pydantic v2, rich, python-dotenv

### Disclaimer

This tool is for informational purposes only and does not constitute medical advice. Consult a healthcare professional for any health concerns.

### License

[MIT License](LICENSE)

---

## 中文

Zepp/Amazfit 可穿戴设备的开源健康评分引擎。通过逆向工程 API 获取健康数据，使用循证算法计算个性化评分，输出结构化报告。

### 功能特性

- **恢复评分** — 7 天 HRV/RHR 均值 vs 60 天个人基线的 z-score 对比
- **睡眠质量** — 七维评分，包含入睡潜伏期（PSQI 标准）和作息一致性（圆形标准差）
- **训练负荷** — 心率储备法，从运动数据推导个性化最大心率，基于 WHO 推荐范围
- **交叉分析** — HRV + 压力 + 血氧 + 睡眠 + 运动多维关联
- **数据导出** — 完整 JSON，包含所有原始指标和 7 天趋势
- **结构化快照** — LLM 可消费的数据格式，支持 AI 健康分析

### 安装

```bash
git clone https://github.com/n0Pnyk/zepp-health.git
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

所有评分均基于原始 API 数据，使用透明、可审计的公式计算。

#### 恢复评分（0-100）

将你的 **7 天 HRV/RHR 均值** 与 **60 天个人基线** 进行 z-score 对比。

```
z = (7天均值 - 60天均值) / 60天标准差
score = 50 + (z / 3) × 50，限制在 [0, 100]
```

- HRV 权重：0.6（越高越好）
- RHR 权重：0.4（越低越好，z-score 取反）
- 疲劳信号：连续 3 天 HRV 低于基线且 RHR 高于基线时触发
- 兜底：历史数据不足时使用 Zepp 内置 readiness 评分

**为什么用 7 天均值？** 单天值受酒精、睡眠差、压力等因素干扰。7 天滚动均值滤除日间波动，反映真实恢复趋势。Garmin HRV Status、AI Endurance、HRV4Training 均采用此方法。

#### 睡眠质量评分（0-100）

七个维度加权：

| 维度 | 权重 | 目标 | 来源 |
|---|---|---|---|
| 时长 | 0.20 | 7-9 小时（按年龄调整） | NSF 指南 |
| 深睡占比 | 0.20 | 15-20% | Berry et al., 2024 |
| REM 占比 | 0.15 | 20-25% | Berry et al., 2024 |
| 睡眠效率 | 0.12 | ≥ 85% | PSQI 标准 |
| 中断惩罚 | 0.12 | 醒来次数 × 12 + 醒来分钟 × 1.5 | |
| **入睡潜伏期** | 0.11 | 10-20 分钟正常，>30 分钟扣分 | DIAMOND measures, 2024 |
| **时间一致性** | 0.10 | 入睡/起床时间的圆形标准差 | SRI 概念, Fischer et al., 2024 |

入睡潜伏期评分（临床阈值）：
- ≤ 20 分钟：100（正常）
- 20-30 分钟：渐进扣分
- \> 30 分钟：加速扣分（可能提示失眠）

一致性评分使用 7 天入睡时间和起床时间的圆形标准差，映射到 0-100（标准差越低分数越高）。

#### 训练负荷评分（0-100）

使用 **心率储备（HRR）法**，而非急慢性负荷比（ACWR）。

ACWR 曾广泛用于运动科学，但已被质疑缺乏预测力。研究显示，将数据作为连续变量处理（而非分桶）后，ACWR 与伤病的关联消失（Impellizzeri et al., 2019; Wang et al., 2020）。原作者也对论文中使用"predicts"一词表示遗憾（Hulin & Gabbett, 2018）。

本工具的方法：

```
最大心率 = max(28天运动中的最大心率)，无数据时 fallback 到 220 - 年龄
心率储备 = 最大心率 - 静息心率
阈值 = 静息心率 + 心率储备 × 0.45
```

评分基于每周超过阈值的分钟数 vs WHO 推荐范围（每周 150-300 分钟中高强度运动）：

| 区间 | 分钟/周 | 评分 |
|---|---|---|
| 不活跃 | 0 | 0 |
| 训练不足 | < 75 | 0-30 |
| 偏低 | 75-150 | 30-50 |
| 有效提升 | 150-300 | 50-80 |
| 负荷偏高 | 300-450 | 80-95 |
| 过度训练 | > 450 | 95-100 |

目标训练区间是自适应的——推荐范围根据恢复评分动态调整。

#### 综合评分（0-100）

加权组合：恢复 0.35 + 睡眠 0.30 + 训练负荷 0.15 + 压力 0.10 + 血氧 0.10。数据缺失时权重按比例重分配。

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

### 参考文献

#### HRV 恢复与基线

- Altini, M. (2013). Heart Rate Variability (HRV) for guided training. HRV4Training.
- Plews, D. J., Laursen, P. B., et al. (2013). Training adaptation and HRV in elite endurance athletes. *Sports Medicine*, 43(7), 539-552.
- Nuuttila, O.-P., et al. (2022). Reliability and sensitivity of nocturnal HR and HRV in monitoring individual responses to training load. *Int J Sports Physiol Perform*, 17(8), 1296.
- Nature Scientific Reports (2025). Individual training prescribed by HRV, HR and well-being scores in experienced cyclists. *Sci Rep*, 15, 13540.
- Frontiers in Sports and Active Living (2025). Mapping HRV in sports science: from monitoring to machine learning.
- Terra Research (2025). Descriptive HRV using z-scores: analysis of 100,000 HRV records.
- ScienceDirect (2025). Interpreting wearable-derived HRV, sleep, and workload in recovery capacity.

#### 训练负荷（ACWR 批评）

- Hulin, B. T., & Gabbett, T. J. (2018). Indeed association does not equal prediction. *Br J Sports Med*, 53(3), 144.
- Impellizzeri, F. M., et al. (2019). Acute to chronic workload ratio: is there scientific evidence? *Br J Sports Med*.
- Wang, C., et al. (2020). Acute:chronic workload ratio and injury risk in sports: a systematic review. *Sports Medicine*.
- MDPI Applied Sciences (2024). A systematic review on utilizing the acute to chronic workload ratio.

#### 睡眠质量与一致性

- Fischer, D., et al. (2024). Sleep regularity index as an emerging digital measure. DIAMOND / DATAcc.
- MIT Media Lab / BHI'25 (2025). Associations between circadian sleep alignment, sleep regularity, and well-being: evidence from wearable data.
- MIT M.Eng. Thesis (2024). Predicting changes in individual wellbeing scores using sleep data from wearables.
- Frontiers in Pain Research (2025). Comparing self-reported sleep quality and wearable-derived sleep metrics.
- Sleep Advances / Oxford (2025). Performance validation of six commercial wrist-worn wearable sleep trackers.
- PSQI: Buysse, D. J., et al. (1989). The Pittsburgh Sleep Quality Index. *Psychiatry Research*, 28(2), 193-213.

#### 开源算法参考

- Open Wearables (2025). Open-source health scoring algorithms for wearable data. MIT License. github.com/the-momentum/open-wearables
- AI Endurance (2022-2025). Personalized HRV recovery model. aiendurance.com

### 技术栈

Python >= 3.10, httpx, pydantic v2, rich, python-dotenv

### 免责声明

本工具仅供健康数据参考，不构成医疗建议。如有健康问题请咨询专业医生。

### 许可证

[MIT License](LICENSE)
