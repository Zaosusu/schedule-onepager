# 邮件客户端 HTML 硬约束

这张表要在**邮件客户端里**渲染，包括手机端。邮件客户端不是浏览器：它会剥掉 `<style>` 块、忽略现代布局、重排你的 div。所以这份 HTML 必须写成 2005 年的样子。

已在 QQ 邮箱（桌面网页版 + 手机客户端）实测通过：底色、表头、图例网格、字重全部还原。其他客户端（Gmail、Outlook、网易系）遵循同一套约束通常也没问题，但**没实测过**。

## 必须

| 项 | 怎么做 |
|---|---|
| 样式 | **全部内联**，`style="..."` 写在标签上 |
| 布局 | **`<table>` 布局**。所有排版靠嵌套 table + `cellpadding` / `cellspacing` / `width` |
| 背景色 | 带背景色的 `<tr>` / `<table>` / `<td>` 要**同时**给 `bgcolor="#xxxxxx"` 属性兜底 |
| 装饰性 table | 加 `role="presentation"`，读屏软件才不会把排版表念成数据表 |
| 配色 | **浅底 + 深字**。别指望暗色模式反色，很多客户端会自己乱反 |
| 容器 | 固定宽度（默认 760px），`width="760"` 属性和 `style="width:760px;max-width:760px;"` 都写 |
| 字体 | 系统字体栈，例如 `'Microsoft YaHei','PingFang SC',Arial,sans-serif` |
| 编码 | `<meta charset="UTF-8">`，文件本身存 UTF-8 无 BOM |

## 禁止

- `<style>` 样式块、外部 CSS、`<link>`
- CSS 变量（`var(--x)`）
- flexbox、grid
- `position: absolute / fixed / relative`
- `background-clip: text`、渐变文字、`box-shadow` 之类的现代效果
- 外部字体（`@font-face`、Google Fonts）
- 外链图片当关键信息用（很多客户端默认不加载图片；图例请用带背景色的 `<span>`，不要用图片色块）
- JavaScript（一定会被剥掉）

## 一行「图例色块」的写法

不要用图片，用一个带内联背景色和边框的空 `<span>`：

```html
<span style="background-color:#e8f4f6;border:1px solid #cfd6e4;padding:3px 14px;">&nbsp;</span>&nbsp;&nbsp;活动名称
```

`&nbsp;` 是必要的——空 `<span>` 在部分客户端里高度会塌成 0。

## 一个表格行的完整写法

```html
<tr bgcolor="#f0f7f1" style="background-color:#f0f7f1;">
  <td style="padding:12px 9px;border:1px solid #d8dced;color:#333333;font-weight:bold;font-size:15px;">8月21日<br>– 8月22日</td>
  <td style="padding:12px 9px;border:1px solid #d8dced;color:#333333;">周五<br><span style="color:#c9302c;">周六</span></td>
  <td style="padding:12px 9px;border:1px solid #d8dced;color:#1e6b32;font-weight:bold;">活动名称</td>
  <td style="padding:12px 9px;border:1px solid #d8dced;color:#333333;">身份</td>
  <td style="padding:12px 9px;border:1px solid #d8dced;color:#333333;line-height:1.9;">事项明细</td>
  <td style="padding:12px 9px;border:1px solid #d8dced;color:#c9302c;font-weight:bold;">10 天</td>
</tr>
```

注意：

- 换行用 `<br>`，不要靠 CSS 控制
- 每个 `<td>` 都要自己写 `padding` 和 `border`，没有继承可用
- `border-collapse:collapse` 写在外层 `<table>` 的 style 上，同时每个 td 写 `border`，两者都需要

## 已知未解决

**容器固定 760px，手机端需要横向滑动或整体缩小。**

想做窄屏版的话，方向是：容器降到 600px 以内、长事项换行、取消「星期」列并入「日期」列。邮件客户端对 media query 支持参差，别指望响应式，宁可做一版专门的窄表。

## 自查

改完 HTML，发之前：

1. 浏览器打开一遍（这一步只能证明没写坏，不能证明邮件里没问题）
2. `grep -c "<style" schedule.html` 应该是 0
3. `grep -cE "display: *(flex|grid)|position: *(absolute|fixed)" schedule.html` 应该是 0
4. 每个有 `background-color` 的 `<tr>` 都有对应的 `bgcolor` 属性
5. 真发一封给自己，用**手机**打开看
