# 前端远程访问（组员不在同一 WiFi）

`127.0.0.1` 和 `192.168.x.x` **只能本机或同一局域网**用。组员在外地/别的网络时，需要下面三种方式之一。

---

## 方案对比（推荐顺序）

| 方案 | 适合场景 | 难度 | 费用 |
|------|----------|------|------|
| **A. 内网穿透（ngrok 等）** | 临时演示、联调、答辩彩排 | 低 | 免费档够用 |
| **B. 云服务器部署** | 答辩、长期给组员用 | 中 | 学生机约几十元/月 |
| **C. 组员本地各自跑** | 只演示 UI、不需共用你这台机器 | 低 | 0 |

**不需要科学上网代理** 才能打开你们自己的前端页面；穿透/云部署是「让别人能连到你电脑或服务器」，和翻墙无关。

---

## 方案 A：ngrok 内网穿透（最快，约 5 分钟）

### 1. 安装 ngrok

1. 打开 https://ngrok.com/ 注册账号（免费）
2. 下载 Windows 版，解压到任意目录（如 `C:\tools\ngrok.exe`）
3. 控制台复制你的 authtoken，执行一次：

```powershell
ngrok config add-authtoken 你的token
```

### 2. 启动（两个窗口）

**窗口 1** — 先启动你们的工作台：

```text
D:\大创\anyclaw\scripts\start_frontend.bat
```

**窗口 2** — 穿透 8000 端口：

```powershell
ngrok http 8000
```

### 3. 发给组员

ngrok 会显示一行 **Forwarding**，例如：

```text
https://abc123.ngrok-free.app -> http://localhost:8000
```

把 **`https://abc123.ngrok-free.app`** 发给组员即可（全国哪都能开，不要求同一 WiFi）。

注意：

- 你电脑要**一直开着**，两个窗口都不能关
- 免费版 URL **每次重启 ngrok 会变**，要重新发链接
- 首次打开 ngrok 免费页可能有个「Visit Site」按钮，点一下再进

也可双击：`scripts\start_frontend_ngrok.bat`（会先检查本机 8000 是否已启动）。

---

## 方案 B：云服务器（答辩推荐）

买一台有**公网 IP** 的云主机（阿里云/腾讯云学生机等），把项目拷上去：

```bash
# 服务器上
cd anyclaw
pip install -r requirements.txt
# 配置 .env 里的 QWEN_APIKEY
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

安全组/防火墙**放行 8000 端口**，组员访问：

```text
http://你的公网IP:8000/
```

优点：链接固定、不用你一直开着笔记本。缺点：要部署和维护一次。

---

## 方案 C：组员各自本地运行

把项目 zip 或 Git 发给组员，每人本机：

```powershell
cd anyclaw
pip install -r requirements.txt
# 各自配置 .env
scripts\start_frontend.bat
```

每人访问自己的 `http://127.0.0.1:8000/`。  
适合：**只看界面流程**；若要用**你的知识库和 API 配额**，仍建议 A 或 B。

---

## 常见问题

**Q：组员打开 ngrok 链接很慢或打不开？**  
A：检查你这边 `start_frontend.bat` 是否在跑；ngrok 窗口是否还在；换手机热点试一次。

**Q：需要 VPN 吗？**  
A：访问你们自己的 ngrok/云服务器地址 **不需要**。只有调用境外 API 时才看 `.env` 和网络环境。

**Q：答辩当天用哪个？**  
A：彩排用 **ngrok**；正式答辩前一夜建议 **云服务器**，避免现场电脑休眠断线。
