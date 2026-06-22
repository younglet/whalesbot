"""drivers/bluetooth.py — 蓝牙手柄 driver

dev_id=0x09 (bluetooth)

读取蓝牙手柄的摇杆值和按键状态。

用法:
    python -m drivers.bluetooth       # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.bluetooth import BluetoothPad
        serial_obj = SerialWrap()
        pad = BluetoothPad(serial_obj)
        sticks, buttons = pad.read()   # sticks: [lx,ly,rx,ry], buttons: bitmask

协议帧:
    读取: struct.pack("<bBBBBi", 0x09, 0x00, 0,0,0,0, 0)
    响应: dev_id(1) + mode(1) + lx(1) + ly(1) + rx(1) + ry(1) + buttons(4)

摇杆原始值范围约 40~160，中位 ~97。
按键 bitmask:
    bit0=上, bit1=下, bit2=左, bit3=右
    bit4~bit15: 其他按键 (10,11,12,13,14,15 等)

手柄布局参考 _backup/controller_wrap.py:
    ╭────╮                            ╭────╮
    | 10 |                            | 11 |
    ╭╰════╯────────────────────────────╰════╯╮
    │  ╭────╮       WhalesBot        ╭────╮  │
    │  │ 12 │                        │ 13 │  │
    │  ╰────╯  ╭──╮            ╭──╮  ╰────╯  │
    │          │14│            │15│          │
    │  ╭───────╰══╯╮          ╭╰══╯───────╮  │
    │  │     0     │          │     4     │  │
    │  │ 1 < 8 > 3 │          │ 7 < 9 > 5 │  │
    │  │     2     │          │     6     │  │
    │  ╰───────────╯          ╰───────────╯  │
    ╰────────────────────────────────────────╯

实现参考:
    _backup/mc602_ctl2.py: BluetoothPad_2
    _backup/controller_wrap.py: BluetoothPad
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

_DEVICE_ID_BLUETOOTH = 0x09

# 摇杆校准默认值
_DEFAULT_STICK_CENTER = [97, 97, 97, 97]
_DEFAULT_STICK_MIN = 40
_DEFAULT_STICK_MAX = 160
_MARGIN = 6

# 按键 bit 定义
BTN_UP = 0       # D-pad 上
BTN_DOWN = 1     # D-pad 下
BTN_LEFT = 2     # D-pad 左
BTN_RIGHT = 3    # D-pad 右
BTN_10 = 10
BTN_11 = 11
BTN_12 = 12
BTN_13 = 13
BTN_14 = 14
BTN_15 = 15


# ---------------------------------------------------------------------------
# BluetoothPad
# ---------------------------------------------------------------------------

class BluetoothPad:
    """蓝牙手柄（dev_id=0x09）。

    读取摇杆位置和按键状态，摇杆自动归一化到 [-1.0, 1.0]。
    """

    def __init__(self, serial):
        """Args:
            serial: SerialWrap 实例
        """
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"bluetooth 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial

        # 摇杆校准参数
        self.stick_center = list(_DEFAULT_STICK_CENTER)
        self.stick_min = _DEFAULT_STICK_MIN
        self.stick_max = _DEFAULT_STICK_MAX
        self.margin = _MARGIN

    def read_raw(self):
        """读取原始值（不归一化）。

        Returns:
            tuple: (sticks, buttons)
                sticks: [lx, ly, rx, ry] 原始值 (约 40-160)
                buttons: 按键 bitmask，或 None（超时）
        """
        payload = struct.pack(
            "<bBBBBi",
            _DEVICE_ID_BLUETOOTH, 0,
            0, 0, 0, 0,
        )
        res = self._serial.get_anwser(payload, time_out=0.3)
        if res is not None and len(res) >= 9:
            # 响应 (与 mc602_ctl2.py BluetoothPad_2 一致):
            #   dev_id(1,b) + lx(1,U) + ly(1,U) + rx(1,U) + ry(1,U) + buttons(4,signed)
            #   共 9 字节，无 mode 字段
            lx, ly, rx, ry, buttons = struct.unpack("<BBBBi", res[1:9])
            return [lx, ly, rx, ry], buttons
        elif res is not None:
            # DEBUG: 响应太短，打印实际数据帮助调试协议
            print(f"  [DEBUG] 蓝牙响应长度异常: len={len(res)}, hex={res.hex(' ')}")
        return None

    def read(self):
        """读取归一化摇杆值和按键。

        Returns:
            tuple: (sticks, buttons)
                sticks: [lx, ly, rx, ry]，每轴归一化到 [-1.0, 1.0]
                buttons: 按键 bitmask
            None: 超时
        """
        raw = self.read_raw()
        if raw is None:
            return None

        sticks_raw, buttons = raw
        sticks = []
        for i, val in enumerate(sticks_raw):
            diff = val - self.stick_center[i]
            if abs(diff) < self.margin:
                sticks.append(0.0)
            elif diff > 0:
                divisor = self.stick_max - self.stick_center[i] - self.margin
                sticks.append(min(1.0, (diff - self.margin) / divisor))
            else:
                divisor = self.stick_center[i] - self.stick_min - self.margin
                sticks.append(max(-1.0, (diff + self.margin) / divisor))
        return sticks, buttons

    def calibrate(self, samples=5):
        """校准摇杆中位。

        Args:
            samples: 采样次数（手柄需要保持中位不动）
        """
        sums = [0, 0, 0, 0]
        for _ in range(samples):
            raw = self.read_raw()
            if raw:
                s, _ = raw
                for i in range(4):
                    sums[i] += s[i]
            time.sleep(0.05)
        for i in range(4):
            avg = sums[i] // samples
            if abs(avg - _DEFAULT_STICK_CENTER[i]) < 10:
                self.stick_center[i] = avg

    def button(self, btn_bit):
        """检查指定按键是否按下。

        Args:
            btn_bit: 按键 bit (0-15)，可用 BTN_UP, BTN_DOWN 等常量

        Returns:
            bool: 是否按下
        """
        raw = self.read_raw()
        if raw is None:
            return False
        _, buttons = raw
        return (buttons >> btn_bit) & 1 == 1


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== BluetoothPad 自检（10 秒，请操作手柄）==")
    serial_obj = SerialWrap()
    pad = BluetoothPad(serial_obj)

    # 校准一次
    print("校准中位...（请勿触碰摇杆）")
    pad.calibrate(samples=10)
    print(f"  中位: {pad.stick_center}")

    start = time.time()
    while time.time() - start < 10:
        result = pad.read()
        if result:
            sticks, buttons = result
            print(f"  摇杆: {[f'{s:.2f}' for s in sticks]}  按键: 0x{buttons:04X}")
        time.sleep(0.15)

    serial_obj.close()
    print("== 完成 ==")
