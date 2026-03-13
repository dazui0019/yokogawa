import argparse
import sys
import time
import os

try:
    import pyvisa
except ImportError:
    print("请先安装 pyvisa: pip install pyvisa pyvisa-py pyusb")
    sys.exit(1)

# --- 默认配置 ---
# 如果不输入参数，默认使用的 USB 序列号
DEFAULT_USB_SERIAL = "90Y701585"


def _dedupe_channels(channels):
    unique_channels = []
    for channel in channels:
        if channel not in unique_channels:
            unique_channels.append(channel)
    return unique_channels


def _parse_channel_values(values):
    channels = []
    for value in values:
        for part in str(value).split(","):
            part = part.strip()
            if not part:
                raise ValueError("channel argument cannot be empty")

            try:
                channel = int(part)
            except ValueError as exc:
                raise ValueError(f"invalid channel: {part}") from exc

            if channel not in (1, 2, 3, 4):
                raise ValueError(f"channel out of range: {channel} (supported: 1-4)")

            channels.append(channel)

    return _dedupe_channels(channels)


class ChannelListAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            parsed_channels = _parse_channel_values(values)
        except ValueError as exc:
            parser.error(str(exc))

        current_channels = getattr(namespace, self.dest, None) or []
        setattr(namespace, self.dest, _dedupe_channels(current_channels + parsed_channels))

class ScopeController:
    def __init__(self, args):
        self.rm = pyvisa.ResourceManager()
        self.inst = None
        self.args = args

    def connect(self, quiet=False):
        """建立连接"""
        if not quiet:
            print("-" * 30)
        
        resource_name = None
        
        try:
            if self.args.ip:
                # VXI-11 网口连接
                if not quiet:
                    print(f"连接方式: VXI-11 (IP: {self.args.ip})")
                # TCPIP 资源字符串格式: TCPIP::<ip>::INSTR
                resource_name = f"TCPIP::{self.args.ip}::INSTR"
            else:
                # USBTMC 连接
                serial = self.args.serial if self.args.serial else DEFAULT_USB_SERIAL
                if not quiet:
                    print(f"连接方式: USBTMC (Serial: {serial})")
                
                # 搜索 USB 设备
                # 格式通常为 USB0::0x0B21::<PID>::<SERIAL>::INSTR
                # 我们通过序列号匹配
                try:
                    resources = self.rm.list_resources()
                except Exception:
                    resources = []
                
                # 尝试找到匹配序列号的 USB 资源
                # 有些系统/驱动会将序列号显示为 Hex 字符串
                # 例如 90Y701585 -> 393059373031353835
                hex_serial = "".join("{:02X}".format(ord(c)) for c in serial)
                
                for res in resources:
                    if "USB" not in res:
                        continue
                        
                    # 1. 直接匹配
                    if serial in res:
                        resource_name = res
                        break
                    
                    # 2. 匹配 Hex 编码
                    if hex_serial in res:
                        resource_name = res
                        break
                
                if not resource_name:
                    if not quiet:
                        print(f"Error: 未找到序列号为 {serial} 的 USB 设备")
                        print(f"当前可用设备: {resources}")
                    return False

            if not quiet:
                print(f"正在打开资源: {resource_name}")
            
            self.inst = self.rm.open_resource(resource_name)
            
            # 基础通信设置
            self.inst.read_termination = '\n'
            self.inst.write_termination = '\n'
            self.inst.timeout = 30000 # 30秒 (pyvisa 单位是 ms)
            
            # 清除状态
            # 横河设备不支持 clear() (viClear)，直接使用 *CLS
            try:
                self.inst.write("*CLS")
            except Exception:
                pass
            
            if not quiet:
                print("连接成功!")
                # 查询 IDN 确认设备
                try:
                    idn = self.inst.query("*IDN?")
                    print(f"设备信息: {idn.strip()}")
                except Exception:
                    pass
                    
            return True

        except Exception as e:
            if not quiet:
                print(f"连接异常: {e}")
            return False

    def close(self, quiet=False):
        """断开连接"""
        if self.inst:
            if not quiet:
                print("正在断开连接...")
            try:
                # 关闭连接
                self.inst.close()
            except Exception:
                pass
            self.inst = None
            if not quiet:
                print("-" * 30)

    def send(self, cmd):
        """发送指令"""
        try:
            self.inst.write(cmd)
        except Exception as e:
            raise Exception(f"指令发送失败: '{cmd}' ({e})")

    def query(self, cmd):
        """查询指令"""
        try:
            return self.inst.query(cmd).strip()
        except Exception as e:
            raise Exception(f"接收数据失败: '{cmd}' ({e})")

    def cmd_list_devices(self):
        """列出所有可用 VISA 设备"""
        print("-" * 30)
        print("正在搜索可用 VISA 设备...")
        try:
            resources = self.rm.list_resources()
            if not resources:
                print("未找到任何设备。")
            else:
                print(f"共找到 {len(resources)} 个设备:")
                for i, res in enumerate(resources):
                    print(f"  {i+1}. {res}")
                    # 尝试获取设备 ID 信息
                    try:
                        with self.rm.open_resource(res) as temp_inst:
                            temp_inst.timeout = 200  # 短超时
                            idn = temp_inst.query("*IDN?")
                            print(f"     -> {idn.strip()}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"搜索出错: {e}")
        print("-" * 30)

    def cmd_get_mean(self):
        """获取 Mean 值逻辑"""
        channel = self.args.channel
        # 默认开启 clean 模式，除非指定了 --verbose
        is_clean = not self.args.verbose
        success = False

        if not is_clean:
            print(f"正在读取 Channel {channel} 的 Mean 值...")

        try:
            self.send(":COMMunicate:HEADer OFF")

            # 查询结果
            val_str = self.query(f":MEASure:CHANnel{channel}:AVERage:VALue?")

            try:
                # 转换为毫伏/毫安 (x1000)
                val = float(val_str) * 1000.0
                if is_clean:
                    print(f"{val:.3f}")
                else:
                    print(f"\n[结果] CH{channel} Mean = {val:.3f} (mUnit)")
            except ValueError:
                if is_clean:
                    print("NaN")
                else:
                    print(f"\n[结果] CH{channel} Mean = {val_str} (非数值)")
            success = True

        except Exception as e:
            if not is_clean:
                print(f"读取出错: {e}")
            else:
                print("Error")

        return success

    def cmd_channel_set(self):
        """Set channel display state."""
        channels = self.args.channel or [1]
        state = self.args.state

        try:
            self.send(":COMMunicate:HEADer OFF")
            channel_text = ", ".join(f"CH{channel}" for channel in channels)

            if state == "on":
                print(f"Turning on {channel_text}...")
                for channel in channels:
                    self.send(f":CHANnel{channel}:DISPlay ON")
                self.query("*OPC?")
                print(f"{channel_text} enabled.")
            else:
                print(f"Turning off {channel_text}...")
                for channel in channels:
                    self.send(f":CHANnel{channel}:DISPlay OFF")
                self.query("*OPC?")
                print(f"{channel_text} disabled.")

            return True
        except Exception as e:
            print(f"Failed to set channel state: {e}")
            return False

    def cmd_get_screenshot(self):
        """截图逻辑"""
        filename = self.args.output
        if not filename:
            # 默认文件名: DLM_年月日_时分秒.png
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"DLM_{timestamp}.png"

        output_path = os.path.abspath(filename)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        print(f"正在获取截图，目标文件: '{filename}'")

        success = False
        stopped = False

        try:
            try:
                self.inst.clear()
            except Exception as e:
                # 忽略不支持的操作错误，尝试使用指令清除
                print(f"Warning: 设备不支持 clear() 操作 ({e})，尝试使用 *CLS")
                try:
                    self.inst.write("*CLS")
                except Exception:
                    pass

            print("暂停示波器采集...")
            self.send(":STOP")
            self.query("*OPC?")
            stopped = True

            print("发送截图指令...")
            self.send(":IMAGe:FORMat PNG")
            self.query("*OPC?")

            print("正在接收图像数据...")
            self.inst.write(":IMAGe:SEND?")

            # 读取二进制数据时，暂时关闭结束符处理，防止数据被意外截断
            old_term = self.inst.read_termination
            self.inst.read_termination = None

            raw_data = bytearray()
            header_len = 0
            data_len = 0

            try:
                # 1. 读取第一块数据
                chunk = self.inst.read_raw()
                raw_data.extend(chunk)

                # 2. 解析 IEEE 488.2 Block Header (#NXXXX...Data...)
                if len(raw_data) > 2 and raw_data[0:1] == b'#':
                    try:
                        # N 是位数
                        digits = int(chr(raw_data[1]))
                        # XXXX 是长度
                        if len(raw_data) >= 2 + digits:
                            data_len = int(raw_data[2:2+digits])
                            header_len = 2 + digits

                            total_expected = header_len + data_len
                            print(f"图像大小: {data_len} bytes, 正在接收剩余数据...")

                            # 3. 循环读取直到读够数据
                            while len(raw_data) < total_expected:
                                try:
                                    # 继续读取
                                    new_chunk = self.inst.read_raw()
                                    if len(new_chunk) == 0:
                                        raise Exception("读取到空数据块，通信可能中断")
                                    raw_data.extend(new_chunk)
                                except Exception as read_err:
                                    raise Exception(f"读取中断: {read_err}")
                        else:
                            raise Exception("数据头不完整，无法解析图像长度")
                    except ValueError:
                        raise Exception("解析数据头长度失败")
                else:
                    raise Exception("未检测到标准数据头 #")

            except Exception as e:
                raise Exception(f"读取数据发生异常: {e}")

            finally:
                self.inst.read_termination = old_term

            # 截取有效数据
            image_data = raw_data
            if header_len > 0 and data_len > 0:
                image_data = raw_data[header_len : header_len + data_len]

                if len(image_data) < data_len:
                    raise Exception(f"接收数据不完整 ({len(image_data)}/{data_len})")

            print(f"实际获取数据大小: {len(image_data)} bytes")

            with open(filename, "wb") as f:
                f.write(image_data)

            print(f"截图成功! 已保存: {output_path}")
            success = True

        except Exception as e:
            print(f"\n截图出错: {e}")
            try:
                err = self.query(":STATus:ERRor?")
                print(f"设备错误日志: {err}")
            except Exception:
                pass
        finally:
            if stopped:
                print("恢复示波器运行...")
                try:
                    self.send(":STARt")
                except Exception as e:
                    success = False
                    print(f"恢复运行失败: {e}")

        return success

def main():
    parser = argparse.ArgumentParser(description="Yokogawa 示波器控制工具 (Cross-Platform)")

    parser.add_argument("--serial", help="指定 USB 序列号 (默认使用内置默认值)", default=None)
    parser.add_argument("--ip", help="指定 IP 地址 (若设置则优先使用网口 VXI-11)", default=None)

    subparsers = parser.add_subparsers(dest="command", required=True, help="请选择要执行的操作")

    # 子命令: mean
    parser_mean = subparsers.add_parser("mean", help="读取指定通道的 Mean 值")
    parser_mean.add_argument("-c", "--channel", type=int, choices=[1, 2, 3, 4], default=1, help="通道号 (1-4, 默认 1)")
    parser_mean.add_argument("-v", "--verbose", action="store_true", help="详细输出模式 (显示日志和完整信息)")
    parser_mean.add_argument("--clean", action="store_true", help="[已废弃] 默认即为干净模式，保留此参数仅为兼容性")

    # 子命令: channel (通道开关，兼容 channel-on 别名)
    parser_channel = subparsers.add_parser("channel", aliases=["channel-on"], help="Set channel display on/off (panel-like by default)")
    parser_channel.add_argument("state", nargs="?", default="on", choices=["on", "off"], help="通道状态: on 开启, off 关闭 (默认: on)")
    parser_channel.add_argument(
        "-c",
        "--channel",
        nargs="+",
        action=ChannelListAction,
        default=None,
        help="Channel number(s) (1-4, default: 1). Supports multiple values, e.g. -c 1 2 or -c 1,2,4",
    )

    # 子命令: shot
    parser_shot = subparsers.add_parser("shot", help="获取屏幕截图")
    parser_shot.add_argument("-o", "--output", help="保存的文件名 (默认: 自动生成带时间戳的文件名)")

    # 子命令: list
    subparsers.add_parser("list", help="列出所有可用 VISA 设备")

    args = parser.parse_args()

    controller = ScopeController(args)

    if args.command == "list":
        controller.cmd_list_devices()
        return 0

    # mean 命令默认 quiet (clean)，除非 verbose
    # shot 命令默认 verbose (不 quiet)
    quiet_mode = False
    if args.command == "mean":
        quiet_mode = not args.verbose

    if not controller.connect(quiet=quiet_mode):
        if args.command == "mean" and quiet_mode:
            print("Error")
        else:
            print("连接失败。")
        return 1

    op_ok = False
    try:
        if args.command == "mean":
            op_ok = controller.cmd_get_mean()
        elif args.command in ("channel", "channel-on"):
            op_ok = controller.cmd_channel_set()
        elif args.command == "shot":
            op_ok = controller.cmd_get_screenshot()
    finally:
        controller.close(quiet=quiet_mode)

    return 0 if op_ok else 1

if __name__ == "__main__":
    sys.exit(main())
