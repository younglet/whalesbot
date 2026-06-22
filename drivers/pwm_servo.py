"""drivers/pwm_servo.py — PWM 舵机 driver（抽离自 drivers/servo.py）

不依赖 _backup/mc602_ctl2.py，直接构造协议帧 + 用 SerialWrap 发送。

当前状态：**占位，固件未支持**。
MC602P 固件当前未实现 servo_pwm 设备（dev_id=0x05）的下行协议。
实例化直接抛 NotImplementedError。

用法：
    python -m drivers.pwm_servo       # 自检（演示占位行为）
    python drivers/pwm_servo.py       # 也可以（自举路径）

协议帧（计划）:
    set_angle:  struct.pack("<bbbBB", 0x05, 0x02, port_id, speed, angle)
        - dev_id:  0x05 (servo_pwm)
        - mode:    0x02 (set)
        - port_id: PWM 通道（1-255）
        - speed:   unsigned byte (0-255)
        - angle:   unsigned byte (0-180)
    MC602 send_cmd 自动加 header (77 68) + len + tail (0A)

实现参考（仅看协议字段，不直接 import）：
    _backup/mc602_ctl2.py:ServoPwm_2  →  ctl602_dev_list["servo_pwm"]
    _backup/controller_wrap.py:ServoPwm
"""

# Path bootstrap：让 `python drivers/pwm_servo.py` 也能跑（不需要 -m）
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ---------------------------------------------------------------------------
# PWMServo — PWM 舵机（占位实现）
# ---------------------------------------------------------------------------

class PWMServo:
    """PWM 舵机（servo_pwm, dev_id=0x05）—— **占位，固件未支持**。

    当前 MC602P 固件未实现 servo_pwm 设备（dev_id=0x05）的下行协议。
    参考 _backup/mc602_ctl2.py:ServoPwm_2 / controller_wrap.py:ServoPwm：
    原版只是 thin wrapper（且 set_angle 里 `port_id=port_id` 是未定义局部变量 bug），
    也没有真硬件验证过。**所以这个 driver 暂不实现**，实例化直接抛 NotImplementedError。

    如果将来固件支持 PWM 舵机，按以下协议实现：
        payload = struct.pack("<bbbBB",
            0x05,      # device_id (servo_pwm)
            0x02,      # mode (set)
            speed,     # unsigned byte (0-255)
            angle,     # unsigned byte (0-180)
        )
        SerialWrap.get_anwser(payload, time_out=0.5)

    API 计划：
        PWMServo(serial, port=1)
        pwm.set_angle(angle, speed=100)   # 与 BusServo 接口一致
    """

    DEFAULT_PORT = 1
    DEFAULT_SPEED = 100

    def __init__(self, serial, port=DEFAULT_PORT):
        # 占位：参数先存好，将来固件支持时直接用
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
        # 故意抛错，提示用户固件未支持
        raise NotImplementedError(
            "PWMServo 暂未实现：MC602P 固件当前不支持 servo_pwm (dev_id=0x05) 协议。"
            "如需支持，请先在固件端实现 servo_pwm 设备再启用此 driver。"
        )


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== PWMServo 自检（占位演示）==")
    serial_obj = SerialWrap()

    print("[1] 尝试实例化 PWMServo（预期抛 NotImplementedError）...")
    try:
        pwm = PWMServo(serial_obj, port=1)
    except NotImplementedError as e:
        print(f"  预期错误: {e}")

    serial_obj.close()
    print("== 完成 ==")
