# gxstzy-shixun-platform

广西生态工程职业技术学院 · 教务处实训科管理平台（FastAPI + Logto + Turso）。

## 本地运行

```powershell
cd c:\00CS\text
.\venv\Scripts\python.exe scripts\sync_shixun_platform_static.py
cd output\gxstzy-shixun-platform
..\..\venv\Scripts\pip.exe install -r requirements.txt
# 密钥见 workspace secrets/shixun-platform/.env（勿提交）
..\..\venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000/ → Logto 登录（邮箱或手机号，视控制台配置） → 平台首页。

## Space 部署

- **service_name**：`gxstzy-shixun`
- **URL**：https://gxstzy-shixun.ai-builders.space
- `LOGTO_APP_SECRET`、`TURSO_AUTH_TOKEN` 等密钥**不要**写入公开仓库或 `deploy-config.json` 的 `env_vars`；部署时走教员密钥通道。
- Logto Redirect URI 需包含：`https://gxstzy-shixun.ai-builders.space/callback`

## 健康检查

`GET /health` — 含 Turso `schema_version`
