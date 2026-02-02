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
# 默认 IP (如果使用网口)
DEFAULT_IP = "192.168.1.100"

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
            except:
                pass
            
            if not quiet:
                print("连接成功!")
                # 查询 IDN 确认设备
                try:
                    idn = self.inst.query("*IDN?")
                    print(f"设备信息: {idn.strip()}")
                except:
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
            except:
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
                    except:
                        pass
        except Exception as e:
            print(f"搜索出错: {e}")
        print("-" * 30)

    def cmd_get_mean(self):
        """获取 Mean 值逻辑"""
        channel = self.args.channel
        # 默认开启 clean 模式，除非指定了 --verbose
        is_clean = not self.args.verbose
        
        if not is_clean:
            print(f"正在读取 Channel {channel} 的 Mean 值...")
        
        try:
            # 1. 暂停示波器
            if not is_clean:
                print("暂停示波器采集...")
            self.send(":STOP")
            self.query("*OPC?")

            self.send(":COMMunicate:HEADer OFF")
            
            # 开启测量
            self.send(f":MEASure:CHANnel{channel}:AVERage:STATe ON")
            self.send(":MEASure:MODE ON")
            
            # 查询结果
            val_str = self.query(f":MEASure:CHANnel{channel}:AVERage:VALue?")
            
            try:
                val = float(val_str)
                if is_clean:
                    print(f"{val:.2f}")
                else:
                    print(f"\n[结果] CH{channel} Mean = {val:.2f}")
            except ValueError:
                if is_clean:
                    print("NaN")
                else:
                    print(f"\n[结果] CH{channel} Mean = {val_str} (非数值)")
            
            # 恢复运行
            if not is_clean:
                print("恢复示波器运行...")
            self.send(":STARt")
                
        except Exception as e:
            if not is_clean:
                print(f"读取出错: {e}")
            else:
                print("Error")

    def cmd_get_screenshot(self):
        """截图逻辑"""
        filename = self.args.output
        if not filename:
            # 默认文件名: DLM_年月日_时分秒.png
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"DLM_{timestamp}.png"
            
        print(f"正在获取截图，目标文件: '{filename}'")
        
        try:
            try:
                self.inst.clear()
            except Exception as e:
                # 忽略不支持的操作错误，尝试使用指令清除
                print(f"Warning: 设备不支持 clear() 操作 ({e})，尝试使用 *CLS")
                try:
                    self.inst.write("*CLS")
                except:
                    pass
            
            print("暂停示波器采集...")
            self.send(":STOP")
            self.query("*OPC?") 
            
            print("发送截图指令...")
            self.send(":IMAGe:FORMat PNG")
            self.query("*OPC?") 
            
            print("正在接收图像数据...")
            self.inst.write(":IMAGe:SEND?")
            
            # 读取二进制数据时，暂时关闭结束符处理，防止数据被意外截断
            old_term = self.inst.read_termination
            self.inst.read_termination = None
            
            raw_data = bytearray()
            
            try:
                # 1. 读取第一块数据
                chunk = self.inst.read_raw()
                raw_data.extend(chunk)
                
                # 2. 解析 IEEE 488.2 Block Header (#NXXXX...Data...)
                header_len = 0
                data_len = 0
                
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
                                        break
                                    raw_data.extend(new_chunk)
                                    # 简单的进度提示
                                    # sys.stdout.write(f"\r已接收: {len(raw_data)}/{total_expected}")
                                    # sys.stdout.flush()
                                except Exception as read_err:
                                    print(f"读取中断: {read_err}")
                                    break
                                    
                            # print("") # 换行
                    except ValueError:
                        print("Warning: 解析数据头长度失败")
                else:
                    print("Warning: 未检测到标准数据头 #")

            except Exception as e:
                print(f"读取数据发生异常: {e}")

            finally:
                self.inst.read_termination = old_term
            
            # 截取有效数据
            image_data = raw_data
            if header_len > 0 and data_len > 0:
                image_data = raw_data[header_len : header_len + data_len]
                
                if len(image_data) < data_len:
                    print(f"Warning: 接收数据不完整 ({len(image_data)}/{data_len})")
            
            print(f"实际获取数据大小: {len(image_data)} bytes")
            
            with open(filename, "wb") as f:
                f.write(image_data)
            
            print(f"截图成功! 已保存: {os.path.abspath(filename)}")
            
            print("恢复示波器运行...")
            self.send(":STARt")

        except Exception as e:
            print(f"\n截图出错: {e}")
            try:
                err = self.query(":STATus:ERRor?")
                print(f"设备错误日志: {err}")
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description="Yokogawa 示波器控制工具 (Cross-Platform)")
    
    parser.add_argument("--serial", help="指定 USB 序列号 (默认使用内置默认值)", default=None)
    parser.add_argument("--ip", help="指定 IP 地址 (若设置则优先使用网口 VXI-11)", default=None)
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="请选择要执行的操作")
    
    # 子命令: mean
    parser_mean = subparsers.add_parser("mean", help="读取指定通道的 Mean 值")
    parser_mean.add_argument("-c", "--channel", type=int, default=1, help="通道号 (1-4, 默认 1)")
    parser_mean.add_argument("-v", "--verbose", action="store_true", help="详细输出模式 (显示日志和完整信息)")
    parser_mean.add_argument("--clean", action="store_true", help="[已废弃] 默认即为干净模式，保留此参数仅为兼容性")
    
    # 子命令: shot
    parser_shot = subparsers.add_parser("shot", help="获取屏幕截图")
    parser_shot.add_argument("-o", "--output", help="保存的文件名 (默认: 自动生成带时间戳的文件名)")

    # 子命令: list
    subparsers.add_parser("list", help="列出所有可用 VISA 设备")
    
    args = parser.parse_args()
    
    controller = ScopeController(args)
    
    if args.command == "list":
        controller.cmd_list_devices()
        return

    # mean 命令默认 quiet (clean)，除非 verbose
    # shot 命令默认 verbose (不 quiet)
    quiet_mode = False
    if args.command == 'mean':
        quiet_mode = not args.verbose
    
    if controller.connect(quiet=quiet_mode):
        if args.command == "mean":
            controller.cmd_get_mean()
        elif args.command == "shot":
            controller.cmd_get_screenshot()
        
        controller.close(quiet=quiet_mode)

if __name__ == "__main__":
    main()