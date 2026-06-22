"""drivers/board_key.py — 板载按键 driver

dev_id=0x0d (board_key)

读取控制器板载 4 个按键状态。

用法:
    python -m drivers.board_key      # 自检
    或在自己的脚本里:
        from link import SerialWrap
        from drivers.board_key import BoardKey
        serial_obj = SerialWrap()
        keys = BoardKey(serial_obj)
        states = keys.read()          # [K1, K2, K3, K4] 每个 0/1

按键编号: K1=左, K2=右, K3=上(ENTER), K4=下(ESC)

协议帧:
    读取: struct.pack("<bbbb", 0x0d, 0x00, 0, 0)
    响应: dev_id(1) + mode(1) + k1(1) + k2(1) + k3(1) + k4(1)

实现参考:
    _backup/mc602_ctl2.py: BoardKey_2
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

_DEVICE_ID_BOARD_KEY = 0x0d

# 按键索引
KEY_LEFT = 0     # K1 - 左
KEY_RIGHT = 1    # K2 - 右
KEY_ENTER = 2    # K3 - 上/确认
KEY_ESC = 3      # K4 - 下/返回


# ---------------------------------------------------------------------------
# BoardKey
# ---------------------------------------------------------------------------

class BoardKey:
    """板载按键（dev_id=0x0d）。

    四个按键: K1(左), K2(右), K3(ENTER), K4(ESC)。
    返回值: 0=松开, 1=按下。
    """

    NUM_KEYS = 4

    def __init__(self, serial):
        if serial is None:
            raise TypeError("serial 不能为 None")
        if not hasattr(serial, "device") or not hasattr(serial, "get_anwser"):
            raise TypeError(f"serial 必须是 SerialWrap 实例，收到 {type(serial).__name__}")
        if not serial.device.name.startswith("mc602"):
            raise RuntimeError(f"board_key 仅支持 MC602，当前设备 {serial.device.name}")
        self._serial = serial

    def read(self):
        """读取所有按键状态。

        Returns:
            list[int]: [K1, K2, K3, K4] 每键 0/1，或 None
        """
        payload = struct.pack("<bbbb", _DEVICE_ID_BOARD_KEY, 0, 0, 0)
        res = self._serial.get_anwser(payload, time_out=0.15)
        if res is not None and len(res) >= 6:
            # 响应: dev_id(1) + mode(1) + k1(1) + k2(1) + k3(1) + k4(1)
            return list(struct.unpack("<bbbb", res[2:6]))
        elif res is not None:
            # DEBUG: 响应太短，打印实际数据帮助调试协议
            print(f"  [DEBUG] 按键响应长度异常: len={len(res)}, hex={res.hex(' ')}")
        return None

    def is_pressed(self, key_index):
        """检查指定按键是否按下。

        Args:
            key_index: KEY_LEFT, KEY_RIGHT, KEY_ENTER, KEY_ESC
        """
        states = self.read()
        if states is None:
            return False
        return states[key_index] == 1


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== BoardKey 自检（10 秒，请按键）==")
    serial_obj = SerialWrap()
    keys = BoardKey(serial_obj)

    names = ["左(K1)", "右(K2)", "ENTER(K3)", "ESC(K4)"]

    start = time.time()
    while time.time() - start < 10:
        states = keys.read()
        if states:
            pressed = [names[i] for i, s in enumerate(states) if s == 1]
            if pressed:
                print(f"  按下: {', '.join(pressed)}")
        time.sleep(0.1)

    serial_obj.close()
    print("== 完成 ==")
