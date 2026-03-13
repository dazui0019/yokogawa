# Yokogawa 示波器 Linux 控制工具指南

本文档介绍如何在 Linux 环境下使用 `yokogawa_pyvisa.py` 脚本通过 USB 控制 Yokogawa DLM 系列示波器。

## 1. 环境准备

### 安装 Python 依赖

本项目使用`uv`工具来管理Python环境, 确保已安装`uv`工具, 并在项目根目录下执行以下命令来安装依赖:

```bash
uv sync
```

## 2. 配置 USB 设备权限 (关键步骤)

在 Linux 系统中，默认情况下普通用户没有权限直接访问 USB 设备。为了让脚本能通过 USB 控制示波器，你需要添加一条 `udev` 规则。

### 步骤 1: 创建规则文件

使用 `sudo` 创建并编辑文件 `/etc/udev/rules.d/99-yokogawa.rules`：

```bash
sudo nano /etc/udev/rules.d/99-yokogawa.rules
```

### 步骤 2: 添加规则内容

将以下内容复制到文件中。这条规则匹配 Vendor ID 为 `0b21` (Yokogawa) 的 USB 设备，并将权限模式设置为 `0666` (所有用户可读写)。

```udev
# Yokogawa USBTMC devices (Vendor ID 0x0B21)
SUBSYSTEM=="usb", ATTRS{idVendor}=="0b21", MODE="0666"
```

保存并退出。

### 步骤 3: 生效规则

运行以下命令重新加载 udev 规则并触发应用：

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

此时，当你插入 USB 线连接示波器时，系统应该会自动赋予正确的权限，脚本即可找到设备。

## 3. 使用方法

脚本 `yokogawa_pyvisa.py` 提供了简单的命令行接口。

### 基本语法

```bash
uv run yokogawa_pyvisa.py [全局参数] <子命令> [子命令参数]
```

### 常用命令

#### 1. Channel display toggle (channel)

Turns selected channel displays on or off. The default behavior matches the front-panel channel keys: it only toggles display state and does not change Mean measurement configuration.

```bash
# Panel-like: only turn on CH1 display
uv run yokogawa_pyvisa.py channel on -c 1

# Turn off CH1, CH2, and CH4 displays together
uv run yokogawa_pyvisa.py channel off -c 1 2 4

# Turn off all channel displays together
uv run yokogawa_pyvisa.py channel off --all

# Alias (defaults to on)
uv run yokogawa_pyvisa.py channel-on -c 1
```

Notes: `channel` defaults to `on`; `--channel` only supports `1-4` and also accepts multiple values such as `-c 1 2` or `-c 1,2,4`; `--all` selects CH1-CH4 and is mutually exclusive with `--channel`; the behavior is display-only.

#### 2. Read Mean value (mean)

Reads the current Mean value for the selected channel.

```bash
# Clean mode: output numeric value only
uv run yokogawa_pyvisa.py mean
# Example output: 12.500

# Read channel 2
uv run yokogawa_pyvisa.py mean -c 2

# Verbose mode: show connection logs and formatted result
uv run yokogawa_pyvisa.py mean -c 1 -v
```

Notes: `--channel` only supports `1-4`; out-of-range values fail fast.
Note: `mean` only reads the current value. It does not enable a channel or initialize Mean automatically. If Mean is not configured yet, enable it on the front panel first.

#### 3. Read RMS value (rms)

Reads the current RMS value for the selected channel.

```bash
# Clean mode: output numeric value only
uv run yokogawa_pyvisa.py rms
# Example output: 8.839

# Read channel 2
uv run yokogawa_pyvisa.py rms -c 2

# Verbose mode: show connection logs and formatted result
uv run yokogawa_pyvisa.py rms -c 1 -v
```

Notes: `--channel` only supports `1-4`; out-of-range values fail fast.
Note: `rms` only reads the current value. It does not enable a channel or initialize RMS automatically. If RMS is not configured yet, enable it on the front panel first.

#### 4. Screenshot (shot)

获取当前屏幕截图并保存为 PNG 文件。

```bash
# 默认保存为 DLM_年月日_时分秒.png
uv run yokogawa_pyvisa.py shot

# 指定文件名
uv run yokogawa_pyvisa.py shot -o my_scope_screen.png
```

说明：`-o/--output` 支持包含目录路径，若目录不存在会自动创建。

#### 5. 列出可用设备 (list)

列出系统当前识别到的所有 VISA 设备资源（包括 USB 和 TCPIP 设备）。这对于查找设备的序列号或资源字符串非常有用。

```bash
uv run yokogawa_pyvisa.py list
```

#### 6. 退出码 (自动化集成)

`channel` / `mean` / `rms` / `shot` 命令支持标准退出码，便于 CI 或上层脚本判断结果：

* `0`: 命令执行成功。
* `1`: 连接失败或命令执行失败。

### 指定设备序列号

如果有多个设备，或者脚本未能自动找到设备，可以通过 `--serial` 参数指定序列号。

```bash
uv run yokogawa_pyvisa.py --serial 90Y701585 mean
```

**提示**: 脚本会自动处理序列号的格式（包括部分驱动显示的 Hex 格式序列号），你只需要输入设备背面标签上的原始序列号即可。

## 4. 故障排除

*   **找不到设备**: 
    *   运行 `lsusb` 检查系统是否识别到 Yokogawa 设备 (ID 通常包含 `0b21`)。
    *   确认是否已正确配置并生效了 udev 规则。
*   **UserWarning: TCPIP:instr resource discovery is limited...**:
    *   这是一个关于网络扫描的警告，如果你只使用 USB 连接，可以忽略。脚本已内置代码抑制此警告。
*   **VI_ERROR_NSUP_OPER**:
    *   这是 PyVISA-py 后端的一个已知兼容性行为，脚本内部已自动处理（回退使用 `*CLS`），不影响使用。
