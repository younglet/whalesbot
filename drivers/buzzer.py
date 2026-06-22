"""drivers/buzzer.py — 蜂鸣器 driver（抽离干净版）

不依赖 _backup/mc602_ctl2.py，直接构造协议帧 + 用 SerialWrap 发送。
构造时显式传入 SerialWrap 实例（依赖注入，多硬件共享同一 serial）。

用法：
    python -m drivers.buzzer           # 自检
    python drivers/buzzer.py          # 也可以（自举路径）
    或在自己的脚本里：
        from link import SerialWrap
        from drivers.buzzer import Buzzer
        serial_obj = SerialWrap()
        buzzer = Buzzer(serial_obj)
        buzzer.beep()                  # 响 0.1s
        buzzer.beep(0.3)               # 响 0.3s
        buzzer.rest(0.5)               # 静音 0.5s

API（简化版，不接受频率参数——这个压电频响太窄，听不出区别）：
    beep(duration=0.1)    响一次
    rest(duration=0.1)    静音一段时间（不发帧）

协议帧格式：
    payload = struct.pack("<bBBB",
        device_id=0x0A,   # 蜂鸣器设备 ID
        mode=0x02,        # set 操作
        freq_half,        # 固定 110（220/2）
        dur_twentieths    # int(dur_s * 20)
    )
    MC602 send_cmd 自动加 header (77 68) + len + tail (0A)
"""

# Path bootstrap：让 `python drivers/buzzer.py` 也能跑（不需要 -m）
# 幂等：被多次 import 时不会重复加
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
import struct


# ---------------------------------------------------------------------------
# 协议常量
# ---------------------------------------------------------------------------

_DEVICE_ID_BEEP = 0x0A   # 蜂鸣器设备 ID（来自 _backup/mc602_ctl2 的 ctl602_dev_list["beep"]）
_MODE_SET = 0x02          # set 操作（来自 DevCmdInterface.set）
_FIXED_FREQ_HALF = 110    # 固定频率 220Hz（不可调——硬件听不出区别）


class Buzzer:
    """蜂鸣器面向用户的简洁 API。"""

    MIN_DURATION_S = 0.05   # 单次响声至少 50ms，否则听不见
    MAX_DURATION_S = 12.75  # duration*20 必须 ≤ 255
    DEFAULT_DURATION_S = 0.1

    def __init__(self, serial):
        """Args:
            serial: SerialWrap 实例（必须已经识别为 MC602）
        """
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(
                f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}"
            )
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(
                f"buzzer 仅支持 MC602，当前设备 {serial.device.name}"
            )
        self._serial = serial

    def beep(self, duration: float = DEFAULT_DURATION_S):
        """响一次。

        Args:
            duration: 时长 秒，默认 0.1s，范围 0.05-12.75
        """
        self._validate_duration(duration)
        duration_twentieths = int(duration * 20)
        payload = struct.pack(
            "<bBBB", _DEVICE_ID_BEEP, _MODE_SET,
            _FIXED_FREQ_HALF, duration_twentieths,
        )
        # SerialWrap.get_anwser 自动加锁 / 加 MC602 帧头尾 / 读响应 / 解锁
        self._serial.get_anwser(payload, time_out=0.2)

    def rest(self, duration: float = DEFAULT_DURATION_S):
        """静音一段时间（不发帧，只 sleep）。

        Args:
            duration: 时长 秒，默认 0.1s，范围 0.05-12.75
        """
        self._validate_duration(duration)
        time.sleep(duration)

    @classmethod
    def _validate_duration(cls, duration):
        if not isinstance(duration, (int, float)):
            raise TypeError(f"duration 必须是数字，收到 {type(duration).__name__}")
        if not (cls.MIN_DURATION_S <= duration <= cls.MAX_DURATION_S):
            raise ValueError(
                f"duration 须在 {cls.MIN_DURATION_S}-{cls.MAX_DURATION_S}s "
                f"(u8 协议上限)，收到 {duration}"
            )


if __name__ == "__main__":
    from link import SerialWrap

    print("== Buzzer (clean) 自检 ==")
    serial_obj = SerialWrap()
    buzzer = Buzzer(serial_obj)

    # 响 3 次
    for i in range(3):
        print(f"[{i+1}] beep()")
        buzzer.beep()
        time.sleep(0.3)

    # 不同 duration
    print("[4] beep(0.05)")
    buzzer.beep(0.05)
    time.sleep(0.2)

    print("[5] beep(0.3)")
    buzzer.beep(0.3)
    time.sleep(0.5)

    # 连响 + 休止节奏
    print("节奏：响-停-响-停...")
    for i in range(4):
        buzzer.beep(0.08)
        buzzer.rest(0.08)

    serial_obj.close()
    print("== 完成 ==")