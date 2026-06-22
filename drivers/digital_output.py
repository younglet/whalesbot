"""drivers/digital_output.py — 数字输出 driver

dev_id=0x10 (dout)

控制 DO 端口输出高/低电平（如电磁铁、LED、继电器等）。

用法:
    python -m drivers.digital_output       # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.digital_output import DigitalOutput
        serial_obj = SerialWrap()
        dout = DigitalOutput(serial_obj, port=1)
        dout.on()                           # 输出高电平
        dout.off()                          # 输出低电平

协议帧:
    set: struct.pack("<bbbb", 0x10, 0x02, port, value)
        - value: 0=低电平, 1=高电平

实现参考:
    _backup/mc602_ctl2.py: PoutD_2
    _backup/controller_wrap.py: PoutD
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

_DEVICE_ID_DOUT = 0x10
_MODE_SET = 0x02


# ---------------------------------------------------------------------------
# DigitalOutput
# ---------------------------------------------------------------------------

class DigitalOutput:
    """数字输出端口（dev_id=0x10）。

    控制 DO 端口输出高/低电平。可用于电磁铁、LED、继电器等。
    """

    def __init__(self, serial, port=1):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"digital_output 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial
        self._port = port

    def set(self, value):
        """设置输出电平。

        Args:
            value: 0=低电平(关), 1=高电平(开)
        """
        if value not in (0, 1):
            raise ValueError(f"value 必须是 0 或 1，收到 {value}")
        payload = struct.pack(
            "<bbbb",
            _DEVICE_ID_DOUT, _MODE_SET,
            self._port, value,
        )
        self._serial.get_anwser(payload, time_out=0.2)

    def on(self):
        """输出高电平（开）。"""
        self.set(1)

    def off(self):
        """输出低电平（关）。"""
        self.set(0)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== DigitalOutput 自检 ==")
    serial_obj = SerialWrap()
    dout = DigitalOutput(serial_obj, port=1)

    print("[1] ON (1s)...")
    dout.on()
    time.sleep(1)

    print("[2] OFF (0.5s)...")
    dout.off()
    time.sleep(0.5)

    print("[3] ON (0.5s)...")
    dout.on()
    time.sleep(0.5)

    print("[4] OFF...")
    dout.off()

    serial_obj.close()
    print("== 完成 ==")
