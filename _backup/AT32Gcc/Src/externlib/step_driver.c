// #include "whalesbot.h"
#include "step_driver.h"



#define STEP_DRIVERID  100   //电机驱动卡ID号
#define STEP_REG_SPD   6     //驱动卡3号电机对应的速度寄存器编号
#define STEP_DT        0.01  //时间间隔
#define STEP_SPD_MAX   6000  //电机最大速度

#define STEP_SPD_MIN   50//300   //电机最小速度
//写总线舵机
#define StepDriver_LEN      14
#define StepDriver_REVLEN   10
static uint8_t StepDriver_Buffer[StepDriver_LEN]={0};
static int StepDriverIndex=0;
static uint8_t StepDriver_RevBuffer[StepDriver_REVLEN*2]={0};


const static float step2rad = 3.141592654/180 * 1.8 / 16;
#define MAXSPED 8000

//3路电机目标速度
static float step_spd1=0;
static float step_spd2=0;
static float step_spd3=0;

//驱动器反馈的PWM计数
static int step_distance1=0;
static int step_distance2=0;
static int step_distance3=0;

static float SPD_ACC_1   =800;
static float SPD_ACC_2   =800;
static float SPD_ACC_3   =800;

static int isInit=false;
static int isReset=false;

static int step_spd1_now=0;
static int step_spd2_now=0;
static int step_spd3_now=0;

static int StepDriver_WriteRegister(int id, int Reg, int spd1,int spd2,int spd3)
{
    StepDriver_Buffer[0] = 0xFF;
    StepDriver_Buffer[1] = 0xFF;
    StepDriver_Buffer[2] = id;
    StepDriver_Buffer[3] = StepDriver_LEN-4;//发送长度
    StepDriver_Buffer[4] = 0x07;//写入指令
    StepDriver_Buffer[5] = Reg;
    StepDriver_Buffer[7] =  (uint8_t)((  spd1 >> 8) & 0x000000ff);
    StepDriver_Buffer[8] =  (uint8_t)(   spd1  &      0x000000ff); 
    StepDriver_Buffer[9] =  (uint8_t)((  spd2 >> 8) & 0x000000ff);
    StepDriver_Buffer[10] = (uint8_t)(   spd2  &      0x000000ff); 
    StepDriver_Buffer[11] = (uint8_t)((  spd3 >> 8) & 0x000000ff);
    StepDriver_Buffer[12] = (uint8_t)(   spd3  &      0x000000ff); 
    StepDriver_Buffer[13] = calchecksum(StepDriver_Buffer);
    UartPort485_Sendbytes(StepDriver_Buffer, StepDriver_LEN);
    return 0;
}




static void StepDriver_RevCallBack(uint8_t revdata)
{
    if(StepDriverIndex == 0 && revdata==0xff)
    {
        StepDriver_RevBuffer[0]=0xff;
        StepDriverIndex=StepDriverIndex+1;
    }
    else if(StepDriverIndex >=1 && StepDriver_RevBuffer[0]==0xff)
    {
        StepDriver_RevBuffer[StepDriverIndex]=revdata;
        StepDriverIndex++;
        if(StepDriverIndex>StepDriver_REVLEN)
            StepDriverIndex=0;
    }
    else
    {
        StepDriverIndex=0;
        StepDriver_RevBuffer[0]=0;
        StepDriver_RevBuffer[1]=0;
    }
}


static int accaplay(int vel_now,int vel_dis,int acc)
{
    if(vel_dis > (vel_now))
    {
        (vel_now) += acc;
        if((vel_now) > vel_dis)
            (vel_now) = vel_dis;
    }
    else if(vel_dis < (vel_now))
    {
        (vel_now) -= acc;
        if((vel_now) < vel_dis)
            (vel_now) = vel_dis;
    }
    else
    {
        (vel_now) = vel_dis;
    }
    return vel_now;
}


static int16_t servos_bus[SERVO_BUS_MAX];

static int16_t servos_rotation[SERVO_BUS_MAX];

void set_my_servo_bus(servo_bus_cmd_t* servo_bus){
	
	switch(servo_bus->mode){
		case 1:
			// set_servo_angle(servo_bus->port_id, servo_bus->speed, servo_bus->angle);
            for(int i=0;i<5;i++)
            {
                PO16_WriteRegister_NoWait(servo_bus->port_id, 32 , to_servo_speed(servo_bus->speed)) ;
                wait(0.001);                 
                PO16_WriteRegister_NoWait(servo_bus->port_id, 30 , angle_to_servo_value(servo_bus->angle));
                wait(0.001); 
            }
			servos_bus[servo_bus->port_id-1] = servo_bus->angle;
			break;
		case 2:
			set_servo_rotation(servo_bus->port_id, servo_bus->speed);
			servos_rotation[servo_bus->port_id-1] = servo_bus->speed;
			break;
	}
}

void get_my_servo_bus(servo_bus_cmd_t* servo_bus){
	switch (servo_bus->mode){
		case 0:
			servo_bus->speed = servos_rotation[servo_bus->port_id-1];
			break;
		case 1:
			servo_bus->angle = servos_bus[servo_bus->port_id-1];
			break;
	}
}


static servo_bus_cmd_t servo_bus_cmd_queue[SERVO_BUS_QUEUE_MAX];
static uint8_t servo_bus_index_front = 0;
static uint8_t servo_bus_index_rear = 0;

void servo_bus_init(){
	for(int i=0; i<20; i++){
		servo_bus_cmd_queue[i].cmd_type = RESET_CMD;
		servo_bus_cmd_queue[i].port_id = 0;
		servo_bus_cmd_queue[i].mode = 0;
		servo_bus_cmd_queue[i].speed = 0;
		servo_bus_cmd_queue[i].angle = 0;
	}
}

// 队列加入命令
void servo_bus_apend(servo_bus_cmd_t* servo_bus){
	// 判断是否满，满了就不加入
	if((servo_bus_index_rear+1)%SERVO_BUS_QUEUE_MAX == servo_bus_index_front){
		return;
	}
	servo_bus_cmd_queue[servo_bus_index_rear].cmd_type = servo_bus->cmd_type;
	servo_bus_cmd_queue[servo_bus_index_rear].port_id = servo_bus->port_id;
	servo_bus_cmd_queue[servo_bus_index_rear].mode = servo_bus->mode;
	servo_bus_cmd_queue[servo_bus_index_rear].speed = servo_bus->speed;
	servo_bus_cmd_queue[servo_bus_index_rear].angle = servo_bus->angle;
	// 更新到下一个位置
	servo_bus_index_rear = (servo_bus_index_rear+1)%SERVO_BUS_QUEUE_MAX;
}



//多线程处理电机加减速过程
static void StepMotorThread()
{
    int step1=0;
    int step2=0;
    int step3=0;
    servo_bus_init();
    while (true)
    {
        //电机进行加减速控制,通道1
        step_spd1_now = accaplay(step_spd1_now,step_spd1,SPD_ACC_1);
        step_spd2_now = accaplay(step_spd2_now,step_spd2,SPD_ACC_2);
        step_spd3_now = accaplay(step_spd3_now,step_spd3,SPD_ACC_3);

        if(abs(step_spd1_now) < STEP_SPD_MIN)
            step1 = 0;
        else
            step1 = step_spd1_now;
        if(abs(step_spd2_now) < STEP_SPD_MIN)
            step2 = 0;   
        else
            step2 = step_spd2_now; 
        if(abs(step_spd3_now) < STEP_SPD_MIN)
            step3 = 0;      
        else
            step3 = step_spd3_now;   
        if(isReset == true)
        {
            Servo_Reset(STEP_DRIVERID);
        }
        else
        {
            StepDriver_WriteRegister(STEP_DRIVERID,STEP_REG_SPD,step1,step2,step3);
        }
        //配置接收
        StepDriverIndex=0;
        StepDriver_RevBuffer[0]=0;
        StepDriver_RevBuffer[1]=0;
        setUartPort485_RxHandle((FunType)StepDriver_RevCallBack);//配置接收回调函数
        //释放CPU给其他线程
        wait(STEP_DT);
        
        //读取驱动器反馈的数据
        if( StepDriver_RevBuffer[0]==0xff && 
            StepDriver_RevBuffer[1]==0xff && 
            StepDriver_RevBuffer[2]==STEP_DRIVERID && 
            StepDriver_RevBuffer[StepDriver_REVLEN-1] == calchecksum(StepDriver_RevBuffer))
        {
            // step_distance1=StepDriver_RevBuffer[7]*0x1000000 + StepDriver_RevBuffer[8]*0x10000 + StepDriver_RevBuffer[9]*0x100+ StepDriver_RevBuffer[10];
            // step_distance2=StepDriver_RevBuffer[11]*0x1000000 + StepDriver_RevBuffer[12]*0x10000 + StepDriver_RevBuffer[13]*0x100+ StepDriver_RevBuffer[14];
            // step_distance3=StepDriver_RevBuffer[15]*0x1000000 + StepDriver_RevBuffer[16]*0x10000 + StepDriver_RevBuffer[17]*0x100+ StepDriver_RevBuffer[18];
            if(StepDriver_RevBuffer[4]==0x90)
                step_distance1=StepDriver_RevBuffer[5]*0x1000000 + StepDriver_RevBuffer[6]*0x10000 + StepDriver_RevBuffer[7]*0x100+ StepDriver_RevBuffer[8];
            else if(StepDriver_RevBuffer[4]==0x91)
                step_distance2=StepDriver_RevBuffer[5]*0x1000000 + StepDriver_RevBuffer[6]*0x10000 + StepDriver_RevBuffer[7]*0x100+ StepDriver_RevBuffer[8];
            else if(StepDriver_RevBuffer[4]==0x92)
                step_distance3=StepDriver_RevBuffer[5]*0x1000000 + StepDriver_RevBuffer[6]*0x10000 + StepDriver_RevBuffer[7]*0x100+ StepDriver_RevBuffer[8];
            
        }
        //如果舵机角度有变化，则进行舵机设置
        // 数据不为空
		if(servo_bus_index_rear != servo_bus_index_front){
			set_my_servo_bus(&servo_bus_cmd_queue[servo_bus_index_front]);
			//servo_bus_index_front = (servo_bus_index_front+1)%SERVO_BUS_QUEUE_MAX;
            servo_bus_index_rear = servo_bus_index_front;
		}
    }
    
}


void set_stepmotor(int ch,int speed)
{
    //初始化
    if(isInit == false)
    {
        ThreadStart(StepMotorThread);
        wait(0.01);
        isInit=true;
    }
    speed = constrain(speed,-MAXSPED,MAXSPED);
    if(ch == STP_MOT_CH1)
    {
        step_spd1 = speed;
    }
    else if(ch== STP_MOT_CH2)
    {
        step_spd2 = speed;
    }
    else if(ch== STP_MOT_CH3)
    {
        step_spd3 = speed;
    }
}

void set_stepmotor_acc(int ch,int acc)
{
    //电机加减速平滑程度：0不进行平滑。16000最大加速度
    acc= constrain(acc,0,MAXSPED);
    if(ch == STP_MOT_CH1)
    {
        SPD_ACC_1 = acc;
    }
    else if(ch== STP_MOT_CH2)
    {
        SPD_ACC_2 = acc;
    }
    else if(ch== STP_MOT_CH3)
    {
        SPD_ACC_3 = acc;
    }
}

int get_stepmotor_distance(int ch)
{
    if(ch == STP_MOT_CH1)
    {
        return step_distance1;
    }
    else if(ch== STP_MOT_CH2)
    {
        return step_distance2;
    }
    else if(ch== STP_MOT_CH3)
    {
        return step_distance3;
    }
    return 0;
}


void set_stepmotor_reset()
{
    step_spd1=0;
    step_spd2=0;
    step_spd3=0;
    isReset=true;
    wait(0.1);//等待复位多发送几次
    isReset=false;
}


void set_step_vel(int ch,float angular){
    set_stepmotor(ch,(int)(angular/step2rad));
}


float get_stepmotor_rad(int ch)
{
    return ((float)get_stepmotor_distance(ch))*step2rad;
}