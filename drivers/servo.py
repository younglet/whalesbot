"""drivers/servo.py — 舵机 driver 兼容入口

已拆分为两个独立文件，本文件保留作为向后兼容的 re-export 入口：
  - BusServo  → drivers/bus_servo.py   （总线舵机，完整实现）
  - PWMServo  → drivers/pwm_servo.py   （PWM 舵机，占位，固件未支持）

建议新代码直接 import 拆分后的文件：
    from drivers.bus_servo import BusServo
    from drivers.pwm_servo import PWMServo

自检请分别运行：
    python -m drivers.bus_servo
    python -m drivers.pwm_servo
"""

from .bus_servo import BusServo
from .pwm_servo import PWMServo
