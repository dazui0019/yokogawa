import argparse
import sys
import time
# 尝试从 tmctl_lib 子目录导入，如果失败则尝试直接导入 (兼容旧结构)
try:
    from tmctl_lib import tmctlLib
except ImportError:
    import tmctlLib
import os

# --- 默认配置 ---
# 如果不输入参数，默认使用的 USB 序列号
DEFAULT_USB_SERIAL = "90Y701585"
# 默认 IP (如果使用网口)
DEFAULT_IP = "192.168.1.100"

class ScopeController:
    def __init__(self, args):
        self.tmctl = tmctlLib.TMCTL()
        self.device_id = -1
        self.args = args

    def connect(self, quiet=False):
        """建立连接"""
        if not quiet:
            print("-" * 30)
        ret = -1
        try:
            if self.args.ip:
                # VXI-11 网口连接
                if not quiet:
                    print(f"连接方式: VXI-11 (IP: {self.args.ip})")
                ret, self.device_id = self.tmctl.Initialize(tmctlLib.TM_CTL_VXI11, self.args.ip)
            else:
                # USBTMC 连接
                serial = self.args.serial if self.args.serial else DEFAULT_USB_SERIAL
                if not quiet:
                    print(f"连接方式: USBTMC (Serial: {serial})")
                
                # 编码序列号
                ret, encode = self.tmctl.EncodeSerialNumber(128, serial)
                if ret == 0:
                    ret, self.device_id = self.tmctl.Initialize(tmctlLib.TM_CTL_USBTMC3, encode)
                else:
                    if not quiet:
                        print("Error: 序列号编码失败")
                    return False

            if ret != 0:
                if not quiet:
                    print(f"连接失败! Error Code: {ret}")
                return False

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
            except:
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
        return buf

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
            
            # 恢复运行
            if not is_clean:
                print("恢复示波器运行...")
            self.send(":STARt")
                
        except Exception as e:
            if not is_clean:
                print(f"读取出错: {e}")
            else:
                # 干净模式下出错可能需要输出特定值或者空，这里输出 Error 便于脚本捕获
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
            # 清除之前的错误信息
            self.send("*CLS")
            
            # 1. 暂停示波器 (Stop Acquisition)
            print("暂停示波器采集...")
            self.send(":STOP")
            # 确保 STOP 执行完成
            self.query("*OPC?") 
            
            print("发送截图指令...")
            self.send(":IMAGe:FORMat PNG")
            
            # 增加 *OPC? 检查，确保上面的设置指令执行完毕
            # 虽然 :IMAGe:SEND? 本身不需要 *OPC?，但加上可以确保状态机同步
            self.query("*OPC?") 
            
            self.send(":IMAGe:SEND?")
            
            # 获取数据头，得到图片总大小
            print("等待数据头...")
            ret, total_len = self.tmctl.ReceiveBlockHeader(self.device_id)
            if ret != 0:
                print(f"Error: 获取图像头信息失败 (Ret={ret})")
                return

            print(f"图像数据总大小: {total_len} bytes")
            
            if total_len == 0:
                print("Error: 接收到的图像数据长度为 0。请检查设备状态。")
                return

            print("开始接收数据体...")
            
            BLOCK_SIZE = 4096 # 增大缓冲区尝试提高效率

            loop_count = int(total_len / BLOCK_SIZE)
            remainder = total_len % BLOCK_SIZE
            received_total = 0
            
            with open(filename, "wb") as f:
                buf = bytearray(BLOCK_SIZE)
                
                # 1. 接收完整块
                for i in range(loop_count):
                    ret, rlen, end = self.tmctl.ReceiveBlockData(self.device_id, buf, BLOCK_SIZE)
                    if ret != 0:
                        raise Exception(f"接收数据块 {i} 失败 (Ret={ret})")
                    if rlen == 0:
                        print(f"Warning: 数据块 {i} 接收长度为 0")
                    f.write(buf[:rlen])
                    received_total += rlen
                    
                    # 简单的进度显示
                    if i % 10 == 0:
                        sys.stdout.write(f"\r进度: {received_total}/{total_len} bytes")
                        sys.stdout.flush()
                
                print("") # 换行
                    
                # 2. 接收剩余块
                if remainder > 0:
                    # 申请略大的 buffer 以防包含结束符
                    req_size = remainder + 16 
                    buf_rem = bytearray(req_size)
                    ret, rlen, end = self.tmctl.ReceiveBlockData(self.device_id, buf_rem, req_size)
                    if ret != 0:
                        raise Exception("接收剩余数据失败")
                    
                    # 只写入属于图像本身的数据长度
                    # 防止把通信结束符(LF)写进图片导致格式错误
                    bytes_to_write = min(rlen, total_len - received_total)
                    if bytes_to_write > 0:
                        f.write(buf_rem[:bytes_to_write])
                        received_total += bytes_to_write
            
            print(f"截图成功! 实际写入: {received_total} bytes. 已保存: {os.path.abspath(filename)}")
            
            # 恢复运行 (DLM 系列通常使用 :SSTart 指令启动采集)
            print("恢复示波器运行...")
            self.send(":STARt")

        except Exception as e:
            print(f"\n截图出错: {e}")
            # 尝试获取设备错误信息
            try:
                self.send(":STATus:ERRor?")
                ret, buf, length = self.tmctl.Receive(self.device_id, 1000)
                print(f"设备错误日志: {buf}")
            except:
                pass

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
    parser_mean.add_argument("-c", "--channel", type=int, default=1, help="通道号 (1-4, 默认 1)")
    parser_mean.add_argument("-v", "--verbose", action="store_true", help="详细输出模式 (显示日志和完整信息)")
    parser_mean.add_argument("--clean", action="store_true", help="[已废弃] 默认即为干净模式，保留此参数仅为兼容性")
    
    # 子命令: shot (截图)
    parser_shot = subparsers.add_parser("shot", help="获取屏幕截图")
    parser_shot.add_argument("-o", "--output", help="保存的文件名 (默认: 自动生成带时间戳的文件名)")
    
    # 解析参数
    args = parser.parse_args()
    
    # 执行逻辑
    controller = ScopeController(args)
    
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