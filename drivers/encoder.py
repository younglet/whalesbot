"""drivers/encoder.py — 单路编码器 driver

dev_id=0x04 (encoder)

读取单路电机编码器脉冲累计值。

用法:
    python -m drivers.encoder        # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.encoder import Encoder
        serial_obj = SerialWrap()
        encoder = Encoder(serial_obj, port=1)
        pos = encoder.read()

协议帧:
    Encoder.read:   struct.pack("<bbbi",  0x04, 0x01, port, 0)
    Encoder.reset:  struct.pack("<bbbi",  0x04, 0x03, port, 0)

实现参考:
    _backup/mc602_ctl2.py: EncoderMotor_2
    _backup/controller_wrap.py: EncoderMotor
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

_DEVICE_ID_ENCODER = 0x04     # 编码器
_MODE_GET = 0x01              # get
_MODE_RESET = 0x03            # reset


# ---------------------------------------------------------------------------
# Encoder — 单路编码器
# ---------------------------------------------------------------------------

class Encoder:
    """单路编码器（dev_id=0x04）。

    读取电机旋转的编码器脉冲累计值，正负表方向。
    """

    def __init__(self, serial, port=1, reverse=1):
        """Args:
            serial:  SerialWrap 实例
            port:    编码器端口号（1-4）
            reverse: 反转方向，1 或 -1
        """
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"encoder 仅支持 MC602，当前设备 {serial.device.name}")
        if reverse not in (1, -1):
            raise ValueError(f"reverse 必须是 1 或 -1，收到 {reverse}")
        self._serial = serial
        self._port = port
        self._reverse = reverse

    def read(self):
        """读取编码器累计值。

        Returns:
            int: 编码器脉冲值，或 None（超时）
        """
        payload = struct.pack(
            "<bbbi",
            _DEVICE_ID_ENCODER, _MODE_GET,
            self._port, 0,
        )
        res = self._serial.get_anwser(payload, time_out=0.2)
        if res is not None and len(res) >= 7:
            val = struct.unpack("<i", res[3:7])[0]
            return val * self._reverse
        return None

    def reset(self):
        """清零编码器累计值。"""
        payload = struct.pack(
            "<bbbi",
            _DEVICE_ID_ENCODER, _MODE_RESET,
            self._port, 0,
        )
        self._serial.get_anwser(payload, time_out=0.2)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== Encoder 自检 ==")
    serial_obj = SerialWrap()

    for port in range(1, 5):
        encoder = Encoder(serial_obj, port=port)
        val = encoder.read()
        print(f"  Port {port}: {val}")

    serial_obj.close()
    print("== 完成 ==")
