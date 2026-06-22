"""drivers/motor4.py — 四路直流电机 + 四路编码器 driver

dev_id=0x01 (motor4), dev_id=0x03 (encoder4)

一次发送控制 4 路电机/读取 4 路编码器，比逐路调用效率更高。

用法:
    python -m drivers.motor4         # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.motor4 import Motor4, Encoder4
        serial_obj = SerialWrap()
        motors = Motor4(serial_obj)
        motors.set_speed([50, -30, 0, 20])     # 四路速度
        encoders = Encoder4(serial_obj)
        pos = encoders.read()                   # [enc1, enc2, enc3, enc4]

协议帧:
    Motor4.set_speed:  struct.pack("<bbbbbb", 0x01, 0x02, s1, s2, s3, s4)
    Encoder4.read:     struct.pack("<bbiiii", 0x03, 0x01, 0, 0, 0, 0)
    Encoder4.reset:    struct.pack("<bbiiii", 0x03, 0x03, 0, 0, 0, 0)

实现参考:
    _backup/mc602_ctl2.py: Motor4_2, EncoderMotors4_2
    _backup/controller_wrap.py: Motor4
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

_DEVICE_ID_MOTOR4 = 0x01      # 四路电机
_DEVICE_ID_ENCODER4 = 0x03    # 四路编码器
_MODE_SET = 0x02              # set
_MODE_GET = 0x01              # get
_MODE_RESET = 0x03            # reset


# ---------------------------------------------------------------------------
# Motor4 — 四路直流电机
# ---------------------------------------------------------------------------

class Motor4:
    """四路直流电机（dev_id=0x01），一次设置四路速度。

    每路 speed: -100 ~ 100，正负表方向。
    """

    NUM_MOTORS = 4
    MIN_SPEED = -100
    MAX_SPEED = 100

    def __init__(self, serial, reverse=None):
        """Args:
            serial:  SerialWrap 实例
            reverse: 可选，四路反转标志 [1/-1, ...]，默认全 1
        """
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"motor4 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial
        self._reverse = reverse or [1, 1, 1, 1]
        if len(self._reverse) != self.NUM_MOTORS:
            raise ValueError(f"reverse 长度必须为 {self.NUM_MOTORS}")

    def set_speed(self, speeds):
        """设置四路电机速度。

        Args:
            speeds: 四路速度 [s1, s2, s3, s4]，每路 -100 ~ 100
        """
        if not isinstance(speeds, (list, tuple)) or len(speeds) != self.NUM_MOTORS:
            raise ValueError(f"speeds 必须是 {self.NUM_MOTORS} 个值的列表")
        clamped = []
        for i, s in enumerate(speeds):
            s = int(s * self._reverse[i])
            s = max(self.MIN_SPEED, min(self.MAX_SPEED, s))
            clamped.append(s)
        payload = struct.pack(
            "<bbbbbb",
            _DEVICE_ID_MOTOR4, _MODE_SET,
            *clamped,
        )
        self._serial.get_anwser(payload, time_out=0.2)

    def stop(self):
        """停止所有电机。"""
        self.set_speed([0, 0, 0, 0])


# ---------------------------------------------------------------------------
# Encoder4 — 四路编码器
# ---------------------------------------------------------------------------

class Encoder4:
    """四路编码器（dev_id=0x03），一次读取/复位四路编码器。"""

    NUM_ENCODERS = 4

    def __init__(self, serial, reverse=None):
        """Args:
            serial:  SerialWrap 实例
            reverse: 可选，四路反转标志 [1/-1, ...]，默认全 1
        """
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"encoder4 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial
        self._reverse = reverse or [1, 1, 1, 1]
        if len(self._reverse) != self.NUM_ENCODERS:
            raise ValueError(f"reverse 长度必须为 {self.NUM_ENCODERS}")

    def read(self):
        """读取四路编码器累计值。

        Returns:
            list[int]: [enc1, enc2, enc3, enc4] 或 None
        """
        payload = struct.pack(
            "<bbiiii",
            _DEVICE_ID_ENCODER4, _MODE_GET,
            0, 0, 0, 0,
        )
        res = self._serial.get_anwser(payload, time_out=0.2)
        if res is not None and len(res) >= 18:
            # 响应: dev_id(1) + mode(1) + enc1(4) + enc2(4) + enc3(4) + enc4(4)
            vals = struct.unpack("<iiii", res[2:18])
            return [v * r for v, r in zip(vals, self._reverse)]
        return None

    def reset(self):
        """清零四路编码器。"""
        payload = struct.pack(
            "<bbiiii",
            _DEVICE_ID_ENCODER4, _MODE_RESET,
            0, 0, 0, 0,
        )
        self._serial.get_anwser(payload, time_out=0.2)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== Motor4 + Encoder4 自检 ==")
    serial_obj = SerialWrap()

    motors = Motor4(serial_obj)
    encoders = Encoder4(serial_obj)
    encoders.reset()

    print("[1] 四路正转 [50, 30, 20, 40] (1s)...")
    motors.set_speed([50, 30, 20, 40])
    time.sleep(1)
    print(f"    编码器: {encoders.read()}")

    print("[2] 停止...")
    motors.stop()
    time.sleep(0.3)
    encoders.reset()
    print(f"    编码器(复位后): {encoders.read()}")

    serial_obj.close()
    print("== 完成 ==")
