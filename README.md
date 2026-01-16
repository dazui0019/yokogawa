# Yokogawa 示波器控制工具

这是一个基于 Python 的命令行工具，用于控制 Yokogawa (横河) DLM 系列示波器。该脚本依赖于官方提供的 `tmctlLib.py` 及相应的 DLL 库文件。

## 功能特性

*   **多接口支持**：支持 USB (USBTMC) 和 网口 (VXI-11) 连接。
*   **读取测量值**：快速读取指定通道的平均值 (Mean)，支持纯数值输出模式（便于脚本集成）。
*   **屏幕截图**：一键获取当前示波器屏幕截图并保存为 PNG 文件。
*   **自动控制**：在执行读取或截图时，自动处理示波器的暂停 (`STOP`) 和恢复 (`START`)，确保数据一致性。

## 环境要求

*   **uv** (推荐的 Python 包与环境管理器)
*   Python 3.x (由 uv 自动管理)
*   `tmctlLib.py` (包含在项目目录中)
*   `tmctl.dll` (32-bit) 或 `tmctl64.dll` (64-bit) (需与 Python 位数匹配，并放在脚本同级目录或系统路径下)
*   Yokogawa USB 驱动 (如果使用 USB 连接)

## 使用方法

本项目使用 `uv` 进行环境管理和运行。请确保已安装 uv。

在终端或命令行中运行：

### 全局连接参数

如果不指定连接参数，脚本默认使用代码中配置的默认 USB 序列号。

*   **指定 USB 序列号**：
    ```bash
    uv run yokogawa.py --serial <序列号> [command]
    # 示例
    uv run yokogawa.py --serial 90Y701585 mean
    ```

*   **指定 IP 地址 (网口)**：
    ```bash
    uv run yokogawa.py --ip <IP地址> [command]
    # 示例
    uv run yokogawa.py --ip 192.168.1.100 shot
    ```

### 1. 读取平均值 (mean)

读取指定通道的 Mean (Average) 测量值。

**语法**：
```bash
uv run yokogawa.py mean [-c CHANNEL] [--clean]
```

**参数**：
*   `-c, --channel`: 通道号 (1-4)，默认为 1。
*   `--clean`: 干净模式。仅输出数值结果（保留两位小数）或 `NaN`/`Error`，不显示连接日志和其他提示信息。非常适合被其他脚本调用。

**示例**：

```bash
# 读取通道 1 的值（带日志）
uv run yokogawa.py mean -c 1

# 仅获取通道 2 的数值（无日志）
uv run yokogawa.py mean -c 2 --clean
# 输出示例: 12.50
```

### 2. 屏幕截图 (shot)

获取当前示波器屏幕画面并保存为 PNG 图片。执行过程中会自动暂停示波器，截图完成后恢复运行。

**语法**：
```bash
uv run yokogawa.py shot [-o OUTPUT]
```

**参数**：
*   `-o, --output`: 指定保存的文件名。如果不指定，默认生成格式为 `DLM_YYYYMMDD_HHMMSS.png` 的文件。

**示例**：

```bash
# 默认文件名截图
uv run yokogawa.py shot

# 指定文件名
uv run yokogawa.py shot -o my_waveform.png
```

## 常见问题

*   **连接失败**：
    *   检查 USB 线或网线是否连接正常。
    *   检查示波器设置中的接口配置是否正确（USBTMC 或 VXI-11）。
    *   确认 DLL 文件是否存在且与 Python 版本（32/64位）匹配。
*   **截图 0KB 或 Timeout**：
    *   截图数据量较大，脚本已内置较长的超时时间。如果仍然超时，请检查网络状况。
    *   确保示波器未处于无法响应的死锁状态。