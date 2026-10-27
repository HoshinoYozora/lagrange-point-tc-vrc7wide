# Lagrange Point 汉化版 Ver1.1 · 精确模拟器修正补丁

《Lagrange Point》（ラグランジュポイント，Konami 1991）中文汉化版 **Ver1.1** 只能在模拟
不够精确的模拟器上跑：在 Mesen 这类精确模拟器上，一开机就死机（黑屏 + PC 飞进 RAM），
侥幸进游戏也是满屏乱码。

这个仓库提供让它在精确模拟器上正常运行的**修正补丁**（ROM 补丁本身，不含模拟器）。

模拟器侧的改动（VRC7-Wide = `mapper 85 / submapper 2`）在另一个仓库：
<https://github.com/HoshinoYozora/MesenCE/releases/tag/v2.2.1-vrc7wide>

## 问题根因

两个独立的问题，都是"汉化版超出了标准 VRC7 的设计范围"：

1. **PRG 寻址只有 6 位**
   汉化版是 1 MiB PRG，把汉化引擎 / 文本 / 字库放在第 64~127 号 8 KiB bank，用普通 8 位
   写入选 bank（`LDA #$41 / STA $9000`），即期望 `page = value & 0x7F`。
   标准 VRC7 的三个 PRG bank 寄存器只取 6 位（`value & 0x3F`，最多 64×8 KiB = 512 KiB），
   于是 `$41` 被当成第 1 号 bank → 读出的字库/代码全错 → 乱码。

2. **复位阶段 PRG RAM 未使能**
   汉化引擎在复位早期就用卡带 PRG RAM（`$6400` 起）当跳转表，而 VRC7 上电时
   `$E000` 的 bit7 = 0（PRG RAM 关闭）。精确模拟器如实返回开总线值，`JMP ($6409)`
   跳到垃圾地址 → CPU 飞进 RAM，死机。不精确的模拟器把 `$6000-$7FFF` 一律映射成可读写
   RAM，所以碰巧能跑。

对应的两个修正：

| 修正 | 位置 | 做法 |
|---|---|---|
| PRG RAM 使能 | ROM，`$FDE6`（固定 bank 的空白区） | 8 字节桩：`LDA #$80; STA $E000; JMP $FDAC`，并把 `$E93D`/`$E94C` 两处早期引擎调用改成 `JSR $FDE6` |
| 7 位 PRG bank | 模拟器 | 新增 VRC7-Wide（`mapper 85 / submapper 2`），bank 掩码 `0x3F` → `0x7F`，其余与 VRC7 完全一致（FM 音乐保留） |

ROM 侧只需改 **14 个字节**：NES 2.0 头 4 字节（声明 mapper 85 / submapper 2 / 8 KiB
PRG-NVRAM / 8 KiB CHR-RAM）+ 8 字节启动桩 + 2 个跳转操作数。

## 补丁

| 文件 | 大小 | 底包 | 说明 |
|---|---|---|---|
| `LagrangePoint-JP-to-TC-Ver1.1-vrc7wide.bps` | 150,271 B | 日版**原版** ROM | 补丁打在原版上，直接得到汉化修正版（**推荐**） |
| `LagrangePointTC-Ver1.1-vrc7wide.bps` | 59 B | 汉化版 Ver1.1 | 只含那 14 字节改动，带 CRC32 校验 |
| `LagrangePointTC-Ver1.1-vrc7wide.ips` | 47 B | 汉化版 Ver1.1 | 同上，IPS 格式 |

### 底包校验值

日版原版（TOSEC / No-Intro）：

| | |
|---|---|
| 文件 | `Lagrange Point (1991-04-26)(Konami)(JP).nes` |
| 大小 | 524,304 字节（512 KiB PRG + 16 字节 iNES 头） |
| CRC32 | `AD2966D3` |
| SHA1 | `FDC91A8B370977720D8EFE16F260FD58730FE495` |

汉化版 Ver1.1：

| | |
|---|---|
| 文件 | `Lagrange+Point+(TC)+Ver1.1.nes` |
| 大小 | 1,048,592 字节（1 MiB PRG） |
| CRC32 | `6BB3B40E` |
| SHA1 | `91807E2D07465EF9C5424F54DA3776D5684C0DA8` |

打完补丁后的结果（两种打法完全一致，逐字节相同）：

| | |
|---|---|
| 大小 | 1,048,592 字节 |
| CRC32 | `900BFB54` |
| SHA1 | `CC91AC192BFF4FB2F3344C82E943EB54D7457EA1` |

### 用法

Mesen / MesenCE / Mesen2 都按文件头识别 IPS / BPS，扩展名无所谓：

1. 把补丁文件和底包 ROM 放在同一个文件夹里；
2. 打开模拟器，`File → Open`（或直接把补丁文件拖进窗口）选中补丁；
3. 同目录只有一个 ROM 时会自动配对加载；有多个会让你选 ROM；
   若已经在跑别的 ROM，会弹窗确认"打补丁并重置"。

补丁只在内存里生效，不会改写你的 ROM 文件。

### 为什么"原版补丁"是 BPS 而不是 IPS

IPS 的偏移是 3 字节，而且**不能改变文件长度**。原版是 512 KiB、汉化版是 1 MiB，长度变了，
IPS 格式上做不到。BPS 支持改变长度并自带 CRC32 校验（底包不对直接拒绝，不会产出坏 ROM），
Mesen 原生支持。

那个 14 字节的增量补丁不改长度，所以 IPS / BPS 两种格式都提供。

## 需要的模拟器

修正后的 ROM 声明 `mapper 85 / submapper 2`（VRC7-Wide），需要支持该变体的模拟器：

- 现成构建：<https://github.com/HoshinoYozora/MesenCE/releases/tag/v2.2.1-vrc7wide>
  （MesenCE 2.2.1 自编译版，已内置 VRC7-Wide）
- 或者自己给 Mesen/Mesen2 的 mapper 实现加一个 7 位掩码（见 `mesence-vrc7-wide.patch`
  与 `mapper_vrc7_wide.md`，在 MesenCE 仓库里）

`play_in_mesen.bat` 是个小启动器：把这批文件解压到 ROM 所在目录、把 `MesenCE\Mesen.exe`
放在旁边（或把模拟器路径作为第一个参数传进去），双击即可。

## 验证

不是"看起来能跑"就算：

- **补丁正确性**：用 Mesen 源码里的 `IpsPatcher` / `BpsPatcher`（`tools/patch_check/`，
  把 MesenCE 的 patch 实现编成小工具）实际打补丁：
  - 日版原版 + 完整 BPS → 与参考 ROM 逐字节一致（1,048,592 字节，CRC32 `900BFB54`）
  - 汉化版 + 14 字节 IPS/BPS → 同上
  - 拿错底包 → CRC32 不匹配，被拒绝
- **实际运行**：在 MesenCE 无头模式下导出 PPU/CHR/OAM 再重新渲染，确认
  汉化组启动画面 → 标题 → 存档菜单 → 开场旁白「大陸1 大陸2 衛星基地 /
  3 個空間殖民地被稱為：/「伊西斯星團」」→ 场景 → 状态菜单（列表/物品/能力/装备/
  编队、HP 75/75、BP 500/500、状态 正常）全部正常；VRC7 FM 寄存器持续被写入、
  通道输出非零（音乐正常）。
- **未影响原版**：原版 Lagrange Point (JP)（submapper 0）在同一个模拟器构建里行为不变。

## 重新生成补丁

需要三个 ROM（原版、汉化版、修正版）放在工作区根目录：

```
python tools/make_rom_patch.py
```

脚本会打印差异区域、生成三个补丁，并用自带的独立 IPS/BPS 解析器做 round-trip 校验。
`tools/patch_check/` 是用 Mesen 自己的打补丁实现交叉验证的小工具（编译方法见文件头注释）。

## 许可与版权

- `tools/`、`play_in_mesen.bat` 为本项目自行编写，可按 MIT 使用（见 `LICENSE`）。
- `LagrangePoint-JP-to-TC-Ver1.1-vrc7wide.bps` 是"日版原版 → 汉化修正版"的完整补丁，
  **包含汉化数据**（相当于以补丁形式分发汉化版），但不含日版原版 ROM 本身。
  分发/使用前请自行确认符合你所在地区的法律与汉化组的授权要求。
- `LagrangePointTC-Ver1.1-*.ips/.bps` 只含本项目自己的 14 字节改动，不含任何原作或汉化数据。
- 原作版权属 Konami；汉化内容版权属汉化组。
