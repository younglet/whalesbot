from drivers import Screen
from link import SerialWrap


serial_obj = SerialWrap()
screen = Screen(serial_obj)

for _ in range(100):
    screen.display(str(_))

serial_obj.close()