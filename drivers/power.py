"""drivers/power.py — 电池电量 driver

dev_id=0x0c (power)

读取电池电压。

用法:
    python -m drivers.power          # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.power import Battery
        serial_obj = SerialWrap()
        bat = Battery(serial_obj)
        v = bat.voltage()             # 电压 (V)

协议帧:
    读取: struct.pack("<bbi", 0x0c, 0x01, 0)
    响应: dev_id(1) + mode(1) + voltage_mV(4, signed int)
    voltage / 1000 = 电压(V)

实现参考:
    _backup/mc602_ctl2.py: Battry_2
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

_DEVICE_ID_POWER = 0x0c
_MODE_GET = 0x01


# ---------------------------------------------------------------------------
# Battery
# ---------------------------------------------------------------------------

class Battery:
    """电池电量（dev_id=0x0c）。"""

    def __init__(self, serial):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"power 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial

    def voltage(self):
        """读取电池电压。

        Returns:
            float: 电压 (V)，或 None（超时）
        """
        payload = struct.pack("<bbi", _DEVICE_ID_POWER, _MODE_GET, 0)
        res = self._serial.get_anwser(payload, time_out=0.2)
        if res is not None and len(res) >= 6:
            # 响应: dev_id(1) + mode(1) + voltage_mV(4, signed int)
            mv = struct.unpack("<i", res[2:6])[0]
            return mv / 1000.0
        return None

    def voltage_mv(self):
        """读取电池电压（mV 整数）。"""
        v = self.voltage()
        return int(v * 1000) if v is not None else None


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== Battery 自检 ==")
    serial_obj = SerialWrap()
    bat = Battery(serial_obj)

    for i in range(5):
        v = bat.voltage()
        if v is not None:
            print(f"  电池电压: {v:.2f} V")
        time.sleep(0.5)

    serial_obj.close()
    print("== 完成 ==")
