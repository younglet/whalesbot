"""drivers/stepper.py — 步进电机 driver

dev_id=0x11 (stepper)

控制步进电机：设置 PWM 频率、读取步数。

用法:
    python -m drivers.stepper           # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.stepper import Stepper
        serial_obj = SerialWrap()
        st = Stepper(serial_obj, port=1)
        st.set_pwm(1000)                # 设置 PWM 频率
        steps = st.get_step()           # 读取累计步数

协议帧:
    设置:  struct.pack("<bbbii", 0x11, 0x02, port, freq, 0)
    读取:  struct.pack("<bbbii", 0x11, 0x01, port, 0, 0)
    响应:  dev_id(1) + mode(1) + port_id(1) + freq(4) + step(4,signed int)

实现参考:
    _backup/mc602_ctl2.py: Stepper_2
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

_DEVICE_ID_STEPPER = 0x11
_MODE_GET = 0x01
_MODE_SET = 0x02


# ---------------------------------------------------------------------------
# Stepper
# ---------------------------------------------------------------------------

class Stepper:
    """步进电机（dev_id=0x11）。

    设置 PWM 频率控制转速，读取累计步数。
    """

    def __init__(self, serial, port=1):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"stepper 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial
        self._port = port

    def set_pwm(self, freq):
        """设置 PWM 频率。

        Args:
            freq: PWM 频率 (Hz)
        """
        payload = struct.pack(
            "<bbbii",
            _DEVICE_ID_STEPPER, _MODE_SET,
            self._port, int(freq), 0,
        )
        self._serial.get_anwser(payload, time_out=0.2)

    def get_step(self):
        """读取累计步数。

        Returns:
            int: 累计步数，或 None（超时）
        """
        payload = struct.pack(
            "<bbbii",
            _DEVICE_ID_STEPPER, _MODE_GET,
            self._port, 0, 0,
        )
        res = self._serial.get_anwser(payload, time_out=0.2)
        if res is not None and len(res) >= 11:
            # 响应: dev_id(1) + mode(1) + port_id(1) + freq(4) + step(4)
            _, step = struct.unpack("<ii", res[3:11])
            return step
        return None


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== Stepper 自检 ==")
    serial_obj = SerialWrap()

    for port in range(1, 5):
        st = Stepper(serial_obj, port=port)
        step = st.get_step()
        print(f"  Port {port}: steps={step}")

    serial_obj.close()
    print("== 完成 ==")
