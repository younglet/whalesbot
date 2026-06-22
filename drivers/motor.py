"""drivers/motor.py — 单路直流电机 + 编码器 driver

dev_id=0x02 (motor), dev_id=0x04 (encoder)

不依赖 _backup/mc602_ctl2.py，直接构造协议帧 + 用 SerialWrap 发送。

用法:
    python -m drivers.motor          # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.motor import Motor, EncoderMotor
        serial_obj = SerialWrap()
        motor = Motor(serial_obj, port=1)
        motor.set_speed(50)
        encoder = EncoderMotor(serial_obj, port=1)
        pos = encoder.read()

协议帧:
    Motor.set_speed:  struct.pack("<bbbb",  0x02, 0x02, port, speed)
    Encoder.read:     struct.pack("<bbbi",  0x04, 0x01, port, 0)
    Encoder.reset:    struct.pack("<bbbi",  0x04, 0x03, port, 0)

实现参考:
    _backup/mc602_ctl2.py: Motor_2, EncoderMotor_2
    _backup/controller_wrap.py: Motor, EncoderMotor
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

_DEVICE_ID_MOTOR = 0x02       # 直流电机
_DEVICE_ID_ENCODER = 0x04     # 编码器
_MODE_SET = 0x02              # set
_MODE_GET = 0x01              # get
_MODE_RESET = 0x03            # reset


# ---------------------------------------------------------------------------
# Motor — 单路直流电机
# ---------------------------------------------------------------------------

class Motor:
    """单路直流电机（dev_id=0x02）。

    speed: -100 ~ 100，正负表方向。
    """

    MIN_SPEED = -100
    MAX_SPEED = 100

    def __init__(self, serial, port=1, reverse=1):
        """Args:
            serial:  SerialWrap 实例
            port:    电机端口号（1-4）
            reverse: 反转方向，1 或 -1
        """
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"motor 仅支持 MC602，当前设备 {serial.device.name}")
        if reverse not in (1, -1):
            raise ValueError(f"reverse 必须是 1 或 -1，收到 {reverse}")
        self._serial = serial
        self._port = port
        self._reverse = reverse

    def set_speed(self, speed):
        """设置电机速度。

        Args:
            speed: -100 ~ 100，正负表方向（受 reverse 影响）
        """
        if not isinstance(speed, (int, float)):
            raise TypeError(f"speed 必须是数字，收到 {type(speed).__name__}")
        speed = int(speed * self._reverse)
        speed = max(self.MIN_SPEED, min(self.MAX_SPEED, speed))
        payload = struct.pack(
            "<bbbb",
            _DEVICE_ID_MOTOR, _MODE_SET,
            self._port, speed,
        )
        self._serial.get_anwser(payload, time_out=0.2)


# ---------------------------------------------------------------------------
# EncoderMotor — 单路编码器
# ---------------------------------------------------------------------------

class EncoderMotor:
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

    print("== Motor + Encoder 自检 ==")
    serial_obj = SerialWrap()

    motor = Motor(serial_obj, port=1)
    encoder = EncoderMotor(serial_obj, port=1)
    encoder.reset()

    print("[1] 电机正转 50 (1s)...")
    motor.set_speed(50)
    time.sleep(1)
    print(f"    编码器: {encoder.read()}")

    print("[2] 电机反转 -50 (1s)...")
    motor.set_speed(-50)
    time.sleep(1)
    print(f"    编码器: {encoder.read()}")

    print("[3] 停止...")
    motor.set_speed(0)
    time.sleep(0.5)

    print("[4] 编码器复位...")
    encoder.reset()
    print(f"    编码器: {encoder.read()}")

    serial_obj.close()
    print("== 完成 ==")
