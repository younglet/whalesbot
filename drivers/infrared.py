"""drivers/infrared.py — 红外测距传感器 driver

dev_id=0x07, mode=1

读取红外距离传感器值。

用法:
    python -m drivers.infrared           # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.infrared import Infrared
        serial_obj = SerialWrap()
        ir = Infrared(serial_obj, port=1)
        val = ir.read()

协议帧:
    读取: struct.pack("<bbbH", 0x07, 0x01, port_id, 0)
    响应: dev_id(1) + mode(1) + port_id(1) + value(2, unsigned short)

实现参考:
    _backup/mc602_ctl2.py: Infrared_2
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
_MODE = 0x01


# ---------------------------------------------------------------------------
# Infrared
# ---------------------------------------------------------------------------

class Infrared:
    """红外测距传感器（dev_id=0x07, mode=1）。"""

    def __init__(self, serial, port=1):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"infrared 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial
        self._port = port

    def read(self):
        """读取红外距离值。

        Returns:
            int: 传感器值，或 None（超时）
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


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== Infrared 自检 ==")
    serial_obj = SerialWrap()

    for port in range(1, 5):
        ir = Infrared(serial_obj, port=port)
        val = ir.read()
        print(f"  Port {port}: {val}")

    serial_obj.close()
    print("== 完成 ==")
