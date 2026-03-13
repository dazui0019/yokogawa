import argparse
import sys
import time
import os

# 尝试从 tmctl_lib 子目录导入，如果失败则尝试直接导入 (兼容旧结构)
try:
    from tmctl_lib import tmctlLib
except ImportError:
    import tmctlLib

# --- 默认配置 ---
# 如果不输入参数，默认使用的 USB 序列号
DEFAULT_USB_SERIAL = "90Y701585"
ALL_CHANNELS = [1, 2, 3, 4]


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
                raise ValueError("通道参数不能为空")

            try:
                channel = int(part)
            except ValueError as exc:
                raise ValueError(f"无效通道: {part}") from exc

            if channel not in ALL_CHANNELS:
                raise ValueError(f"通道号超出范围: {channel} (仅支持 1-4)")

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
        self.tmctl = tmctlLib.TMCTL()
        self.device_id = -1
        self.args = args

    def connect(self, quiet=False):
        """建立连接"""
        if not quiet:
            print("-" * 30)

        try:
            if self.args.ip:
                # VXI-11 网口连接
                if not quiet:
                    print(f"连接方式: VXI-11 (IP: {self.args.ip})")
                _, self.device_id = self.tmctl.Initialize(tmctlLib.TM_CTL_VXI11, self.args.ip)
            else:
                # USBTMC 连接
                serial = self.args.serial if self.args.serial else DEFAULT_USB_SERIAL
                if not quiet:
                    print(f"连接方式: USBTMC (Serial: {serial})")

                # 编码序列号
                _, encode = self.tmctl.EncodeSerialNumber(128, serial)
                _, self.device_id = self.tmctl.Initialize(tmctlLib.TM_CTL_USBTMC3, encode)

            # 基础通信设置
            self.tmctl.SetTerm(self.device_id, 2, 1)  # 接收/发送结束符设为 LF
            self.tmctl.SetRen(self.device_id, 1)      # 开启远程控制模式
            self.tmctl.SetTimeout(self.device_id, 300) # 设置超时时间为 30秒 (单位 100ms)，截图可能较慢
            self.tmctl.DeviceClear(self.device_id)    # 清除设备状态
            if not quiet:
                print("连接成功!")
            return True

        except Exception as e:
            if not quiet:
                print(f"连接异常: {e}")
            return False

    def close(self, quiet=False):
        """断开连接"""
        if self.device_id >= 0:
            if not quiet:
                print("正在断开连接...")
            try:
                self.tmctl.SetRen(self.device_id, 0) # 恢复本地控制
                self.tmctl.Finish(self.device_id)
            except Exception:
                pass
            self.device_id = -1
            if not quiet:
                print("-" * 30)

    def send(self, cmd):
        """发送指令"""
        ret = self.tmctl.Send(self.device_id, cmd)
        if ret != 0:
            raise Exception(f"指令发送失败: '{cmd}' (Ret={ret})")

    def query(self, cmd, buf_size=1000):
        """查询指令 (发送 + 接收)"""
        self.send(cmd)
        ret, buf, length = self.tmctl.Receive(self.device_id, buf_size)
        if ret != 0:
            raise Exception(f"接收数据失败: '{cmd}' (Ret={ret})")
        return buf.strip()

    def _cmd_get_measurement(self, measurement_name, scpi_parameter):
        """获取标量测量值逻辑"""
        channel = self.args.channel
        # 默认开启 clean 模式，除非指定了 --verbose
        is_clean = not self.args.verbose
        success = False

        if not is_clean:
            print(f"正在读取 Channel {channel} 的 {measurement_name} 值...")

        try:
            self.send(":COMMunicate:HEADer OFF")

            # 查询结果
            val_str = self.query(f":MEASure:CHANnel{channel}:{scpi_parameter}:VALue?")

            try:
                # 转换为毫伏/毫安 (x1000)
                val = float(val_str) * 1000.0
                if is_clean:
                    print(f"{val:.3f}")
                else:
                    print(f"\n[结果] CH{channel} {measurement_name} = {val:.3f} (mUnit)")
            except ValueError:
                if is_clean:
                    print("NaN")
                else:
                    print(f"\n[结果] CH{channel} {measurement_name} = {val_str} (非数值)")
            success = True

        except Exception as e:
            if not is_clean:
                print(f"读取出错: {e}")
            else:
                # 干净模式下出错可能需要输出特定值或者空，这里输出 Error 便于脚本捕获
                print("Error")

        return success

    def cmd_get_mean(self):
        """获取 Mean 值逻辑"""
        return self._cmd_get_measurement("Mean", "AVERage")

    def cmd_get_rms(self):
        """获取 RMS 值逻辑"""
        return self._cmd_get_measurement("RMS", "RMS")

    def cmd_channel_set(self):
        """Set channel display state."""
        channels = ALL_CHANNELS if self.args.all_channels else (self.args.channel or [1])
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
            # 清除之前的错误信息
            self.send("*CLS")

            # 1. 暂停示波器 (Stop Acquisition)
            print("暂停示波器采集...")
            self.send(":STOP")
            # 确保 STOP 执行完成
            self.query("*OPC?")
            stopped = True

            print("发送截图指令...")
            self.send(":IMAGe:FORMat PNG")

            # 增加 *OPC? 检查，确保上面的设置指令执行完毕
            # 虽然 :IMAGe:SEND? 本身不需要 *OPC?，但加上可以确保状态机同步
            self.query("*OPC?")

            self.send(":IMAGe:SEND?")

            # 获取数据头，得到图片总大小
            print("等待数据头...")
            _, total_len = self.tmctl.ReceiveBlockHeader(self.device_id)

            print(f"图像数据总大小: {total_len} bytes")

            if total_len == 0:
                raise Exception("接收到的图像数据长度为 0。请检查设备状态。")

            print("开始接收数据体...")

            block_size = 4096
            received_total = 0
            chunk_index = 0

            with open(filename, "wb") as f:
                while received_total < total_len:
                    remaining = total_len - received_total
                    # 末尾多申请 1 字节，兼容设备附带的块结束符。
                    req_size = min(block_size, remaining + 1)
                    buf = bytearray(req_size)
                    _, rlen, _ = self.tmctl.ReceiveBlockData(self.device_id, buf, req_size)

                    if rlen == 0:
                        raise Exception("接收到 0 字节，通信可能中断")

                    bytes_to_write = min(rlen, remaining)
                    f.write(buf[:bytes_to_write])
                    received_total += bytes_to_write
                    chunk_index += 1

                    if chunk_index % 10 == 0 or received_total == total_len:
                        sys.stdout.write(f"\r进度: {received_total}/{total_len} bytes")
                        sys.stdout.flush()
                print("")

            if received_total != total_len:
                raise Exception(f"图像数据不完整: {received_total}/{total_len} bytes")

            print(f"截图成功! 实际写入: {received_total} bytes. 已保存: {output_path}")
            success = True

        except Exception as e:
            print(f"\n截图出错: {e}")
            # 尝试获取设备错误信息
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
    # 定义命令行参数
    parser = argparse.ArgumentParser(description="Yokogawa 示波器控制工具")

    # 全局参数：连接设置
    parser.add_argument("--serial", help="指定 USB 序列号 (默认使用内置默认值)", default=None)
    parser.add_argument("--ip", help="指定 IP 地址 (若设置则优先使用网口 VXI-11)", default=None)

    # 子命令集
    subparsers = parser.add_subparsers(dest="command", required=True, help="请选择要执行的操作")

    # 子命令: mean (读取平均值)
    parser_mean = subparsers.add_parser("mean", help="读取指定通道的 Mean 值")
    parser_mean.add_argument("-c", "--channel", type=int, choices=[1, 2, 3, 4], default=1, help="通道号 (1-4, 默认 1)")
    parser_mean.add_argument("-v", "--verbose", action="store_true", help="详细输出模式 (显示日志和完整信息)")
    parser_mean.add_argument("--clean", action="store_true", help="[已废弃] 默认即为干净模式，保留此参数仅为兼容性")

    # 子命令: rms (读取有效值)
    parser_rms = subparsers.add_parser("rms", help="读取指定通道的 RMS 值")
    parser_rms.add_argument("-c", "--channel", type=int, choices=[1, 2, 3, 4], default=1, help="通道号 (1-4, 默认 1)")
    parser_rms.add_argument("-v", "--verbose", action="store_true", help="详细输出模式 (显示日志和完整信息)")
    parser_rms.add_argument("--clean", action="store_true", help="[已废弃] 默认即为干净模式，保留此参数仅为兼容性")

    # 子命令: channel (通道开关，兼容 channel-on 别名)
    parser_channel = subparsers.add_parser("channel", aliases=["channel-on"], help="Set channel display on/off (panel-like by default)")
    parser_channel.add_argument("state", nargs="?", default="on", choices=["on", "off"], help="通道状态: on 开启, off 关闭 (默认: on)")
    channel_target_group = parser_channel.add_mutually_exclusive_group()
    channel_target_group.add_argument(
        "-c",
        "--channel",
        nargs="+",
        action=ChannelListAction,
        default=None,
        help="Channel number(s) (1-4, default: 1). Supports multiple values, e.g. -c 1 2 or -c 1,2,4",
    )
    channel_target_group.add_argument(
        "-a",
        "--all",
        dest="all_channels",
        action="store_true",
        help="选择所有通道 (CH1-CH4)",
    )

    # 子命令: shot (截图)
    parser_shot = subparsers.add_parser("shot", help="获取屏幕截图")
    parser_shot.add_argument("-o", "--output", help="保存的文件名 (默认: 自动生成带时间戳的文件名)")

    # 解析参数
    args = parser.parse_args()

    # 执行逻辑
    controller = ScopeController(args)

    # mean/rms 命令默认 quiet (clean)，除非 verbose
    # shot 命令默认 verbose (不 quiet)
    quiet_mode = False
    if args.command in ("mean", "rms"):
        quiet_mode = not args.verbose

    if not controller.connect(quiet=quiet_mode):
        if args.command in ("mean", "rms") and quiet_mode:
            print("Error")
        else:
            print("连接失败。")
        return 1

    op_ok = False
    try:
        if args.command == "mean":
            op_ok = controller.cmd_get_mean()
        elif args.command == "rms":
            op_ok = controller.cmd_get_rms()
        elif args.command in ("channel", "channel-on"):
            op_ok = controller.cmd_channel_set()
        elif args.command == "shot":
            op_ok = controller.cmd_get_screenshot()
    finally:
        controller.close(quiet=quiet_mode)

    return 0 if op_ok else 1

if __name__ == "__main__":
    sys.exit(main())
