# 前端工作台启动

## 1. 安装依赖（若未安装）

```powershell
cd D:\大创\anyclaw
pip install -r requirements.txt
```

## 2. 配置 API Key

确保 `.env` 中有 `QWEN_APIKEY=...`

## 3. 启动 Web 服务

**推荐（双击或命令行）：**

```text
D:\大创\anyclaw\scripts\start_frontend.bat
```

或 PowerShell：

```powershell
D:\大创\anyclaw\scripts\start_frontend.ps1
```

手动启动（已改为局域网可访问 `0.0.0.0`）：

```powershell
cd D:\大创\anyclaw
$env:PYTHONIOENCODING='utf-8'
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- **本机**：http://127.0.0.1:8000/
- **组员（同一 WiFi）**：http://你的局域网IP:8000/（启动脚本会打印，如 `http://192.168.1.23:8000/`）

组员**不能**使用 `127.0.0.1`。不需要代理。

若组员进不去：确认服务在跑、同一局域网、Windows 防火墙允许 Python/8000 端口。

**组员不在同一 WiFi**：见 [FRONTEND_REMOTE.md](./FRONTEND_REMOTE.md)（推荐 ngrok 或云服务器）。

## 4. 功能对照

| 能力 | 界面位置 |
|------|----------|
| Hootsuite Composer | 左侧 Composer + 预设芯片 + 人工审核横幅 |
| 侧栏 AI | 右侧传播提示 / Skill 要点 |
| Sprinklr 快捷改稿 | 侧栏「更短/加 emoji/更严肃」→ `/api/posts/polish` |
| 平台预览 | 成稿区 X / Instagram 预览 Tab |
| Insert 回填 | 「Insert 回填到编辑器」按钮 |
| Floro 分场景 | 顶部：主动发帖 / 选题 / 回复 |
| 论据透明面板 | 底部卡片/列表/来源三视图 |
| 无证据即停 | 管道可视化 + 红色门控告警 |

## 5. API 端点

- `GET /api/health` `GET /api/meta`
- `POST /api/posts/generate` `POST /api/posts/topics` `POST /api/posts/polish`
- `POST /api/replies/generate` `POST /api/evidence`
