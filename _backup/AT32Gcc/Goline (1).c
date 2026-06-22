#ifndef EXTERNLIB_STEPDRIVER_H_
#define EXTERNLIB_STEPDRIVER_H_
#ifdef EXTERNLIB_STEPDRIVER_H_
#include "serial_protocol.h"

//对应3个步进电机
#define STP_MOT_CH1   1
#define STP_MOT_CH2   2
#define STP_MOT_CH3   3

//设置步进电机旋转，speed：-10000~10000，（根据不同步进电机，确定最大可设定速度）
void set_stepmotor(int ch,int speed);

void set_step_vel(int ch,float angular);
//获取步进驱动器的步进计数
int get_stepmotor_distance(int ch);
// 获取步进转动的弧度
float get_stepmotor_rad(int ch);

//电机加减速平滑程度：acc: 0~16000（数值越大,加速度越快）
void set_stepmotor_acc(int ch,int acc);

//复位步进电机驱动器，释放电机力矩
void set_stepmotor_reset(void); 

// 橙色舵机相关
#define SERVO_BUS_MAX 18
// 定义一个循环队列，存放舵机的相关数据
# define SERVO_BUS_QUEUE_MAX 20

#pragma pack(push,1)    //可以指定结构的对齐和补齐的字节数
typedef struct _servo_bus{
	enum cmd_type cmd_type;
    int8_t port_id;
	int8_t mode;
    int8_t speed;
	int16_t angle;
}servo_bus_cmd_t;

#pragma pack(pop)       //恢复push前的值

void servo_bus_apend(servo_bus_cmd_t* servo_bus);
void get_my_servo_bus(servo_bus_cmd_t* servo_bus);
void set_my_servo_bus(servo_bus_cmd_t* servo_bus);
#endif
#endif

