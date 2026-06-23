from link import SerialWrap
from drivers import PIDEncoderMotor

serial_obj = SerialWrap()
motor = PIDEncoderMotor(serial_obj, port=1, min_speed=-20, max_speed=70)            
targets = [10000, 20000, 10000, 0]
for i, t in enumerate(targets):
    print(f"第[{i+1}]轮： 移动到 {t}...")
    res  = motor.goto(t,timeout=3)
    print(f"    {'到达' if res else '超时'}! position={motor.position}")

motor.close()
serial_obj.close()
print("== 完成 ==")