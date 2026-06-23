"""drivers — 面向用户的硬件 driver 包

每个 driver 封装一对 tools/* 协议类，做参数校验 + 友好 API。
调用方式：python -m drivers.<hw>
"""

from .ambient_light import AmbientLight
from .analog_input import AnalogInput
from .bluetooth import BluetoothPad
from .board_key import BoardKey
from .bus_servo import BusServo
from .buzzer import Buzzer
from .digital_input import DigitalInput
from .digital_output import DigitalOutput
from .encoder import Encoder
from .infrared import Infrared
from .led_light import LedLight
from .motor import Motor, EncoderMotor
from .motor4 import Motor4, Encoder4
from .nixietube import NixieTube
from .pid_encoder_motor import PIDEncoderMotor
from .power import Battery
from .pwm_servo import PWMServo
from .screen import Screen
from .stepper import Stepper
from .touch import Touch
from .ultrasonic import Ultrasonic

__all__ = [
    "AmbientLight",
    "AnalogInput",
    "Battery",
    "BluetoothPad",
    "BoardKey",
    "BusServo",
    "Buzzer",
    "DigitalInput",
    "DigitalOutput",
    "Encoder",
    "Encoder4",
    "EncoderMotor",
    "Infrared",
    "LedLight",
    "Motor",
    "Motor4",
    "NixieTube",
    "PIDEncoderMotor",
    "PWMServo",
    "Screen",
    "Stepper",
    "Touch",
    "Ultrasonic",
]
