"""drivers/nixietube.py — 数码管 driver

dev_id=0x0f (nixietube)

控制 4 位数码管显示数字。

用法:
    python -m drivers.nixietube       # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.nixietube import NixieTube
        serial_obj = SerialWrap()
        tube = NixieTube(serial_obj, port=1)
        tube.set_number(1234)         # 显示 1234
        tube.off()                    # 关闭

协议帧:
    set_number: struct.pack("<bbbi", 0x0f, 0x02, port, number)
        - number: 4 位整数，每 4 bit 一段对应一位数码管

实现参考:
    _backup/mc602_ctl2.py: NixieTube_2
    _backup/controller_wrap.py: NixieTube
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

_DEVICE_ID_NIXIE = 0x0f
_MODE_SET = 0x02


# ---------------------------------------------------------------------------
# NixieTube
# ---------------------------------------------------------------------------

class NixieTube:
    """数码管（dev_id=0x0f）。

    控制 4 位数码管显示。number 每 4 bit 控制一位（0-9 有效，0xA-0xF 为关闭/特殊符号）。
    """

    def __init__(self, serial, port=1):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"nixietube 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial
        self._port = port

    def set_number(self, number):
        """设置数码管显示。

        Args:
            number: 显示的数值。
                    例如 1234 → 数码管显示 '1234'
                    每 4 bit 一段，0-9=数字，10-15=关闭/特殊
        """
        payload = struct.pack(
            "<bbbi",
            _DEVICE_ID_NIXIE, _MODE_SET,
            self._port, int(number),
        )
        self._serial.get_anwser(payload, time_out=0.2)

    def off(self):
        """关闭数码管（全段熄灭）。"""
        self.set_number(0xFFFF)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== NixieTube 自检 ==")
    serial_obj = SerialWrap()
    tube = NixieTube(serial_obj, port=1)

    tests = [0, 1111, 2222, 3333, 4444, 5555, 6666, 7777, 8888, 9999, 1234, 5678]
    for n in tests:
        print(f"  显示 {n}...")
        tube.set_number(n)
        time.sleep(0.5)

    print("  关闭...")
    tube.off()

    serial_obj.close()
    print("== 完成 ==")
