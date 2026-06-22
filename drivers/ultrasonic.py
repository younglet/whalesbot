"""drivers/ultrasonic.py — 超声波测距传感器 driver

dev_id=0x07, mode=3

读取超声波距离，单位 mm。

用法:
    python -m drivers.ultrasonic         # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.ultrasonic import Ultrasonic
        serial_obj = SerialWrap()
        us = Ultrasonic(serial_obj, port=1)
        mm = us.distance_mm()
        cm = us.distance_cm()

协议帧:
    读取: struct.pack("<bbbH", 0x07, 0x03, port_id, 0)
    响应: dev_id(1) + mode(1) + port_id(1) + value(2, unsigned short)

实现参考:
    _backup/mc602_ctl2.py: ultrasonic mode
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

_DEVICE_ID = 0x07
_MODE = 0x03


# ---------------------------------------------------------------------------
# Ultrasonic
# ---------------------------------------------------------------------------

class Ultrasonic:
    """超声波测距传感器（dev_id=0x07, mode=3）。

    读取距离，单位 mm。
    """

    def __init__(self, serial, port=1):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"ultrasonic 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial
        self._port = port

    def read(self):
        """读取超声波距离（mm）。

        Returns:
            int: 距离（mm），或 None（超时）
        """
        payload = struct.pack(
            "<bbbH",
            _DEVICE_ID, _MODE,
            self._port, 0,
        )
        res = self._serial.get_anwser(payload, time_out=0.2)
        if res is not None and len(res) >= 5:
            # 响应: dev_id(1) + mode(1) + port_id(1) + value(2, unsigned short)
            return struct.unpack("<H", res[3:5])[0]
        return None

    def distance_mm(self):
        """读取距离（mm）。"""
        return self.read()

    def distance_cm(self):
        """读取距离（cm）。"""
        val = self.read()
        return val / 10.0 if val is not None else None


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== Ultrasonic 自检（10 秒）==")
    serial_obj = SerialWrap()

    start = time.time()
    while time.time() - start < 10:
        for port in range(1, 5):
            us = Ultrasonic(serial_obj, port=port)
            val = us.read()
            if val is not None and val > 0:
                print(f"  Port {port}: {val} mm  ({val/10:.1f} cm)")
        time.sleep(0.3)

    serial_obj.close()
    print("== 完成 ==")
