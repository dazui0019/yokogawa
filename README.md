# Yokogawa 示波器控制工具

这是一个基于 Python 的命令行工具，用于控制 Yokogawa (横河) DLM 系列示波器。本项目包含两个针对不同操作系统的脚本版本。

## 脚本版本说明

本项目提供两个版本的控制脚本，请根据您的操作系统选择使用：

| 脚本文件 | 适用系统 | 依赖库 | 说明 |
| :--- | :--- | :--- | :--- |
| **`yokogawa.py`** | **Windows** | `tmctlLib`, `tmctl.dll` | 基于官方 DLL 开发，稳定支持 USBTMC 和 VXI-11。 |
| **`yokogawa_pyvisa.py`** | **Linux** | `pyvisa`, `pyvisa-py`, `pyusb` | 基于 PyVISA 开发，适用于 Linux 环境 (如 Ubuntu, CentOS)。 |

---

## 1. Windows 版本 (`yokogawa.py`)

### 环境要求

*   **uv** (推荐的 Python 包与环境管理器)
*   Python 3.x
*   `tmctlLib.py` (包含在项目目录中)
*   `tmctl.dll` (32-bit) 或 `tmctl64.dll` (64-bit) (需与 Python 位数匹配，并放在脚本同级目录或系统路径下)
*   Yokogawa USB 驱动 (如果使用 USB 连接)

### 使用方法

**指定 USB 序列号**：
如果不指定参数，默认使用内置的序列号。
```bash
uv run yokogawa.py --serial 90Y701585 mean
```

**指定 IP 地址 (网口)**：
```bash
uv run yokogawa.py --ip 192.168.1.100 shot
```

---

## 2. Linux 版本 (`yokogawa_pyvisa.py`)

### 环境要求

*   **uv** (推荐的 Python 包与环境管理器)
*   Python 3.x
*   依赖库：`pyvisa`, `pyvisa-py`, `pyusb`

### USB 权限配置 (必须)

Linux 默认不允许普通用户直接访问 USB 设备。你需要添加 udev 规则：

1. 创建规则文件（例如 `/etc/udev/rules.d/99-yokogawa.rules`）：
   ```bash
   # Yokogawa USBTMC devices (Vendor ID 0x0B21)
   SUBSYSTEM=="usb", ATTRS{idVendor}=="0b21", MODE="0666"
   ```

2. 重新加载规则并触发：
   ```bash
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

### 使用方法

命令格式与 Windows 版本基本一致，只是脚本文件名不同。

**读取 Mean 值**:
```bash
uv run yokogawa_pyvisa.py mean -c 1
```

**截图**:
```bash
uv run yokogawa_pyvisa.py shot -o screen.png
```

---

## 通用功能详解

以下命令适用于两个版本的脚本。

### 1. 读取平均值 (mean)

读取指定通道的 Mean (Average) 测量值。

**语法**：
```bash
# Windows
uv run yokogawa.py mean [-c CHANNEL] [-v/--verbose]
# Linux
uv run yokogawa_pyvisa.py mean [-c CHANNEL] [-v/--verbose]
```

**参数**：
*   `-c, --channel`: 通道号 (1-4)，默认为 1。
*   `-v, --verbose`: 详细输出模式。如果添加此参数，将显示连接日志、暂停/恢复提示以及完整的 "CHx Mean = ..." 格式结果。
*   **(默认行为)**: 默认为干净模式，仅输出数值结果（保留三位小数，单位为 **mA** 或 **mV**）或 `NaN`/`Error`，不显示任何其他日志。

**示例**：

```bash
# 默认模式：仅输出数值（推荐用于脚本集成）
uv run yokogawa.py mean -c 1
# 输出示例: 12500.000 (代表 12.5 A 或 12.5 V)

# 详细模式：显示过程日志
uv run yokogawa.py mean -c 2 -v
# 输出示例:
# ------------------------------
# 连接方式: USBTMC (Serial: 90Y701585)
# ...
# [结果] CH2 Mean = 12500.000 (mUnit)
# ...
```

### 2. 屏幕截图 (shot)

获取当前示波器屏幕画面并保存为 PNG 图片。执行过程中会自动暂停示波器，截图完成后恢复运行。

**语法**：
```bash
# Windows
uv run yokogawa.py shot [-o OUTPUT]
# Linux
uv run yokogawa_pyvisa.py shot [-o OUTPUT]
```

**参数**：
*   `-o, --output`: 指定保存的文件名。如果不指定，默认生成格式为 `DLM_YYYYMMDD_HHMMSS.png` 的文件。

## 常见问题

*   **Linux 下找不到 USB 设备**:
    *   请确保 `lsusb` 能看到设备（ID `0b21:xxxx`）。
    *   检查 udev 权限设置是否生效。
*   **VI_ERROR_NSUP_OPER (Linux)**:
    *   如果在连接或截图时遇到此错误，通常是因为 `pyvisa-py` 对某些设备的 Clear 操作支持不完全。脚本已内置兼容处理，通常可以忽略或会自动重试。
*   **连接失败 (Windows)**:
    *   检查 DLL 文件是否存在且与 Python 版本匹配。
    *   检查 USB 驱动是否安装。
