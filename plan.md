# whalesbot 抽离执行计划

## 总体策略

参考方案里"每个硬件类独立可测"的设计原则，按**搬过来 → 协议测 → 验证 → 封装 driver** 的节奏，逐块落地。
复杂模块依赖简单模块，所以**从最简硬件开始**，每一步必须真硬件跑通再进下一步。

> **mock 暂不做**——原方案里"无硬件自动 mock"的特性推迟，等全部 driver 落地后再补。需要测无硬件的代码就用真硬件临时断开。

## 节奏模板（每类硬件）

1. 搬 `*Cmd` 到 `tools/`，独立可跑
2. 写 `tools/<hw>_test.py`，直接对 `*Cmd` 发协议帧
3. 真硬件验证 → 看 / 听 / 读真实数据
4. 封装成 `whalesbot/drivers/<hw>.py` 的面向用户类
5. 写 `__main__` 测试，`python -m whalesbot.drivers.<hw>` 可直接跑

---

## Stage 1 — 串口基础设施

**目标**：在 `tools/` 跑通一条 ping 链路。

- [x] 搬 `SerialWrap` → `link.py`（项目根，核心基础设施位置）
- [x] 写 `tools/link_test.py`（原 tools/serial_test.py 改名）：
  - 接真硬件 → 打印 ping 响应
  - 列出可用串口、连第一个试 ping
- **完成标志**：能 ping 到真硬件
- **风险点**：`SerialWrap` 自动烧录逻辑复杂，先看是否能在没硬件的机器上不进入烧录流程

---

## Stage 2 — 协议骨架

**目标**：把协议基类搬过来，所有 `*Cmd` 的父类就位。

- [ ] 搬 `DevCmdInterface` / `DevListWrap` → `tools/_mc602.py`
- [ ] 写 `tools/protocol_test.py`：构造一个假 `*Cmd`，验证 pack → send → unpack 闭环
- **完成标志**：基类的并发 / 帧同步 / 校验逻辑都覆盖到

---

## Stage 3 — 第一个硬件：蜂鸣器（最简，跳板）

**目标**：走通"原本测试 → 抽离干净"两阶段模板。

**Step 1：原本测试（依赖 mc602_ctl2）**
- [x] 搬 `Buzzer_2` → `drivers/buzzer_.py`（API：`beep(freq, duration)` + 校验）—— **待改名**
- [x] `python -m drivers.buzzer_` 真硬件 6 beep OK

**Step 2：抽离干净（不依赖 mc602_ctl2）**
- [x] 重写 `drivers/buzzer.py`：直接用 `link.py` 发协议帧，struct.pack 构造 payload
- [ ] `python -m drivers.buzzer` 真硬件验证（结果应与 Step 1 一致）

**完成标志**：两个文件都能跑，结果一致 → 协议理解到位

## 两阶段抽离通用模板（Stage 4-6 都照抄）

| 步骤 | 文件 | 内容 | 依赖 |
|------|------|------|------|
| Step 1a | `tools/<hw>_test.py` | 协议层直调 `<hw>_2` 类 | mc602_ctl2 |
| Step 1b | `drivers/<hw>_.py` | 包装 `<hw>_2` + 参数校验 | mc602_ctl2 |
| Step 2  | `drivers/<hw>.py`  | 自己 struct.pack + SerialWrap | ❌ 不依赖 |

---

## Stage 4 — 输出类：LED / 数码管 / 屏幕（中等）

按 Stage 3 模板逐个：

- [ ] `LedLight` → `drivers/output.py`
- [ ] `NixieTube` / `ScreenShow` / `Battry` → `drivers/display.py`
- [ ] `PoutD` → `drivers/output.py`（气泵 / 阀门）
- **完成标志**：4 个 driver 都能调通

---

## Stage 5 — 复杂硬件：电机 / 舵机

- [ ] `Motor` / `Motors` / `Motor4` / `MotorWrap` / `MotorConvert` → `drivers/motor.py`
- [ ] `StepperWrap` → `drivers/stepper.py`
- [ ] `ServoPwm` / `ServoBus` → `drivers/servo.py`
- [ ] 搬 `tools.py` 的 `CountRecord` / `limit_val` 到 `whalesbot/tools.py`
- **完成标志**：电机能调速 + 读编码器，舵机能转角度 + 读位置

---

## Stage 6 — 输入类：传感器 / 按键

- [ ] `AnalogInput` / `AnalogInput2` / `Infrared` → `drivers/sensor.py`
- [ ] `Key4Btn` / `BoardKey` / `BluetoothPad` → `drivers/keypad.py`
- **完成标志**：能读 AD 值、红外距离、按键状态（含长 / 短按识别）

---

## Stage 7 — 包壳收尾

- [ ] 建 `whalesbot/__init__.py`：`init(serial)` / `get_serial()`（**必传** serial，不做 mock fallback）
- [ ] 改所有 driver 的 import 路径，统一从 `whalesbot` 入口拿串口
- [ ] 搬 `tools.py` → `whalesbot/tools.py`
- [ ] 搬 `download.py` → `whalesbot/download.py`（烧录也算库能力）
- [ ] 写 README 快速开始、examples
- **完成标志**：`whalesbot_抽离方案.md` 里的目录结构 1:1 落地

---

## 验证策略

每个 Stage 完成 = 两件套：
1. ✅ 真硬件跑通（看 / 听 / 读真实数据）
2. ✅ 留下可复现的测试脚本（`<hw>_test.py` 或 `__main__`）

任一 Stage 不通过 → 修通再进下一个，**不跳过**。

## 延期项（不阻塞主线）

- `whalesbot/_mock/` — 无硬件自动 mock 模式
- `whalesbot.init()` 不传参 → 走 mock 的 fallback

---

## 驱动清单（全部完成 ✅）

参见上方 "已完成的 driver" 表格。

## 待办

- [ ] Stage 7：包壳收尾

---

**每个 driver 的实现模板**（从 `drivers/buzzer.py` / `drivers/screen.py` 照抄）：
1. Path bootstrap 顶部
2. 协议常量从 `_backup/mc602_ctl2.py:ctl602_dev_list` 复制（`_DEVICE_ID_*` / `_MODE_SET`）
3. class `__init__(self, serial)` — DI，校验设备
4. struct.pack 构造 payload → `self._serial.get_anwser(payload)`
5. `__main__` 自检 + 3s 间隔 + 用户友好的 print
6. 真硬件跑通 → 更新 plan.md 此清单打勾

- ✅ Stage 0：基础设施 — `tools/firmware_flash/{flash.py, firmware.bin}` 就位
- ✅ Stage 1：SerialWrap（`link.py` + `tools/link_test.py`）—— COM7 实际 ping 通过
- ✅ Stage 2：协议骨架（`_backup/mc602_ctl2.py`，DevCmdInterface + 21 个 *_2 类）
- ✅ Stage 3：`drivers/buzzer.py`（抽离干净版，6 beep OK）
  - 简化 API：`beep(duration=0.1)` + `rest(duration=0.1)`，不接受 freq
- ✅ Stage 4 部分：`drivers/screen.py`（LED 矩阵屏 5×20，powered by\nwhalesbot + @逐行填满动画）
- ✅ DI + bootstrap：所有 driver 顶部自举路径，双入口都能跑
- ✅ `drivers/multi_demo.py` 验证多实例共享 serial + lock 串行化（Buzzer + Screen）
- ✅ 重构：`tools/serial.py` → 根目录 `link.py`（核心基础设施不在 tools/）
- ✅ 清理：`buzzer_.py` / `screen_.py` / `beep_test.py` 删除（`<hw>_.py` 双版本模式废弃）
- ✅ 清理：`mc602_ctl2.py` + `controller_wrap.py` 移到 `_backup/`（加 README 说明）
- ✅ 命名：全量去简写（`sw` → `serial_obj`, `dev` → `device`, `dur` → `duration` 等）
- ✅ 协议修复：所有 driver 的 `len(res)` 守卫条件修复（6 个文件，切片需要精确匹配）
- ✅ 协议修复：`bluetooth.py` 响应格式修正（9 字节，无 mode 字段）
- ✅ 传感器拆分：`sensor.py` → `analog_input.py` / `infrared.py` / `touch.py` / `ultrasonic.py` / `ambient_light.py`
- ✅ `AnalogInput` + `AnalogInput2` 合并为单类：`port_type="rj45"`（默认）/ `"dupont"`，`port_id` → `port`
- ✅ 新增：`digital_input.py`（基于 AnalogInput 阈值判断）
- ✅ 新增：`digital_output.py`（原 `dout.py` 改名，`DigitalOut` → `DigitalOutput`）
- ✅ 新增：`stepper.py`（dev_id=0x11，补全协议列表最后缺失项）
- ✅ 全量重命名：所有 driver 的 `port_id` → `port`（Python 标识符层面）
- ✅ `motor.py` / `bus_servo.py` 重写修复不一致状态
- ✅ 21/21 协议设备全覆盖

## 已完成的 driver（全部 21 设备）

| dev_id | driver 文件 | 类名 | 状态 |
|--------|------------|------|------|
| 0x01 | motor4.py | Motor4 | ✅ |
| 0x02 | motor.py | Motor | ✅ |
| 0x03 | motor4.py | Encoder4 | ✅ |
| 0x04 | motor.py | EncoderMotor | ✅ |
| 0x05 | pwm_servo.py | PWMServo | ✅ (占位) |
| 0x06 | bus_servo.py | BusServo | ✅ |
| 0x07,m0 | analog_input.py | AnalogInput | ✅ (port_type="rj45") |
| 0x07,m1 | infrared.py | Infrared | ✅ |
| 0x07,m2 | touch.py | Touch | ✅ |
| 0x07,m3 | ultrasonic.py | Ultrasonic | ✅ |
| 0x07,m4 | ambient_light.py | AmbientLight | ✅ |
| 0x08 | analog_input.py | AnalogInput | ✅ (port_type="dupont") |
| 0x09 | bluetooth.py | BluetoothPad | ✅ |
| 0x0a | buzzer.py | Buzzer | ✅ |
| 0x0b | screen.py | Screen | ✅ |
| 0x0c | power.py | Power | ✅ |
| 0x0d | board_key.py | BoardKey | ✅ |
| 0x0e | led_light.py | LedLight | ✅ |
| 0x0f | nixietube.py | NixieTube | ✅ |
| 0x10 | digital_output.py | DigitalOutput | ✅ |
| 0x11 | stepper.py | Stepper | ✅ |

额外 driver（非协议设备）：
- `digital_input.py` — DigitalInput（基于 AnalogInput 阈值）
- `servo.py` — 兼容 re-export（BusServo + PWMServo）
