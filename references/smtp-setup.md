# SMTP 配置

`scripts/send_schedule.py` 只从**环境变量**读凭据。仓库里没有任何地方存密码，也不该有。

## 铁律：授权码不落盘

各家邮箱的「授权码 / 应用专用密码」等价于你的邮箱密码，泄露了别人就能以你的名义发信、也能读你的邮件（视协议而定）。

- 不要写进 `config.json`、不要写进脚本、不要写进 README、不要贴进 issue
- 不要让 AI 助手把它写进任何文件——**每次运行时现给**
- 已经泄露过的，去邮箱设置里**删掉重新生成**，改密码没用，授权码是独立的

## 拿授权码

| 邮箱 | host | port | 怎么拿 |
|---|---|---|---|
| QQ 邮箱 | `smtp.qq.com` | 465 | 设置 → 账号 → POP3/SMTP 服务 → 开启 → 生成授权码。**发件人必须等于登录账号** |
| 163 邮箱 | `smtp.163.com` | 465 | 设置 → POP3/SMTP/IMAP → 开启 → 新增授权密码 |
| Gmail | `smtp.gmail.com` | 465 | 需先开两步验证 → Google 账号 → 应用专用密码 |
| Outlook | `smtp.office365.com` | 587 | 需 STARTTLS，本脚本默认走 465 隐式 TLS，用 Outlook 需自行改 |

脚本默认 `smtp.qq.com:465`，其他家用 `SMTP_HOST` / `SMTP_PORT` 覆盖。

## 运行

**bash / zsh**（前置赋值，只对这一条命令生效）：

```bash
SMTP_USER='you@example.com' SMTP_PASS='<授权码>' \
  python scripts/send_schedule.py my/schedule.html
```

**不进 shell 历史**的写法（前面加一个空格，需 `HISTCONTROL=ignorespace`；或者用下面的 read）：

```bash
read -rs SMTP_PASS && export SMTP_PASS   # 输入时不回显，不进历史
SMTP_USER='you@example.com' python scripts/send_schedule.py my/schedule.html
unset SMTP_PASS                          # 用完清掉
```

**PowerShell**：

```powershell
$env:SMTP_USER = 'you@example.com'
$env:SMTP_PASS = Read-Host -AsSecureString | ForEach-Object { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)) }
python scripts/send_schedule.py my/schedule.html
Remove-Item Env:SMTP_PASS
```

## 先干跑一遍

`--dry-run` 不需要凭据，只把收件人、主题、HTML 大小打出来，用来确认参数没写错：

```bash
python scripts/send_schedule.py examples/schedule-demo.html --dry-run
```

## 只发正文，不发附件

脚本固定把 HTML 作为**邮件正文**发送（`add_alternative(..., subtype="html")`），不附加 HTML 附件——手机上打不开附件，纯属占空间。

`set_content()` 里塞的纯文本是给拒绝渲染 HTML 的客户端兜底的，HTML 正常时看不见。

## 报错对照

| 输出 | 原因 |
|---|---|
| `FAILED ConfigError SMTP_USER / SMTP_PASS not set` | 环境变量没传进来。注意 `sudo` 和某些 IDE 终端会清环境变量 |
| `FAILED SMTPAuthenticationError` | 用了登录密码而不是授权码；或授权码已失效；或 SMTP 服务没开 |
| `FAILED SMTPSenderRefused` | `MAIL_FROM` 不等于登录账号。QQ / 163 都强制两者一致 |
| `FAILED SMTPServerDisconnected` / `timeout` | 端口被网络策略挡了；换网络，或确认该服务商的端口 |
| `FAILED SSLError` | 该端口不是隐式 TLS（如 587 需要 STARTTLS），换 465 或改脚本 |
