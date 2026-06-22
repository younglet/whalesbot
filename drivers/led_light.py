"""drivers/led_light.py — RGB 彩灯 driver

dev_id=0x0e (led_light)

控制板载 RGB LED 灯或外接灯带。

用法:
    python -m drivers.led_light       # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.led_light import LedLight
        serial_obj = SerialWrap()
        led = LedLight(serial_obj, port=1)
        led.set_light(0, 255, 0, 0)     # LED 0, 红色
        led.set_light(1, 0, 255, 0)     # LED 1, 绿色

协议帧:
    set_light: struct.pack("<bbbBBBB", 0x0e, 0x02, port_id, led_id, r, g, b)
        - led_id: LED 编号 (0-based)
        - r, g, b: 0-255 (unsigned byte)

实现参考:
    _backup/mc602_ctl2.py: LedLight_2
    _backup/controller_wrap.py: LedLight
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

_DEVICE_ID_LED = 0x0e
_MODE_SET = 0x02


# ---------------------------------------------------------------------------
# LedLight
# ---------------------------------------------------------------------------

class LedLight:
    """RGB 彩灯（dev_id=0x0e）。

    控制单个或多个 RGB LED。r/g/b 范围 0-255。
    """

    def __init__(self, serial, port=1):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"led_light 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial
        self._port = port

    def set_light(self, led_id, r, g, b):
        """设置指定 LED 的 RGB 颜色。

        Args:
            led_id: LED 编号（0-based）
            r: 红色 0-255
            g: 绿色 0-255
            b: 蓝色 0-255
        """
        for name, val in [("r", r), ("g", g), ("b", b)]:
            if not (0 <= val <= 255):
                raise ValueError(f"{name} 必须在 0-255，收到 {val}")
        payload = struct.pack(
            "<bbbBBBB",
            _DEVICE_ID_LED, _MODE_SET,
            self._port,
            led_id, r, g, b,
        )
        self._serial.get_anwser(payload, time_out=0.2)

    def off(self, led_id):
        """关闭指定 LED。"""
        self.set_light(led_id, 0, 0, 0)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== LedLight 自检 ==")
    serial_obj = SerialWrap()
    led = LedLight(serial_obj, port=1)

    colors = [
        ("红", 255, 0, 0),
        ("绿", 0, 255, 0),
        ("蓝", 0, 0, 255),
        ("白", 255, 255, 255),
    ]

    for name, r, g, b in colors:
        print(f"  {name} (R={r} G={g} B={b})")
        led.set_light(0, r, g, b)
        time.sleep(1)

    print("  关闭")
    led.off(0)

    serial_obj.close()
    print("== 完成 ==")
