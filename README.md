# KaniSkills

我的 CodeBuddy 用户级 skill 集合（"法术书"），可版本化管理并推送至 GitHub。

> 比喻：你是写法术的法师，本仓库是你的法术书；CodeBuddy（魔杖）按 `skills/` 下的
> `SKILL.md` 指引执行。

## 已有法术

| Skill | 说明 |
|-------|------|
| `bbg-morning-macro-brief` | Bloomberg ASKB 驱动的全球市场晨间简报，覆盖多资产（ equities / rates / FX / commodities / credit / positioning ），交叉验证 5+ 免费数据源，输出专业 DOCX 报告并邮件分发 |
| `global-markets-brief` | 纯免费数据源版本的全球市场日报（Yahoo Finance / FRED / Finnhub / NewsAPI / Alpha Vantage），含自检审计模块 |

## 架构

```
codebuddy-skills/
├── README.md
├── .gitignore                 # 排除 .env / config.json / .codebuddy / data/ / input/ / 缓存
├── LICENSE
├── skills/                    # ★ 自定义 skill（纳入版本控制，推 GitHub）
│   ├── bbg-morning-macro-brief/
│   │   ├── SKILL.md
│   │   ├── scripts/           # Python：采集/生成/对账/发送
│   │   ├── references/        # Bloomberg ASKB 工作流 & schema 参考
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

# 安装：把 skills/ + downloaded/ 下每个法术软链到 CodeBuddy 发现目录
./scripts/install.sh

# 重启 CodeBuddy 使新法术生效
```

## 新增一个法术

```bash
mkdir -p skills/my-new-skill/scripts
# 编写 skills/my-new-skill/SKILL.md（含 name + description 前置字段）
# 提交
git add skills/my-new-skill && git commit -m "feat: add my-new-skill"
```

## 安装第三方法术

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
