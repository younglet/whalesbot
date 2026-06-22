"""drivers/bus_servo.py — 总线舵机 driver（抽离自 drivers/servo.py）

不依赖 _backup/mc602_ctl2.py，直接构造协议帧 + 用 SerialWrap 发送。

用法：
    python -m drivers.bus_servo       # 自检
    python drivers/bus_servo.py       # 也可以（自举路径）
    或在自己的脚本里：
        from link import SerialWrap
        from drivers.bus_servo import BusServo
        serial_obj = SerialWrap()
        servo = BusServo(serial_obj, port=1)
        servo.set_angle(90, speed=100)
        servo.set_speed(50)          # 360° 连续旋转

协议帧:
    set_angle:  struct.pack("<bbbbbh", 0x06, 0x02, port, 0x01, speed,  angle)
    set_speed:  struct.pack("<bbbbbh", 0x06, 0x02, port, 0x02, speed,  0)
        - dev_id:  0x06 (servo_bus)
        - mode:    0x02 (set)
        - port:    总线上的舵机 ID（1-255）
        - sub_mode: 0x01=角度模式, 0x02=速度模式
        - set_angle.speed:   signed byte (-128~127)，实际只用 0~127
        - set_angle.angle:   signed short（-32768~32767）
        - set_speed.speed:   signed byte (-128~127)，末尾补 0 对齐 7 字节帧

    注意：线格式是 <bbbbbh（6 值 7 字节），源于 StructData 自动在 format 前补 <b。
    MC602 send_cmd 自动加 header (77 68) + len + tail (0A)

实现参考（仅看协议字段，不直接 import）：
    _backup/mc602_ctl2.py:ServoBus_2  →  ctl602_dev_list["servo_bus"]
"""

# Path bootstrap：让 `python drivers/bus_servo.py` 也能跑（不需要 -m）
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
import struct


# ---------------------------------------------------------------------------
# 协议常量
# ---------------------------------------------------------------------------

_DEVICE_ID_SERVO_BUS = 0x06   # 总线舵机（来自 ctl602_dev_list["servo_bus"]）
_MODE_SET = 0x02              # set 操作（来自 DevCmdInterface.set）
_MODE_GET = 0x01              # get 操作（来自 DevCmdInterface.get）

# 子模式：占用 set_angle 协议里 speed 字段的字节（signed byte 位置）
_SUBMODE_SET_ANGLE = 0x01     # 旧 ServoBus_2.set_angle 的 act_mode 第一个 arg
_SUBMODE_SET_SPEED = 0x02     # 旧 ServoBus_2.set_speed 的 act_mode 第一个 arg


# ---------------------------------------------------------------------------
# BusServo — 总线舵机
# ---------------------------------------------------------------------------

class BusServo:
    """总线舵机（servo_bus, dev_id=0x06）—— 完整实现。

    协议层硬约束（来自 ctl602_dev_list["servo_bus"] = "<bbbbh"）：
      - port:    1-255
      - set_angle 的 speed 字段是 signed byte（-128~127，负数无意义）
      - set_angle 的 angle 字段是 signed short（-32768~32767）
      - set_speed 的 speed 字段是 signed short（-32768~32767）

    实际舵机硬件的范围远小于协议上限：
      - 普通 0-180° 舵机：angle ∈ [0, 180]
      - 普通 0-270° 舵机：angle ∈ [0, 270]
      - 360° 连续旋转舵机：用 set_speed 控制方向和速度
    """

    DEFAULT_PORT = 1
    DEFAULT_SPEED = 100

    # set_angle 的 speed 字段（signed byte）
    MIN_ANGLE_SPEED = 0
    MAX_ANGLE_SPEED = 127

    # angle 字段（signed short）
    MIN_ANGLE = -32768
    MAX_ANGLE = 32767

    # set_speed 的 speed 字段（signed short）
    MIN_ROTATE_SPEED = -32768
    MAX_ROTATE_SPEED = 32767

    def __init__(self, serial, port=DEFAULT_PORT):
        """Args:
            serial:  SerialWrap 实例（必须已经识别为 MC602）
            port:    总线上的舵机 ID（1-255）
        """
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(
                f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}"
            )
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(
                f"servo 仅支持 MC602，当前设备 {serial.device.name}"
            )
        if not isinstance(port, int) or not (1 <= port <= 255):
            raise ValueError(f"port 必须在 1-255，收到 {port}")
        self._serial = serial
        self._port = port

    def set_angle(self, angle, speed=DEFAULT_SPEED):
        """让舵机转到指定角度。

        Args:
            angle: 角度（signed short 范围，常见 0-180 / 0-270）
            speed: 速度 0-127，默认 100
        """
        if not isinstance(speed, int) or not (
            self.MIN_ANGLE_SPEED <= speed <= self.MAX_ANGLE_SPEED
        ):
            raise ValueError(
                f"speed 必须在 {self.MIN_ANGLE_SPEED}-{self.MAX_ANGLE_SPEED}，收到 {speed}"
            )
        if not isinstance(angle, int) or not (self.MIN_ANGLE <= angle <= self.MAX_ANGLE):
            raise ValueError(
                f"angle 必须在 {self.MIN_ANGLE}-{self.MAX_ANGLE} (signed short)，"
                f"收到 {angle}"
            )
        payload = struct.pack(
            "<bbbbbh",
            _DEVICE_ID_SERVO_BUS, _MODE_SET,
            self._port, _SUBMODE_SET_ANGLE, speed, angle,
        )
        self._serial.get_anwser(payload, time_out=1.0)

    def set_speed(self, speed):
        """让舵机以指定速度连续旋转（仅适用于 360° 连续旋转舵机）。

        Args:
            speed: 速度（signed short 范围 -32768~32767，正负表方向）
        """
        if not isinstance(speed, int) or not (
            self.MIN_ROTATE_SPEED <= speed <= self.MAX_ROTATE_SPEED
        ):
            raise ValueError(
                f"speed 必须在 {self.MIN_ROTATE_SPEED}-{self.MAX_ROTATE_SPEED} "
                f"(signed short)，收到 {speed}"
            )
        payload = struct.pack(
            "<bbbbbh",
            _DEVICE_ID_SERVO_BUS, _MODE_SET,
            self._port, _SUBMODE_SET_SPEED, speed, 0,
        )
        self._serial.get_anwser(payload, time_out=1.0)

    def read_angle(self):
        """读取当前角度（mode=1 get）。

        固件若未实现 servo_bus 的 get 协议则返回 None。
        备份代码中 ServoBus_2 也未调用过 get 模式，此方法为扩展预留。

        Returns:
            int | None: 当前角度，或 None（固件不支持/超时）
        """
        payload = struct.pack(
            "<bbbbbh",
            _DEVICE_ID_SERVO_BUS, _MODE_GET,
            self._port, 0, 0, 0,
        )
        res = self._serial.get_anwser(payload, time_out=1.0)
        if res is not None and len(res) >= 5:
            angle = struct.unpack("<h", res[3:5])[0]
            return angle
        return None


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== BusServo 自检 ==")
    serial_obj = SerialWrap()

    servo = BusServo(serial_obj, port=1)
    print("[1] 归零 (0°)...")
    servo.set_angle(0)
    time.sleep(1)

    print("[2] 0°→179° 扫描 (step=1°, interval=20ms)...")
    for angle in range(180):
        servo.set_angle(angle)
        time.sleep(0.02)

    print("[3] 回到 90°...")
    servo.set_angle(90)
    time.sleep(0.5)

    serial_obj.close()
    print("== 完成 ==")
