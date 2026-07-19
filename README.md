# CcWatch — Claude Code 上手腕

**中文** · [English](README.en.md)

![CcWatch](docs/hero.png)

**CcWatch** 是给 Claude Code 用户的佳明表盘(Descent G2):抬腕看 **Claude 额度环**(5 小时窗口 + 每周用量 + 重置倒计时)+ 睡眠/身体数据 + 忙碌小螃蟹(有 `claude` 进程在跑时它就敲鼓)。

> 📖 **安装指导**:[中文](INSTALL.md) · [English](INSTALL.en.md)

## 表盘显示什么

- `5H 12% 3H33M` —— 5 小时窗口:已用 % + 距重置时间
- `7D 64% 2D13H` —— 每周窗口:已用 % + 距重置时间
- 像素小螃蟹:有 `claude` CLI 进程在跑时打鼓
- 链路灯:绿 = 数据新鲜(<25 分钟)· 黄 <60 分钟 · 红 = 断了

## 本仓是什么:companion(额度数据源)

单文件 Python、纯标准库。它在你登录了 Claude Code 的电脑上读订阅用量,推给手表。两种模式:

| 模式 | 一行命令 | 适合 |
|---|---|---|
| **云端推送(推荐)** | `--push <cloud>/wc/report --token <你的token>` | 零暴露零运维 |
| 自托管 | `--token <secret> --port 8399` | 你已有自己的端点 |

**平台**:macOS ✅(从钥匙串读 token)· Linux ✅(读 `~/.claude/.credentials.json`)· 原生 Windows ❌(用 WSL)。前提:这台电脑登录着 Claude Code。

## 云端推送模式(推荐)

1. 打开免费手表云 <https://watch.xiaohuiwangai.cn/wc/cc>,输入表盘上的配对码(或点一键拿 token)
2. 在登录了 Claude Code 的电脑上:

```bash
python3 ccwatch_companion.py --push https://watch.xiaohuiwangai.cn/wc/report --token <你的token>
```

3. 配对码激活的表盘会自动配好,无需手动填设置

### 常驻运行(一条命令)

```bash
python3 ccwatch_companion.py --push https://watch.xiaohuiwangai.cn/wc/report --token <你的token> --install
```

装成后台服务(macOS launchd / Linux systemd 用户单元),开机自启、挂了自动拉起。`--uninstall` 卸载。

## 🔄 数据多久更新一次

| 环节 | 频率 |
|---|---|
| companion 上报 Claude 用量 | **每 5 分钟**(`--interval` 可调) |
| 表盘从云端刷新 | 约每 10 分钟(佳明后台周期) |
| 睡眠/身体数据(云端拉佳明) | 小时级自动;仪表盘有「立即同步」 |
| companion 超 20 分钟没上报 | Claude 环显示 "?"(其他数据不受影响) |

## 自托管模式

```bash
python3 ccwatch_companion.py --token pick-a-secret --port 8399
curl "http://localhost:8399/watch?t=pick-a-secret"
```

手机侧要能访问该 URL(表盘经手机 Garmin Connect 取数):Tailscale Funnel / Cloudflare Tunnel / 自己的反代均可。表盘设置里填 URL + token(Garmin Connect Mobile → 设备 → Connect IQ 应用 → CC Watch → 设置)。

## 数据契约(`GET /watch?t=<token>`)

```json
{"ok": true, "ts": 1783500000,
 "fh_used": 12, "wk_used": 64,
 "fh_resets": "3h33m", "wk_resets": "2d13h",
 "busy": 1, "pending": 0, "done_str": ""}
```

任何实现此契约的端点都能用。

## 支持

免费开源。觉得有用可以[请我喝杯咖啡 ☕](https://ko-fi.com/xiaohuiwang)。
