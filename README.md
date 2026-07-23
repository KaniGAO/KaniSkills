# codebuddy-skills

我的 CodeBuddy 用户级 skill 集合（"法术书"），可版本化管理并推送至 GitHub。

> 比喻：你是写法术的法师，本仓库是你的法术书；CodeBuddy（魔杖）按 `skills/` 下的
> `SKILL.md` 指引执行。

## 架构

```
codebuddy-skills/
├── README.md
├── .gitignore                 # 排除 .env / config.json / 缓存 / 运行时 DB
├── LICENSE
├── skills/                    # ★ 对应 ~/.codebuddy/skills/
│   └── <skill-name>/
│       ├── SKILL.md           # 必需：name + description 前置字段
│       ├── scripts/           # 可选：Python/Shell/C/Node 脚本
│       ├── references/        # 可选：按需加载的参考资料
│       └── assets/            # 可选：输出模板/图标
├── scripts/install.sh         # 软链 skills/* -> ~/.codebuddy/skills/
├── docs/ARCHITECTURE.md       # 架构说明
└── .github/workflows/         # CI：校验 SKILL.md + 密钥扫描
```

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 快速开始

```bash
# 克隆（或已在本地）
cd codebuddy-skills

# 安装：把 skills/ 下每个法术软链到 CodeBuddy 发现目录
./scripts/install.sh

# 重启 CodeBuddy 使新法术生效
```

## 新增一个法术

```bash
mkdir -p skills/my-new-skill/scripts
# 编写 skills/my-new-skill/SKILL.md（含 name + description）
# 提交
git add skills/my-new-skill && git commit -m "add my-new-skill"
```

## ⚠️ 安全

- 真实 API Key 明文存于各 skill 的 `.env`，已被 `.gitignore` 排除，**切勿手动 `git add`**。
- 只提交 `.env.example`（占位符模板）。
- CI（`validate.yml`）会在每次 push 时跑密钥扫描（gitleaks），误提交会被拦下。
- 若需轮换密钥，改对应 `.env` 即可，无需动代码。

## 推送到 GitHub

```bash
git init                      # 若尚未初始化
git add -A
git commit -m "init: codebuddy skills collection"
git branch -M main
git remote add origin git@github.com:<you>/codebuddy-skills.git
git push -u origin main
```
