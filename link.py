"""link.py — 硬件 ↔ 上位机的串口链路（核心基础设施）

位置：项目根目录（不在 tools/，因为它是基础设施而非辅助工具）
来源：原项目 smartcar/whalesbot/vehicle/base/serial_wrap.py
改动：
    - 去掉 logger、去掉 sys.path 体操、`__init__` 找不到设备直接 raise（不再死循环）
    - 变量名改全（self.dev → self.device, dev_list → devices, ctl_dev → controller）
未做：MC602 自动烧录恢复（Stage 7 接入 firmware_flash/flash.py）

为什么叫 link：
    - 不和 pyserial（也叫 serial）撞名 → 避免 self-import 死循环
    - 语义：硬件 ↔ 上位机的链路层
    - Stage 7 终态：whalesbot/link.py（在包内），现在先在根目录
"""

import time
from threading import Lock
from typing import List

import serial
from serial.tools import list_ports


# ---------------------------------------------------------------------------
# 全局串口指针（让 mc602_ctl2 协议层不依赖 sys.path 体操）
# ---------------------------------------------------------------------------

_current_serial: "SerialWrap | None" = None


def _set_current(ser: "SerialWrap") -> None:
    """SerialWrap 构造时调用，注册自己为当前串口。"""
    global _current_serial
    _current_serial = ser


def get_serial() -> "SerialWrap":
    """协议层调用：拿当前串口。必须先实例化 SerialWrap。

    仅供 _backup/mc602_ctl2.py 等历史协议层使用。
    新 driver 请用 DI（构造时传入 serial_obj），不要用这个。
    """
    if _current_serial is None:
        raise RuntimeError("未创建 SerialWrap 实例；请先 SerialWrap()")
    return _current_serial


# ---------------------------------------------------------------------------
# 控制器抽象
# ---------------------------------------------------------------------------

class CotrollerInfo:
    def __init__(self, baudrate, timeout=0.1, mode="USB"):
        self.baudrate = baudrate
        self.timeout = timeout
        self.connect_mode = mode
        self.name: str = None

    def send_cmd(self, cmd): pass
    def get_anwser(self, cmd): pass
    def ping_rx(self): pass
    def download_bin(self, obj): pass

    def __str__(self):
        return f"baudrate:{self.baudrate},timeout:{self.timeout},mode:{self.connect_mode}"


# ---------------------------------------------------------------------------
# SerialWrap — 串口主类
# ---------------------------------------------------------------------------

class SerialWrap(serial.Serial):
    def __init__(self):
        super().__init__(port=None, baudrate=115200, bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                         timeout=0.03, xonxoff=False, rtscts=False, dsrdtr=False)
        mc601 = MC601()
        mc602_usb = MC602()
        mc602_wireness = MC602Wireness()
        self.devices: List[CotrollerInfo] = [mc601, mc602_usb, mc602_wireness]
        self.device = None
        self.connect_flag = False
        self.lock = Lock()
        self.timeout = 0.01

        # 找设备；找不到直接 raise，不再死循环
        self.device = self.ping_port()
        if self.device is None:
            raise RuntimeError("未找到 MC602P 控制器（未接串口 / 未开机 / 协议不匹配）")
        print(f"port is {self.port}, controller is {self.device.name}, mode {self.device.connect_mode}")
        self.timeout = 0.1

        # 注册为当前串口，让 _backup/mc602_ctl2.py 协议层能拿
        _set_current(self)

    def get_anwser(self, cmd: bytes, time_out=0.1) -> bytes:
        self.lock.acquire()
        res = None
        try:
            self.reset_buffer()
            self.device.send_cmd(self, cmd)
            res = self.device.get_anwser(self)
        except Exception as e:
            print(f"get_anwser error: {e}")
        self.lock.release()
        return res

    def set_bps(self, bps):
        self.baudrate = bps

    def set_port(self, port):
        if self.connect_flag:
            self.close()
            self.connect_flag = False
        self.port = port

    def open(self):
        try:
            if self.port is None:
                return False
            self.connect_flag = True
            super().open()
            return True
        except Exception:
            self.connect_flag = False
            return False

    def get_serial_list(self):
        port_list = list_ports.comports()
        port_list = [p for p in port_list if "CH340" in p[1] or "USB" in p[1]]
        port_list.sort(key=lambda x: "CH340" not in x[1])
        return port_list

    def set_controller_serial(self, controller: CotrollerInfo):
        self.baudrate = controller.baudrate

    def ping_port(self):
        serial_list = self.get_serial_list()
        if not serial_list:
            print("未找到串口,查看是否插入了串口,或者查看下位机是否开机")
            return None
        for ser in serial_list:
            try:
                print(f"try: {ser}")
                self.set_port(ser[0])
                time.sleep(0.01)
                self.open()
                for controller in self.devices:
                    self.set_controller_serial(controller)
                    if controller.ping_rx(self):
                        return controller
                for controller in self.devices:
                    self.set_controller_serial(controller)
                    if controller.download_bin(self):
                        return controller
                self.close()
            except Exception as e:
                print(e)
        print("未找到支持的设备")
        return None

    def reset_buffer(self):
        self.reset_input_buffer()
        self.reset_output_buffer()

    def assert_device(self, name_test: str):
        name_device = self.device.name.lower()
        name_test = name_test.lower()
        if name_test in name_device or name_device in name_test:
            return True
        raise RuntimeError(f"device is not {name_test}")


# ---------------------------------------------------------------------------
# 各控制器协议
# ---------------------------------------------------------------------------

class MC601(CotrollerInfo):
    def __init__(self, baudrate=380400, timeout=0.1, mode="USB"):
        super().__init__(baudrate, timeout, mode)
        self.name = "mc601"
        self.header = bytes.fromhex("77 68")
        self.tail = bytes.fromhex("0A")

    def send_cmd(self, serial_obj: SerialWrap, cmd: bytes):
        serial_obj.write(cmd)

    def get_anwser(self, serial_obj: SerialWrap, time_out=0.05):
        time_start = time.time()
        res = serial_obj.read(3)
        if len(res) != 3:
            return None
        dst_len = res[2] + 7
        res = res + serial_obj.read(dst_len - 3)
        while True:
            if time.time() - time_start > time_out:
                return None
            if len(res) == dst_len:
                if res[0] == self.header[0] and res[-1] == self.tail[0]:
                    return res
                return None
            res = res + serial_obj.read(dst_len - len(res))

    def ping_rx(self, serial_obj: SerialWrap, time_out=0.05):
        time_start = time.time()
        while time.time() - time_start < time_out:
            serial_obj.reset_buffer()
            self.send_cmd(serial_obj, bytes.fromhex("77 68 04 00 01 CA 01 0A"))
            res = self.get_anwser(serial_obj, 0.03)
            if res is not None:
                self.send_cmd(serial_obj, bytes.fromhex("77 68 03 00 02 67 0A"))
                return True
        return False


class MC602(CotrollerInfo):
    def __init__(self, baudrate=1_000_000, timeout=0.1, mode="USB"):
        super().__init__(baudrate, timeout, mode)
        self.name = "mc602"
        self.header = bytes.fromhex("77 68")
        self.tail = bytes.fromhex("0A")

    def send_cmd(self, serial_obj: SerialWrap, cmd: bytes):
        cmd_len = (len(cmd) + 4).to_bytes(1, "big")
        cmd_all = self.header + cmd_len + cmd + self.tail
        serial_obj.write(cmd_all)

    def get_anwser(self, serial_obj: SerialWrap, time_out=0.2):
        time_start = time.time()
        res = serial_obj.read(3)
        if len(res) != 3:
            return None
        dst_len = res[2]
        res = res + serial_obj.read(dst_len - 3)
        while True:
            if time.time() - time_start > time_out:
                return None
            if len(res) == dst_len:
                if res[0] == self.header[0] and res[-1] == self.tail[0]:
                    return res[3:-1]
                return None
            res = res + serial_obj.read(dst_len - len(res))

    def ping_rx(self, serial_obj: SerialWrap, time_out=0.05):
        time_start = time.time()
        while time.time() - time_start < time_out:
            serial_obj.reset_buffer()
            self.send_cmd(serial_obj, bytes.fromhex("02 01 10"))
            res = self.get_anwser(serial_obj, 0.02)
            if res is not None:
                return True
        return False

    def download_bin(self, serial_obj: SerialWrap):
        """MC602P 在 bootloader 模式下的自动恢复。

        完全照搬原 _backup/serial_wrap.py:MC602.download_bin() 的 3 步流程：
        1. 发送 pydownload PING 检测 bootloader downloader
        2. 若已下载过 PROGRAM_GCC，发送 RUNCODE 直接跑现成的（**不重下**）
        3. RUN 失败或 ping 失败才调 flash_firmware() 下载并运行
        4. 最后用 MC602 USB ping 验证（不依赖 flash_firmware 的返回值）

        链路要求：
        - firmware.bin 必须存在于 tools/firmware_flash/ 目录下
        - 设备必须处于 bootloader downloader 模式（pydownload PING 有响应）
          → STM32 硬件 bootloader 时返回 False，提示用户断电重插
        """
        is_mc602 = False

        # 1. 检测 bootloader downloader 模式（pydownload 协议 PING）
        serial_obj.write(bytes.fromhex("55 AA 00 01 08 00 00 F7"))
        time.sleep(0.01)
        ret = serial_obj.read(10)
        if ret == bytes.fromhex("66 BB 01 01 0A 00 5A 02 00 76"):
            is_mc602 = True

            # 2. 尝试运行 PROGRAM_GCC (0x0800D000) —— 板子已烧过时直接可用
            start_time = time.time()
            while time.time() - start_time < 1:
                serial_obj.reset_buffer()
                serial_obj.write(bytes.fromhex("55 AA 00 40 0B 00 00 D0 00 08 DD"))
                time.sleep(0.01)
                ret = serial_obj.read(11)
                if ret == bytes.fromhex("66 BB 01 41 0B 00 00 D0 00 08 B9"):
                    break
            # 2a. RUN 成功 → 用 MC602 USB ping 验证（设备已在正常模式）
            if self.ping_rx(serial_obj, time_out=2):
                return True

        # 3. RUN 失败或 PING 失败 → 下载 firmware.bin → PROGRAM_GCC 并运行
        if is_mc602:
            port = serial_obj.port
            serial_obj.close()
            try:
                from tools.firmware_flash.flash import flash as flash_firmware
                flash_firmware(port, slot="debug", run=True)
            except Exception as e:
                print(f"flash 失败: {e}")
            try:
                serial_obj.open()
            except Exception as e:
                print(f"重新打开串口失败: {e}")
                return False
            # 3a. 最后兜底：正常 MC602 ping（**不检查 flash_firmware 的返回值**，
            #     flash_firmware 内部有 bug：RUN 成功后 slow PING 会失败返 False）
            return self.ping_rx(serial_obj, time_out=1.5)
        return False


class MC602Wireness(CotrollerInfo):
    def __init__(self, baudrate=115200, timeout=0.2, mode="Wireness"):
        super().__init__(baudrate, timeout, mode)
        self.name = "mc602_wireness"
        self.header = bytes.fromhex("FE")
        self.header_escape = bytes.fromhex("FE FC")
        self.tail = bytes.fromhex("FF")
        self.tail_escape = bytes.fromhex("FE FD")
        self.port_src = bytes.fromhex("90")
        self.port_dst = bytes.fromhex("91")
        self.target_id = bytes.fromhex("5D 3D")

    def set_target_id(self, target_id: bytes):
        self.target_id = target_id

    def send_cmd(self, serial_obj: SerialWrap, cmd: bytes):
        cmd_len = (len(cmd) + 4).to_bytes(1, "big")
        cmd_data = self.port_src + self.port_dst + self.target_id + cmd
        cmd_data_escape = cmd_data.replace(self.header, self.header_escape).replace(self.tail, self.tail_escape)
        cmd_all = self.header + cmd_len + cmd_data_escape + self.tail
        serial_obj.write(cmd_all)

    def get_anwser(self, serial_obj: SerialWrap, time_out=0.15):
        time_start = time.time()
        res = b""
        while True:
            if time.time() - time_start > time_out:
                print(f"get_anwser timeout {res.hex(' ')}")
                return None
            res = serial_obj.read(2)
            if len(res) == 2:
                break
        dst_len = res[1] + 3
        res = res + serial_obj.read(dst_len - 2)
        while True:
            if time.time() - time_start > time_out:
                return None
            res = res.replace(self.header_escape, self.header).replace(self.tail_escape, self.tail)
            rx_len = len(res)
            if rx_len == dst_len:
                if res[0] == self.header[0] and res[-1] == self.tail[0]:
                    return res[6:-1]
            res = res + serial_obj.read(dst_len - len(res))

    def ping_rx(self, serial_obj: SerialWrap, time_out=0.3):
        self.send_cmd(serial_obj, bytes.fromhex("02 01 10"))
        ret = self.get_anwser(serial_obj, time_out)
        if ret is not None:
            return True
        return False