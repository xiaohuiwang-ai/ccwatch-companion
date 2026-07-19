# CcWatch 安装指导

> 适用机型:**Garmin Descent G2**(其他机型陆续支持)
> CcWatch = 给 Claude Code 用户的手表表盘:睡眠/身体数据 + Claude 用量环。

## 方式一(推荐):Connect IQ 商店安装

1. 手机打开 **Connect IQ Store** App(佳明官方应用商店)
2. 搜索 **CcWatch**,点安装——手表自动收到
3. 在表盘界面长按中键(MENU)→「表盘」→ 选中 CcWatch
4. 跳到下面「激活」一节

## 方式二:侧载安装(测试版/没有商店时)

拿到 `CcWatch.prg` 文件后,用**原装充电线**把手表连电脑:

**Mac**(需先装免费小工具 OpenMTP,Mac 默认看不到手表存储):
1. https://openmtp.ganeshrvel.com 下载安装
2. 打开 OpenMTP → 进手表存储 `GARMIN` → `APPS`
3. 把 `CcWatch.prg` 拖进去,拔线

**Windows**(免装软件):"此电脑" → Garmin 设备 → `GARMIN/APPS` → 复制进去,拔线

拔线后长按中键 →「表盘」→ 选中 **CcWatch**。

## 激活(配对码,30 秒)

首次使用表盘会显示 **PAIR CODE + 6 位数字**。

1. 手机浏览器打开:**watch.xiaohuiwangai.cn/cc**,按页面上的步进指引走
2. 在第 2 步输入表上的 6 位配对码——自动创建你的专属账户(第 1 步的 token 同时生成)
3. 第 3 步绑定佳明账号(在账户页完成):选中国区/国际区,输佳明账号密码(密码只用于一次登录,**不保存**;两步验证会让补验证码)
4. 之后不用管手表:10 分钟内自动激活(码消失),约 20-30 分钟睡眠/身体数据上屏

## 可选:Claude 用量环(需要电脑)

表盘上的 Claude usage 环需要你的电脑定时上报(5 分钟一次):

```bash
git clone https://github.com/xiaohuiwang-ai/ccwatch-companion
cd ccwatch-companion
python3 ccwatch_companion.py --push https://watch.xiaohuiwangai.cn/wc/report --token <你的token>
# 常驻安装(Mac launchd / Linux systemd):
python3 ccwatch_companion.py --install --push https://watch.xiaohuiwangai.cn/wc/report --token <你的token>
```

token 在 watch.xiaohuiwangai.cn/cc 账户页可见。不跑 companion 不影响其他数据,只是 Claude 环显示 "?"。

## 常见问题

| 现象 | 原因/办法 |
|---|---|
| 配对码一直不消失 | 表盘每 10 分钟检查一次,输完码等下一轮 |
| 配对码过期(1 小时) | 重进一次表盘拿新码重输 |
| OpenMTP 看不到手表 | 换原装线;拔插一次 |
| Claude 环显示 "?" | 电脑上的 companion 没在跑,或超过 20 分钟没上报 |
| 数据显示 "--" | 绑定后首次拉取最长 30 分钟 |

有问题在 GitHub 提 issue:https://github.com/xiaohuiwang-ai/ccwatch-companion
