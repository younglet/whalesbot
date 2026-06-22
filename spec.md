# whalesbot 抽离项目 — Spec

## 项目目录结构

```
whalesbot/                              # 项目根
├── link.py                             # ★ 核心：SerialWrap（硬件链路）
├── main.py                             # 用户入口（示例）
├── _backup/                            # 历史参考（不 import、不运行）
│   ├── README.md
│   ├── mc602_ctl2.py                   # 原协议层 v2
│   └── controller_wrap.py              # 原上层包装
├── drivers/                            # ★ 用户 API（面向硬件）
│   ├── __init__.py
│   ├── buzzer.py                       # 蜂鸣器 (0x0a)
│   ├── screen.py                       # LED 矩阵屏 (0x0b)
│   ├── motor.py                        # 单路电机 + 编码器 (0x02/0x04)
│   ├── motor4.py                       # 四路电机 + 编码器 (0x01/0x03)
│   ├── bus_servo.py                    # 总线舵机 (0x06)
│   ├── pwm_servo.py                    # PWM 舵机 (0x05, 占位)
│   ├── servo.py                        # 兼容 re-export
│   ├── stepper.py                      # 步进电机 (0x11)
│   ├── analog_input.py                 # 模拟输入 (0x07/0x08)
│   ├── digital_input.py                # 数字输入（基于 AnalogInput）
│   ├── digital_output.py               # 数字输出 (0x10)
│   ├── infrared.py                     # 红外测距 (0x07,m1)
│   ├── touch.py                        # 触碰传感器 (0x07,m2)
│   ├── ultrasonic.py                   # 超声波 (0x07,m3)
│   ├── ambient_light.py                # 环境光 (0x07,m4)
│   ├── bluetooth.py                    # 蓝牙手柄 (0x09)
│   ├── board_key.py                    # 板载按键 (0x0d)
│   ├── power.py                        # 电池电压 (0x0c)
│   ├── led_light.py                    # RGB 灯条 (0x0e)
│   ├── nixietube.py                    # 数码管 (0x0f)
│   └── multi_demo.py                   # 多硬件共享 serial 演示
├── tools/                              # 辅助工具（不是主线）
│   ├── __init__.py
│   ├── link_test.py                    # SerialWrap ping 测试
│   └── firmware_flash/                 # 烧录子包
│       ├── __init__.py
│       ├── flash.py
│       └── firmware.bin
├── plan.md
└── spec.md
```

**设计原则**：
- `link.py` 是核心基础设施——放根目录，不放 `tools/`
  - 不和 `pyserial`（也叫 serial）撞名，避免 self-import 死循环
  - Stage 7 装包后变为 `whalesbot/link.py`
- `drivers/` 是面向用户 API（不依赖 `_backup/`）
- `tools/` 是辅助：测试、烧录工具
- `_backup/` 是历史代码保留作参考，**禁止 import**（依赖链不全，跑不起来）

## 来源

原本项目路径：`C:\Users\young\Documents\projects\baidu_smartcar_2026`

## 固件文件

原本 `Run.bin` 在当前项目改为了 `firmware.bin`，路径：

```
tools/firmware_flash/
├── __init__.py
├── flash.py        # 烧录函数（由 tools/download.py 改名 + 移入）
└── firmware.bin    # 固件
```

要点：`flash.py` 与 `firmware.bin` 同位于 `tools/firmware_flash/`，调用方无论在哪个目录（根目录 `main.py`、子目录、`cd` 任意位置）都能找到固件：

```python
bin_path = str(Path(__file__).resolve().parent / "firmware.bin")
```

**以 `__file__` 锚定**，不依赖 CWD。若调用方想用别的固件，显式传 `bin_path` 参数即可。

## driver 与 SerialWrap 的关系：依赖注入（DI）

driver **不自动**拿 serial，**构造时显式传入**。原因：
- **多硬件 → 1 serial**：buzzer/led/motor 共享同一个 SerialWrap，靠内部 lock 串行化
- **多串口**：不干扰，以后接 2 块 MC602 也可以
- **可测**：可注入 mock serial 跑单元测试

**API 模式（变量全名，不简写）：**

```python
from link import SerialWrap
from drivers.buzzer import Buzzer
from drivers.led    import Led       # Stage 4+
from drivers.motor  import Motor     # Stage 5+

serial_obj = SerialWrap()            # 1 个串口（不叫 sw）
buzzer = Buzzer(serial_obj)          # 多个 driver 共享
led    = Led(serial_obj)
motor  = Motor(serial_obj)

buzzer.beep(0.2)                     # 蜂鸣器 API 已简化：不接受 freq
led.set_color(0, 255, 0, 0)
motor.set_speed(0.5)
```

**反面例子（**❌** 不要这样）：**
```python
sw = SerialWrap()                    # ❌ 简写，不清晰
buzzer = Buzzer(sw)

sw = SerialWrap()
buzzer = Buzzer()                    # ❌ 隐式从全局拿
```

多 driver 共享 1 serial 的 demo：`python -m drivers.multi_demo`

## Driver 入口约定：自举路径

所有 driver 文件**顶部**都要包含路径自举：

```python
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
```

**为什么**：
- `python drivers/<hw>.py` 直接跑也能成（不需要 `-m`）
- 开发单个 driver 调试更方便
- 幂等：被多次 import 时不会重复加
- Stage 7 装成 package 后，路径自动在 sys.path 里，本段成为无害冗余

**两种入口都能跑**：
```bash
python -m drivers.buzzer     # 传统方式，始终可用
python drivers/buzzer.py     # 直接执行，自举后可用
```

## 命名约定

### 变量名（不简写）

| 不用 | 用 |
|------|-----|
| `sw` | `serial_obj` |
| `self.dev` | `self.device` |
| `dev_list` | `devices` |
| `ctl_dev` | `controller` |
| `dur` | `duration` |
| `tmp` | 直接 inline，别用临时变量 |

理由：`sw` / `dev` 等简写让初次阅读的人费解。全名让代码自解释。

### 参数命名

| 不用 | 用 | 说明 |
|------|-----|------|
| `port_id` | `port` | 所有驱动统一用 `port` |
| `port_id` (bus_servo) | `port` | 总线舵机 ID 也用 `port`（1-255） |

`AnalogInput` 的特殊约定：
```python
# 一个类兼容两路硬件接口
AnalogInput(serial, port=1)                        # 默认 rj45 水晶头 (0x07)
AnalogInput(serial, port=1, port_type="dupont")   # 杜邦头 (0x08)
```

`digital_output.py` / `digital_input.py` 命名与 `analog_input.py` 对齐（全称+下划线）。

### 文件命名

- `<hw>.py`：抽离后的干净 driver（不依赖 `_backup/`，公开 API）
- `_backup/<file>.py`：历史参考代码（**不要 import**）
- `tools/<test>.py`：测试脚本