"""drivers/screen.py — LED 矩阵屏 driver（抽离干净版）

不依赖 _backup/mc602_ctl2.py，直接构造协议帧 + 用 SerialWrap 发送。

屏幕规格：
    5 行 × 20 字符 = 100 字符（与 MAX_CHARS 对应）
    \n 换行；超出 100 字符截断

用法：
    python -m drivers.screen          # 自检
    python drivers/screen.py          # 也可以（自举路径）
    或在自己的脚本里：
        from link import SerialWrap
        from drivers.screen import Screen
        serial_obj = SerialWrap()
        screen = Screen(serial_obj)
        screen.display("Hello")

协议帧：
    payload = struct.pack("<bb" + "b"*100,
        device_id=0x0B,   # 屏幕设备 ID
        mode=0x02,        # set 操作
        *100_chars        # ASCII 码（不足补 0，超 100 截断）
    )
    MC602 send_cmd 自动加 header (77 68) + len + tail (0A)
"""

# Path bootstrap：让 `python drivers/screen.py` 也能跑（不需要 -m）
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
import struct


# ---------------------------------------------------------------------------
# 协议常量
# ---------------------------------------------------------------------------

_DEVICE_ID_SCREEN = 0x0B  # LED 矩阵屏设备 ID（来自 _backup/mc602_ctl2 的 ctl602_dev_list["led_show"]）
_MODE_SET = 0x02           # set 操作（来自 DevCmdInterface.set）


class Screen:
    """LED 矩阵屏面向用户的简洁 API。

    协议层硬约束：100 字符（ASCII 0-127），其他字符拒绝。
    """

    MAX_CHARS = 100

    def __init__(self, serial):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(
                f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}"
            )
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(
                f"screen 仅支持 MC602，当前设备 {serial.device.name}"
            )
        self._serial = serial

    def display(self, text: str):
        """在 LED 矩阵屏上显示文本。

        Args:
            text: ASCII 字符串，最多 100 字符（超出截断）
        """
        if not isinstance(text, str):
            raise TypeError(f"text 必须是 str，收到 {type(text).__name__}")
        # ASCII 校验（signed 'b' 范围 -128~127）
        for c in text:
            if ord(c) > 127:
                raise ValueError(
                    f"screen 只支持 ASCII (0-127)，收到非 ASCII 字符: {c!r} "
                    f"(ord={ord(c)})"
                )
        # 截断到 MAX_CHARS（保留前 100 字符）+ 补 0 到 100
        char_codes = [ord(c) for c in text[:self.MAX_CHARS]]
        char_codes.extend([0] * (self.MAX_CHARS - len(char_codes)))
        # 构造 payload：device_id (signed b) + mode (signed b) + 100 chars (signed b)
        payload = struct.pack(
            "<bb" + "b" * self.MAX_CHARS,
            _DEVICE_ID_SCREEN, _MODE_SET, *char_codes
        )
        # SerialWrap.get_anwser 自动加锁 / 加 MC602 帧头尾 / 读响应 / 解锁
        self._serial.get_anwser(payload, time_out=0.5)

    def clear(self):
        """清空屏幕"""
        self.display("")


if __name__ == "__main__":
    from link import SerialWrap

    print("== Screen (clean) 自检 ==")
    serial_obj = SerialWrap()
    screen = Screen(serial_obj)

    # 1. 品牌多行（占 2 行）
    text = "powered by\nwhalesbot"
    print(f"显示 {text!r} (len={len(text)})...")
    screen.display(text)
    time.sleep(3)

    # 2. @ 逐行填满（5 行 × 20 字符，每行 1s）
    print("@ 逐行填满（5 行 × 20 字符，每行 1s）...")
    for row in range(1, 6):
        n = row * 20
        screen.display("@" * n)
        print(f"  第 {row} 行填满（{n} 字符）")
        time.sleep(1)
    # 铺满后保持
    time.sleep(2)

    # 3. 清空
    print("清空屏幕...")
    screen.clear()

    serial_obj.close()
    print("== 完成（请看屏幕确认） ==")