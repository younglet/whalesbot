# _backup/ — 历史参考代码

这个目录里的代码**只用于对照参考**，不会运行、也不应在 driver 里 import。

## 文件说明

| 文件 | 来源 | 状态 |
|------|------|------|
| `mc602_ctl2.py` | 原项目 `smartcar/whalesbot/vehicle/base/mc602_ctl2.py` | 缺 `mc601_ctl2`、`logger`、`PID`、`CountRecord` 等依赖；不能跑 |
| `controller_wrap.py` | 原项目 `smartcar/whalesbot/vehicle/base/controller_wrap.py` | 同上，依赖链更深；不能跑 |

## 为什么留在项目里

抽离过程中用作对照：
- `mc602_ctl2.py` 的 `ctl602_dev_list` 记录了所有硬件的 `dev_id` 和协议格式
- `Buzzer_2` / `ScreenShow_2` 等类展示了原始协议帧怎么拼
- 帮助理解某些字段为什么是某个值（如 freq/2、duration*20）

## 为什么不能直接用

这些文件的设计前提是：
- `logger` 来自某个被删的 log 模块
- `serial_wrap` 是某个被 import 的全局单例（不是 DI）
- 依赖 `mc601_ctl2`（协议层 v1，我们抽离的是 v2）
- 用 `sys.path.append` 体操找模块

我们的新架构（`link.py` + `drivers/*.py`）已经替代了所有这些。

## 何时删除

等 Stage 7 完成后，所有抽离逻辑都稳定了，可以整个 `_backup/` 删掉。
在那之前留着做参考——尤其当某个新硬件行为异常时，可以对比原版。