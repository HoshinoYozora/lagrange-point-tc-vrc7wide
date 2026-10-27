# Lagrange Point 汉化版 Ver1.1 · 精确模拟器修正补丁

《Lagrange Point》（ラグランジュポイント，Konami 1991）中文汉化版 Ver1.1 只能在模拟
不够精确的模拟器上运行，在 Mesen 这类高精确度模拟器上无法正常运行。

这个仓库提供让它在精确模拟器上正常运行的修正补丁（ROM 补丁本身，不含模拟器）。

### 底包校验值

日版原版（TOSEC / No-Intro）：

| | |
|---|---|
| 文件 | `Lagrange Point (1991-04-26)(Konami)(JP).nes` |
| 大小 | 524,304 字节（512 KiB PRG + 16 字节 iNES 头） |
| CRC32 | `AD2966D3` |
| SHA1 | `FDC91A8B370977720D8EFE16F260FD58730FE495` |

## 需要的模拟器

修正后的 ROM 声明 `mapper 85 / submapper 2`（VRC7-Wide），需要支持该变体的模拟器：<https://github.com/HoshinoYozora/MesenCE/releases/tag/v2.2.1-vrc7wide>（MesenCE 2.2.1 自编译版，已内置 VRC7-Wide）
**未经过详细测试，不保证全程正常运行！**

## 许可与版权

- `LagrangePoint-JP-to-TC-Ver1.1-vrc7wide.bps` 是"日版原版 → 汉化修正版"的完整补丁，
  **包含汉化数据**，但不含日版原版 ROM 本身。
  分发/使用前请自行确认符合你所在地区的法律要求。
- 原作版权属 Konami；汉化内容版权属汉化组。
