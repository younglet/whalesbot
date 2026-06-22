"""tools/link_test.py — link.py 的 ping 测试

测试根目录的 link.py（SerialWrap 类）能否 ping 通 MC602P。

用法（在项目根目录）: python -m tools.link_test
     或: python tools/link_test.py

要求: 插上 MC602P 控制板，运行在普通模式（非 bootloader）
"""

# Path bootstrap：让 `python tools/link_test.py` 也能跑（不需要 -m）
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from link import SerialWrap


def main():
    print("== SerialWrap ping 测试 ==")
    try:
        serial_obj = SerialWrap()
    except RuntimeError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"FAIL: 异常 {type(e).__name__}: {e}")
        sys.exit(1)

    print(f"端口:     {serial_obj.port}")
    print(f"控制器:   {serial_obj.device.name}")
    print(f"波特率:   {serial_obj.baudrate}")
    print(f"连接模式: {serial_obj.device.connect_mode}")
    print()

    # 再发一次 ping 确认链路通
    print("ping ...")
    if serial_obj.device.ping_rx(serial_obj):
        print("OK: ping 成功")
    else:
        print("FAIL: ping 无响应")
        serial_obj.close()
        sys.exit(1)

    serial_obj.close()
    print("== 串口已关闭 ==")


if __name__ == "__main__":
    main()