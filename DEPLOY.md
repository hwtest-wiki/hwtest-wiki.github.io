# 部署到 GitHub Pages（手把手）

> 本仓库 = 硬件测试科普百科（VitePress）。`articles/` 与 `public/images/` 是网站内容（已入库）；
> 私有源（`第NN篇/*.md`、视频、封面、公众号 HTML）不在本仓库，不会被发布。

## 一、账号准备（重要）
- **用个人 GitHub 账号**，不要用企业托管账号（EMU，如 `*_microsoft`）——EMU 一般不能建公开仓库、Pages 也不对外。
- 让 token 带 `workflow` 权限（否则推送 `.github/workflows` 会被拒）：
  ```powershell
  gh auth login --scopes "repo,workflow"
  # 或为已登录账号补权限：
  gh auth refresh -h github.com -s workflow
  ```

## 二、创建仓库并推送
在 `site/` 目录下执行：
```powershell
cd D:\copilot\硬件测试科普系列\site
git init -b main
git add .
git commit -m "init: 硬件测试科普百科 VitePress 站"
gh repo create hw-test-wiki --public --source . --remote origin --push
```
> 仓库名 `hw-test-wiki` 可改。最终网址为 `https://<你的用户名>.github.io/hw-test-wiki/`。
> 若想要 `https://<用户名>.github.io/`（根路径），把仓库命名为 `<用户名>.github.io`。

## 三、开启 Pages
仓库 → **Settings → Pages → Build and deployment → Source 选「GitHub Actions」**。
（首次推送后，Actions 会自动跑 `deploy.yml` 构建并部署；base 路径由 `configure-pages` 自动注入，无需手改。）

## 四、查看网址
仓库 → **Actions** 看部署是否成功；成功后在 **Settings → Pages** 顶部或 deploy 任务里看到网址。

## 五、以后更新内容（每次改完文章/视频）
```powershell
cd D:\copilot\硬件测试科普系列\site
python build_content.py     # 从私有源重新生成 articles/ 与 public/images/
git add .
git commit -m "update: 第NN篇"
git push                    # 推送后 Actions 自动重新部署
```

## 私密红线
- 机密资料（如 Power test Procedure）**绝不入库**。
- 本仓库只含已发布的科普网站内容，均为可公开知识。
