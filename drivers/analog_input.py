"""drivers/analog_input.py — 模拟输入传感器 driver

MC602 有两路模拟输入，物理接口不同但协议一致：

  port_type="rj45"   (dev_id=0x07) — 端口 1~6，对应 RJ45 水晶头
  port_type="dupont" (dev_id=0x08) — 端口 1~3，对应杜邦头

读取端口模拟电压值，范围 0-4095（12-bit ADC）。

用法:
    python -m drivers.analog_input       # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.analog_input import AnalogInput
        serial_obj = SerialWrap()
        ai   = AnalogInput(serial_obj, port=1)                     # 默认 rj45
        ai2  = AnalogInput(serial_obj, port=1, port_type="dupont") # 杜邦头
        val = ai.read()                   # 0-4095

协议帧:
    读取: struct.pack("<bbbH", dev_id, 0, port, 0)
    响应: dev_id(1) + mode(1) + port(1) + value(2, unsigned short)

实现参考:
    _backup/mc602_ctl2.py: AnalogInput_2, Sensor_Analog2_2
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

_DEV_ID_MAP = {
    "rj45":   0x07,    # RJ45 水晶头，端口 1~6
    "dupont": 0x08,    # 杜邦头，端口 1~3
}


# ---------------------------------------------------------------------------
# AnalogInput
# ---------------------------------------------------------------------------

class AnalogInput:
    """模拟输入传感器。

    支持两路物理接口：RJ45 水晶头（默认）和杜邦头。
    读取 0-4095（12-bit ADC）。
    """

    def __init__(self, serial, port=1, port_type="rj45"):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"analog_input 仅支持 MC602，当前设备 {serial.device.name}")
        if port_type not in _DEV_ID_MAP:
            raise ValueError(f"port_type 必须是 {list(_DEV_ID_MAP.keys())}，收到 '{port_type}'")
        self._serial = serial
        self._port = port
        self._dev_id = _DEV_ID_MAP[port_type]

    def read(self):
        """读取模拟值。

        Returns:
            int: 0-4095，或 None（超时）
        """
        payload = struct.pack(
            "<bbbH",
            self._dev_id, 0,
            self._port, 0,
        )
        res = self._serial.get_anwser(payload, time_out=0.2)
        if res is not None and len(res) >= 5:
            return struct.unpack("<H", res[3:5])[0]
        return None


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== AnalogInput 自检 ==")
    serial_obj = SerialWrap()

    print("\n--- RJ45 水晶头 (0x07) 端口 1~6 ---")
    for port in range(1, 7):
        ai = AnalogInput(serial_obj, port=port)
        val = ai.read()
        print(f"  Port {port}: {val}")

    print("\n--- 杜邦头 (0x08) 端口 1~3 ---")
    for port in range(1, 4):
        ai2 = AnalogInput(serial_obj, port=port, port_type="dupont")
        val = ai2.read()
        print(f"  Port {port}: {val}")

    serial_obj.close()
    print("\n== 完成 ==")
