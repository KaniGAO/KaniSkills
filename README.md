# KaniSkills

个人 CodeBuddy 用户级 skill 仓库，集中管理我自己编写并持续维护的 skills，可版本化、可移植，并通过 GitHub 备份与分发。

## 项目概览：全球市场每日晨报（Global Macro Daily Brief）

本仓库的核心是一个**自动化的全球宏观市场每日晨报系统**，由两个配套的 skill 组成：

| Skill | 数据源 | 用途 |
|-------|--------|------|
| `bbg-morning-macro-brief` | Bloomberg ASKB（主）+ 5+ 免费源交叉验证 | 以 Bloomberg 终端为主要数据源生成专业级 DOCX 晨报 |
| `global-markets-brief` | 纯免费数据源（Yahoo / FRED / Finnhub / NewsAPI / Alpha Vantage） | 不依赖 Bloomberg 终端的轻量替代版本，含自检审计模块 |

### 晨报覆盖的资产与研究维度

报告按照真实交易台的视角组织，覆盖完整的宏观 desk 频谱：

- **股票（Equities）**：S&P 500、Nasdaq 100、Euro Stoxx 50、FTSE 100、Nikkei 225、CSI 300、Hang Seng、MSCI EM
- **利率与曲线（Rates & Curves）**：美/德/英/日 10Y 收益率、2s10s 与 5s30s 利差、swap spread、实际收益率
- **外汇与远期（FX & Forwards）**：G10 + USDCNH，carry trade 动态、1Y 远期点
- **大宗商品（Commodities）**：原油（Brent / WTI）、黄金、白银、铜、天然气
- **信用（Credit）**：IG / HY OAS、主权 CDS、EM 主权利差
- **持仓与资金流（Positioning & Flows）**：CFTC/IMM 净投机持仓、拥挤头寸识别、TRACE / 贷款市场情绪

### 报告结构

每份报告产出 8 个标准章节：

1. **Executive Summary** — 当日核心叙事
2. **宏观日历** — 本周关键数据 / 央行事件
3. **隔夜市场回顾** — 跨资产涨跌与驱动因素
4. **宏观发展** — 经济意外指数、就业、PMI、通胀
5. **央行观察** — FOMC / BOJ / ECB / BOE / PBoC 决策与表态
6. **访谈要点（Interview Talking Points）** — 可直接用于交易台沟通的要点 + 方向性交易想法（曲线、波动率、配对交易）
7. **亚洲前瞻（Asia Day Ahead）** — 催化剂排序、关键支撑/阻力位
8. **关键水平（Key Levels）** — 主要资产支撑/阻力与交易含义

### 系统特点

- **多源交叉验证（Reconciliation）**：Bloomberg 数据作为 primary source，再用 Yahoo / FRED / Alpha Vantage 等免费源交叉核对，自动标记数据异常（如 FX 在不同源间的偏差）并生成质量告警 —— 直接对应交易台对数据完整性的要求。
- **可审计（Audit）**：`global-markets-brief` 内置审计模块（judge / accuracy_check / fetch_ground_truth），可对照真实数据校验报告准确性。
- **自动化分发**：生成 DOCX 后通过 Gmail SMTP 逐人发送，收件人互不可见。
- **Bloomberg ASKB 工作流**：`bbg-morning-macro-brief` 通过粘贴 Bloomberg ASKB 输出获得 proprietary 数据，配合 `references/` 下的工作流与 schema 文档实现标准化采集。
- **数据完整性**：真实 API Key 存于 `.env`（不入库），Bloomberg 粘贴输入与运行期数据库存于 `data/`、`input/`（被 `.gitignore` 排除）。

## 仓库结构

```
KaniSkills/
├── README.md
├── .gitignore                 # 排除 .env / .codebuddy / data/ / input/ / 缓存
├── LICENSE
├── skills/                    # ★ 自定义 skill（纳入版本控制）
│   ├── bbg-morning-macro-brief/
│   │   ├── SKILL.md
│   │   ├── scripts/           # 采集 / 生成 / 对账 / 发送
│   │   ├── references/        # Bloomberg ASKB 工作流 & schema
│   │   └── assets/
│   └── global-markets-brief/
│       ├── SKILL.md
│       ├── scripts/
│       └── assets/
├── downloaded/                # ★ 第三方下载的 skill（gitignore 排除，不推 GitHub）
├── scripts/install.sh         # 软链 skills/* + downloaded/* -> ~/.codebuddy/skills/
├── docs/ARCHITECTURE.md       # 架构说明
└── .github/workflows/         # CI：校验 SKILL.md + 密钥扫描（gitleaks）
```

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 快速开始

```bash
# 克隆
git clone git@github.com:KaniGAO/KaniSkills.git
cd KaniSkills

# 安装：把 skills/ + downloaded/ 下每个 skill 软链到 CodeBuddy 发现目录
./scripts/install.sh

# 重启 CodeBuddy 使新 skill 生效
```

## 新增一个 skill

```bash
mkdir -p skills/my-new-skill/scripts
# 编写 skills/my-new-skill/SKILL.md（含 name + description 前置字段）
# 提交
git add skills/my-new-skill && git commit -m "feat: add my-new-skill"
```

## 安装第三方 skill

```bash
# 将第三方 skill 放到 downloaded/ 目录下，install.sh 会自动发现并软链
# downloaded/ 已被 .gitignore 排除，不会推送至 GitHub
mkdir -p downloaded/some-skill
# 放入 SKILL.md + scripts/...
./scripts/install.sh
```

## ⚠️ 安全

- 真实 API Key 明文存于各 skill 的 `.env`，已被 `.gitignore` 排除，**切勿手动 `git add`**。
- 只提交 `.env.example`（占位符模板）。
- Bloomberg 粘贴输入（`skills/*/input/`）和运行期数据库（`skills/*/data/`）均被排除，不含 proprietary data。
- CI（`validate.yml`）会在每次 push 时跑密钥扫描（gitleaks），误提交会被拦下。
- 若需轮换密钥，改对应 `.env` 即可，无需动代码。
