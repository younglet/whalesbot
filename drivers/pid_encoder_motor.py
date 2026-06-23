"""drivers/pid_encoder_motor.py — PID 编码电机位移控制

组合 Motor + Encoder + PID，封装移动到目标脉冲数的阻塞式控制。

用法:
    from link import SerialWrap
    from drivers.pid_encoder_motor import PIDEncoderMotor

    serial_obj = SerialWrap()
    pem = PIDEncoderMotor(serial_obj, port=1)

    pem.goto(10000)   # 阻塞，移到 10000 脉冲
    pem.goto(20000)
    pem.goto(0)

    pem.stop()        # 紧急停止
"""

# Path bootstrap
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
from simple_pid import PID


class PIDEncoderMotor:
    """PID + Encoder + Motor 位移控制器。

    封装：Motor（速度控制）+ Encoder（脉冲读数）+ PID（闭环），
    提供阻塞式位移移动。
    """

    DEFAULT_KP = 0.2
    DEFAULT_KI = 0.001
    DEFAULT_KD = 0.004
    DEFAULT_MIN_SPEED = -100       # PID 输出下限
    DEFAULT_MAX_SPEED = 100        # PID 输出上限
    DEFAULT_TOLERANCE = 50         # 到达目标的脉冲容差
    DEFAULT_TIMEOUT = 5.0          # 单次移动超时（秒）
    DEFAULT_SAMPLE_TIME = 0.02     # 控制周期 20ms → 50Hz

    def __init__(
        self,
        serial,
        port=1,
        reverse=1,
        *,
        kp=DEFAULT_KP,
        ki=DEFAULT_KI,
        kd=DEFAULT_KD,
        min_speed=DEFAULT_MIN_SPEED,
        max_speed=DEFAULT_MAX_SPEED,
        tolerance=DEFAULT_TOLERANCE,
        timeout=DEFAULT_TIMEOUT,
        sample_time=DEFAULT_SAMPLE_TIME,
    ):
        """Args:
            serial:     SerialWrap 实例
            port:       电机/编码器端口号（1-4）
            reverse:    编码器方向反转，1 或 -1
            kp, ki, kd: PID 增益
            min_speed:  PID 输出下限（-100 ~ 100）
            max_speed:  PID 输出上限（-100 ~ 100）
            tolerance:  到达目标的脉冲容差
            timeout:    单次 goto 最大时长（秒），超时抛 TimeoutError
            sample_time: 控制周期（秒），None 表示每次调用都计算
        """
        # 延迟导入，避免循环依赖（兼容 python -m 和直接运行）
        try:
            from .motor import Motor
            from .encoder import Encoder
        except ImportError:
            from drivers.motor import Motor
            from drivers.encoder import Encoder

        self._motor = Motor(serial, port=port)
        self._encoder = Encoder(serial, port=port, reverse=reverse)

        self._min_speed = min_speed
        self._max_speed = max_speed
        self._pid = PID(
            Kp=kp, Ki=ki, Kd=kd,
            setpoint=0,
            output_limits=(self._min_speed, self._max_speed),
            sample_time=None  # 让 goto 里手动控制节奏
        )
        self._tolerance = tolerance
        self._timeout = timeout
        self._sample_time = sample_time  # sleep 用

        self._target = 0
        self._running = False

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def target(self):
        """当前目标脉冲数。"""
        return self._target

    @property
    def position(self):
        """当前编码器脉冲数。"""
        return self._encoder.read()

    @property
    def pid(self):
        """内部 PID 实例，可调参。"""
        return self._pid

    @property
    def speed_limits(self):
        """当前速度限幅 (min_speed, max_speed)。"""
        return (self._min_speed, self._max_speed)

    def set_speed_limits(self, min_speed, max_speed):
        """修改 PID 输出限幅。

        Args:
            min_speed: PID 输出下限（-100 ~ 100）
            max_speed: PID 输出上限（-100 ~ 100）
        """
        self._min_speed = min_speed
        self._max_speed = max_speed
        self._pid.output_limits = (min_speed, max_speed)

    # ------------------------------------------------------------------
    # 控制
    # ------------------------------------------------------------------

    def goto(self, target, *, tolerance=None, timeout=None):
        """阻塞式移动到目标脉冲数。

        Args:
            target:    目标脉冲数
            tolerance: 到达容差（覆盖实例默认值）
            timeout:   超时秒数（覆盖实例默认值）

        Returns:
            bool: True=到达目标，False=超时未到达
        """
        tol = tolerance if tolerance is not None else self._tolerance
        tmo = timeout if timeout is not None else self._timeout

        self._target = target
        self._pid.setpoint = target
        self._pid.reset()  # 清零积分，避免上一段累积冲过头
        self._running = True

        t_start = time.time()
        reached = False

        while self._running:
            current = self._encoder.read()
            if current is None:
                time.sleep(self._sample_time)
                continue

            # 检查是否到达
            if abs(current - target) <= tol:
                reached = True
                break

            # 超时检查
            if time.time() - t_start > tmo:
                break

            # PID 计算 + 驱动
            output = self._pid(current)
            self._motor.set_speed(int(output))

            time.sleep(self._sample_time)

        # 停止电机
        self._motor.set_speed(0)
        self._running = False
        return reached

    def stop(self):
        """紧急停止，中断正在执行的 goto。"""
        self._running = False
        self._motor.set_speed(0)

    def close(self):
        """停止并释放资源。"""
        self.stop()


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from link import SerialWrap

    print("== PIDEncoderMotor 自检 ==")
    serial_obj = SerialWrap()

    pem = PIDEncoderMotor(serial_obj, port=1)

    targets = [5000, 10000, 5000, 0]
    for i, t in enumerate(targets):
        print(f"[{i}] 移动到 {t}...")
        ok = pem.goto(t)
        print(f"    {'到达!' if ok else '超时'} position={pem.position}")

    pem.close()
    serial_obj.close()
    print("== 完成 ==")
