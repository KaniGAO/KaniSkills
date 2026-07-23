# 架构说明（ARCHITECTURE）

## 目标
把"用户级 CodeBuddy skill"沉淀为一个**可版本化、可移植、安全**的 GitHub 仓库。

## 为什么用 `skills/` 子目录，而不是直接 git init 在 `~/.codebuddy/skills/`
- 仓库根只放元信息（README / CI / 文档 / 安装脚本），与法术内容解耦；
- `skills/` 子目录与 CodeBuddy 的发现目录 `~/.codebuddy/skills/` **一一对应**，
  安装只需把 `skills/*` 软链过去，任意机器 clone 后可一键启用；
- 便于 CI 仅针对 `skills/**` 触发校验，互不干扰。

## 发现机制
CodeBuddy 启动时扫描 `~/.codebuddy/skills/` 下每个含 `SKILL.md` 的子目录，
读取其 `name` + `description` 注册为可用能力。因此软链后的法术与真实目录等效。

## 安装机制
`scripts/install.sh` 遍历 `skills/` 下每个子目录，在 `~/.codebuddy/skills/` 建立软链。
已存在的真实目录会被跳过（防误覆盖）。修改 `SKILL.md` 的 `description` 后需重启会话。

## 安全模型
| 层 | 措施 |
|---|---|
| 文件层 | `.gitignore` 排除 `.env` / `config.json` / `*.db` / 缓存 |
| 模板层 | 仅提交 `.env.example`（占位符），真实密钥永不入库 |
| 提交层 | CI 用 gitleaks 扫描每次 push，误提交密钥会被拦下 |
| 运行时 | 代码统一 `os.getenv("XXX")` 读密钥，从环境变量获取 |

## CI（.github/workflows/validate.yml）
- 校验每个 `skills/*/SKILL.md` 存在且含 `name` + `description` 前置字段；
- 跑 gitleaks 密钥扫描。
仅当 `skills/**` 变更时触发，保持轻量。

## 新增 / 修改法术
1. `mkdir -p skills/<name>/{scripts,references,assets}`
2. 写 `skills/<name>/SKILL.md`（frontmatter 必填 name + description）
3. `./scripts/install.sh` 启用
4. `git add skills/<name> && git commit`

## 关于预装（managed）法术
`web-access`、`meituan-coupon-workbuddy` 等带 `_skillhub_meta.json` 且标记
`preinstalledTemplate: true` 的法术，由 CodeBuddy 自身管理。
建议：**不要**把它们软链回发现目录（可能与 CodeBuddy 的更新/重装冲突）。
如需归档，可拷贝进仓库并标注"仅参考"，但不要由 `install.sh` 链接。
