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

#### 1. 读取平均值 (mean)

读取指定通道的平均值 (Mean)。

```bash
# 读取通道 1 (默认)
uv run yokogawa_pyvisa.py mean

# 读取通道 2
uv run yokogawa_pyvisa.py mean -c 2

# 干净输出模式 (仅输出数值，适合脚本调用)
uv run yokogawa_pyvisa.py mean -c 1 --clean
```

#### 2. 屏幕截图 (shot)

获取当前屏幕截图并保存为 PNG 文件。

```bash
# 默认保存为 DLM_年月日_时分秒.png
uv run yokogawa_pyvisa.py shot

# 指定文件名
uv run yokogawa_pyvisa.py shot -o my_scope_screen.png
```

#### 3. 列出可用设备 (list)

列出系统当前识别到的所有 VISA 设备资源（包括 USB 和 TCPIP 设备）。这对于查找设备的序列号或资源字符串非常有用。

```bash
uv run yokogawa_pyvisa.py list
```

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