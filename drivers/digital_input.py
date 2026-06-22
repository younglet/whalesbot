"""drivers/digital_input.py — 数字输入 driver

基于模拟输入 (AnalogInput) 实现，通过阈值判断高低电平。

用法:
    python -m drivers.digital_input        # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.digital_input import DigitalInput
        serial_obj = SerialWrap()
        di = DigitalInput(serial_obj, port=1)
        if di.read():                       # True=高电平, False=低电平
            print("高电平")

阈值默认 2048（12-bit ADC 中位），可根据实际电压调整。
"""

# Path bootstrap
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
import struct


# ---------------------------------------------------------------------------
# 协议常量
# ---------------------------------------------------------------------------

_DEVICE_ID_AI1 = 0x07    # 水晶头
_DEVICE_ID_AI2 = 0x08    # 杜邦头


# ---------------------------------------------------------------------------
# DigitalInput
# ---------------------------------------------------------------------------

class DigitalInput:
    """数字输入。

    基于模拟输入读取电压值，通过阈值判断高低电平。
    与 AnalogInput 共用同一物理端口。
    """

    def __init__(self, serial, port=1, port_type="rj45", threshold=2048):
        """Args:
            serial:    SerialWrap 实例
            port:      端口号（rj45: 1~6, dupont: 1~3）
            port_type: "rj45"（水晶头）或 "dupont"（杜邦头）
            threshold: 阈值，>= 此值视为高电平，默认 2048
        """
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"digital_input 仅支持 MC602，当前设备 {serial.device.name}")
        if port_type not in ("rj45", "dupont"):
            raise ValueError(f"port_type 必须是 'rj45' 或 'dupont'，收到 '{port_type}'")
        self._serial = serial
        self._port = port
        self._dev_id = _DEVICE_ID_AI1 if port_type == "rj45" else _DEVICE_ID_AI2
        self._threshold = threshold

    def read(self):
        """读取数字电平。

        Returns:
            bool: True=高电平, False=低电平, None=超时
        """
        payload = struct.pack(
            "<bbbH",
            self._dev_id, 0,
            self._port, 0,
        )
        res = self._serial.get_anwser(payload, time_out=0.2)
        if res is not None and len(res) >= 5:
            val = struct.unpack("<H", res[3:5])[0]
            return val >= self._threshold
        return None

    @property
    def threshold(self):
        return self._threshold

    @threshold.setter
    def threshold(self, value):
        self._threshold = value


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== DigitalInput 自检（10 秒，Ctrl+C 退出）==")
    serial_obj = SerialWrap()

    print("\n--- RJ45 端口 1~6 ---")
    try:
        start = time.time()
        while time.time() - start < 10:
            for port in range(1, 7):
                di = DigitalInput(serial_obj, port=port)
                val = di.read()
                if val:
                    print(f"  Port {port}: HIGH")
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass

    serial_obj.close()
    print("== 完成 ==")
