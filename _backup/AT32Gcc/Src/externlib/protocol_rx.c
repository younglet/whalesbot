#include "protocol_rx.h"
// #include "step_driver.h"

// 限制值在范围内
#define LIMIT_VALUE(value, min, max)	(value>max?max:(value<min?min:value))
// 获取当前指令内类型是在指令内
#define GETCMD(comand, type)	(0x01<<type & comand)
// 清除当前指令内类型是在指令内
#define CLEARCMD(comand, type)	(comand = ~(0x01<<type) & comand)
// 设置当前指令内类型是到指令内
#define SETCMD(comand, type)	(comand = 0x01<<type | comand)

enum var_type{
	i8_var=1,
	u8_var=2,
	i16_var=3,
	u16_var=4,
	i32_var=5,
	u32_var=6,
	float_var=7,
	double_var=8,
};


typedef struct _comand
{
	void *cmd_rst;
	void *cmd_set;
	void *cmd_read;
}dev_comand_t;


/***
 * cmd 01 read 02 write
tx  head1	head2	length	[comand]	rear
	77		68		01-10	xxxx		0a

conmand		dev_id		cmd			params
			moto    	reset
			encoder		read
			imu			write		

params		port	angle	speed
			P1		20		40
**/



#define DEV_MAX 20
enum dev_type{
	NONE_DEV=0,
	MOTOS_DEV= 1,
	MOTO_DEV=2,
	ENCODERS_DEV=3,
	ENCODER_DEV=4,
	SERVO_ANGLE_DEV=5,
	SERVO_SET_DEV=6,
	IMU_DEV = 7,
	ROS_DEV = 8,
};



#pragma pack(push,1)    //可以指定结构的对齐和补齐的字节数

// 蜂鸣器相关
typedef struct _beep_rx_t{
	enum cmd_type cmd_type;
	uint8_t freq;
	uint8_t time;
}beep_cmd_t;

static beep_cmd_t beep_cmd;
static uint8_t beep_flag=0;
static void beep_thread(){
	float time = 0;
	int freq = beep_cmd.freq * 2;
	while (1)
	{
		if(beep_flag==1){
			time = beep_cmd.time * (1.0 / 20);
			freq = beep_cmd.freq * 2;
			beep_play(freq, time);
			// printf("freq:%d\ntime:%f\n",freq, time);
			beep_flag = 0;
		}
		wait(0.1);
	}
}

void beep_rx_process(uint8_t* params){
	beep_cmd_t beep_cmd = *(beep_cmd_t *)params;
	switch (beep_cmd.cmd_type)
	{
	case WRITE_CMD:
		// beep_play(freq, time);
		beep_flag = 1;
		// printf("freq:%d\ntime:%f\n",freq, time);
		break;
	default:
		break;
	}
}

// 蓝牙相关
typedef struct _bluetooch_rx_t{
	uint8_t stick_left_x;
	uint8_t stick_left_y;
	uint8_t stick_right_x;
	uint8_t stick_right_y;
	int button_key;
}bluetooth_cmd_t;

static bluetooth_cmd_t bluetooth_cmd;
void bluetooth_rx_process(uint8_t* params){
	bluetooth_cmd_t* bluetooth_set = (bluetooth_cmd_t*)params;
	bluetooth_set->stick_left_y = get_bt_remote_control(BTSTICK1);
	bluetooth_set->stick_left_x = get_bt_remote_control(BTSTICK2);
	bluetooth_set->stick_right_y = get_bt_remote_control(BTSTICK3);
	bluetooth_set->stick_right_x = get_bt_remote_control(BTSTICK4);
	bluetooth_set->button_key = get_bt_remote_control(BTKEY);
}

// 传感器相关
#define SENSOR_MAX 9
enum sensor_type{
	// getAI
	AI_SENSOR=0,
	// get_infrared_distance
	INFRARED_SENSOR=1,
	// touch_switch_pressed
	TOUCH_SWITCH_SENSOR=2,
	// ultrasonic_SENSOR=3
	ULTRASONIC_SENSOR=3,
	// get_ambient_light
	AMBIENT_LIGHT_SENSOR=4,
	// get_temperature
	TEMPERATURE_SENSOR=5,
	// get_humidity
	HUMIDITY_SENSOR=6,
	// get_flame
	FLAME_SENSOR=7,
	// get_sound_volume
	SOUND_VOLUME_SENSOR=8,
	// color_value
	COLOR_VALUE_SENSOR=9,
	// get_gesture
	GESTURE_SENSOR=10,
	// get_tof
	TOF_SENSOR=11,
	// infrared_receiver
	INFRARED_RECEIVER=12,
	// get_single_grayscale
	GRAYSCALE_SENSOR=13,
	// button_pressed
	BUTTON_PRESSED=14,

};

typedef struct _sensor_rx_t{
	enum sensor_type senser_type;
	int8_t port_id;
	int16_t value;
}sensor_cmd_t;

static sensor_cmd_t sensor_a_portp;
static sensor_cmd_t sensor_a_porta;

void sensor_portp_rx_process(uint8_t* params){
	sensor_cmd_t *sensor_cmd = (sensor_cmd_t *)params;
	if(sensor_cmd->port_id>SENSOR_MAX || sensor_cmd->port_id<1){
		// 发的数据错误
		sensor_a_portp.value = 0;
		return;
	}
	switch (sensor_cmd->senser_type)
	{
	case AI_SENSOR:
		sensor_cmd->value = getAI(sensor_cmd->port_id);
		break;
	case INFRARED_SENSOR:
		sensor_cmd->value = get_infrared_distance(sensor_cmd->port_id);
		break;
	case TOUCH_SWITCH_SENSOR:
		sensor_cmd->value = touch_switch_pressed(sensor_cmd->port_id);
		break;
	case ULTRASONIC_SENSOR:
		sensor_cmd->value = get_ultrasonic_distance(sensor_cmd->port_id);
		break;
	case AMBIENT_LIGHT_SENSOR:
		sensor_cmd->value = get_ambient_light(sensor_cmd->port_id);
		break;
	case TEMPERATURE_SENSOR:
		sensor_cmd->value = get_temperature(sensor_cmd->port_id);
		break;
	case HUMIDITY_SENSOR:
		sensor_cmd->value = get_humidity(sensor_cmd->port_id);
		break;
	case FLAME_SENSOR:
		sensor_cmd->value = get_flame(sensor_cmd->port_id);
		break;
	case SOUND_VOLUME_SENSOR:
		sensor_cmd->value = get_sound_volume(sensor_cmd->port_id);
		break;
	case COLOR_VALUE_SENSOR:
		sensor_cmd->value = color_value(sensor_cmd->port_id);
		break;
	case GESTURE_SENSOR:
		sensor_cmd->value = get_gesture(sensor_cmd->port_id);
		break;
	case TOF_SENSOR:
		sensor_cmd->value = get_tof(sensor_cmd->port_id);
		break;
	case INFRARED_RECEIVER:
		sensor_cmd->value = infrared_receiver(sensor_cmd->port_id);
		break;
	case GRAYSCALE_SENSOR:
		sensor_cmd->value = get_single_grayscale(sensor_cmd->port_id);
		break;

	default:
		break;
	}
	// printf("id%d\nval:%d\n",sensor_a_portp.port_id, sensor_a_portp.value);
}

void sensor_porta_rx_process(uint8_t* params){
	sensor_cmd_t *sensor_cmd = (sensor_cmd_t *)params;
	
	if(sensor_cmd->port_id>SENSOR_MAX || sensor_cmd->port_id<1){
		// 发的数据错误
		sensor_a_porta.value = 0;
		return;
	}
	switch (sensor_cmd->senser_type)
	{
	case AI_SENSOR:
		sensor_cmd->value = getAI(sensor_cmd->port_id+P6);
		// printf("/n%d", sensor_cmd->value);
		break;
	
	default:
		sensor_cmd->value = 0;
		break;
	}
}

static servo_bus_cmd_t servo_bus_cmd;
void servo_bus_rx_process(uint8_t* params)
{	
	servo_bus_cmd_t * servo_bus_param = (servo_bus_cmd_t*)params;
	// 数据错误处理
	if(servo_bus_param->port_id>SERVO_BUS_MAX || servo_bus_param->port_id<1){
		// 发的数据错误
		servo_bus_param->angle = 0;
		// SetServo = 0;
		return;
	}
	servo_bus_param->mode = LIMIT_VALUE(servo_bus_param->mode, 1, 2);
	servo_bus_param->speed = LIMIT_VALUE(servo_bus_param->speed, -100, 100);
	servo_bus_param->angle = LIMIT_VALUE(servo_bus_param->angle, -150, 150);

	if(servo_bus_param->port_id>SERVO_BUS_MAX || servo_bus_param->port_id<1){
		// 发的数据错误
		servo_bus_param->angle = 0;
		// SetServo = 0;
		return;
	}
	switch(servo_bus_param->cmd_type){
		case RESET_CMD:
			// 舵机重置
			break;
		case WRITE_CMD:
			// set_my_servo_bus(servo_bus_cmd);
			servo_bus_apend(servo_bus_param);
			// printf("servo%d\nspeed:%d\nangle%d\n",servo_bus_param->port_id, servo_bus_param->speed, servo_bus_param->angle);
			break;
		case READ_CMD:
			// 根据之前存储的值进行获取
			// ThreadSuspendAll();
			get_my_servo_bus(servo_bus_param);
			// ThreadResumeAll();
			// printf("servo%d\nspeed:%d\nangle%d\n",servo_bus_cmd->port_id, servo_bus_cmd->speed, servo_bus_cmd->angle);
			break;
		default:
			break;
	}
}

// PWM舵机相关
#define PWM_MAX 7
static uint8_t pwm_servos_angle[PWM_MAX];

typedef struct _servo_pwm{
	enum cmd_type cmd_type;
    int8_t port_id;
    uint8_t speed;
	uint8_t angle;
}servo_pwm_data_cmd_t;

static servo_pwm_data_cmd_t servo_p_cmd;
static void set_my_servo_pwm(int8_t port_id, uint8_t speed, uint8_t angle){
	SetServo(6+port_id, speed, angle);
	pwm_servos_angle[port_id-1] = angle;
}

static int8_t get_my_servo_pwm(int8_t port_id){
	return pwm_servos_angle[port_id-1];
}

// //打开PWM舵机电源
// void SERVO_PWR_ON(void);

// //关闭PWM舵机电源
// void SERVO_PWR_OFF(void);
void servo_pwm_rx_process(uint8_t* params)
{	
	servo_pwm_data_cmd_t *servo_pset = (servo_pwm_data_cmd_t *)params;
	// 数据错误处理
	// printf("servo%d\nspeed:%d\nangle%d\n",servo_pset.port_id, servo_pset.speed, servo_pset.angle);
	if(servo_pset->port_id>PWM_MAX || servo_pset->port_id<1){
		// 发的数据错误
		
		servo_pset->angle = 0;
		// SetServo = 0;
		return;
	}
	servo_pset->speed = LIMIT_VALUE(servo_pset->speed, 0, 100);
	servo_pset->angle = LIMIT_VALUE(servo_pset->angle, 0, 180);

	switch(servo_pset->cmd_type){
		case RESET_CMD:
			// 舵机重启
			SERVO_PWR_OFF();
			wait(0.2);
			SERVO_PWR_ON();
			break;
		case WRITE_CMD:
			set_my_servo_pwm(servo_pset->port_id, servo_pset->speed,servo_pset->angle);
			// printf("servo%d\nspeed:%d\nangle%d\n",servo_pset.port_id, servo_pset.speed, servo_pset.angle);
			break;
		case READ_CMD:
			// 根据之前存储的值进行获取
			servo_pset->speed = 0;
			servo_pset->angle = get_my_servo_pwm(servo_pset->port_id);
			// printf("servo%d\nspeed:%d\nangle%d\n",servo_pset.port_id, servo_pset.speed, servo_pset.angle);
			break;
		case START_CMD:
			SERVO_PWR_ON();
			break;
		case END_CMD:
			SERVO_PWR_OFF();
			break;
		default:
			break;
	}
	
}

// 电机相关
#define MOTOR_MAX 6
#define MOTOR_NUM 4
static int8_t motors_speed[MOTOR_MAX];
static float last_time_motor[MOTOR_MAX];
static uint8_t motor_state[MOTOR_MAX];

// 定义电机超时时间
#define TIME_STOP 0.8
typedef struct _motors{
	enum cmd_type cmd_type;
	int8_t speed[MOTOR_NUM];
}motors_data_cmd_t;

static motors_data_cmd_t motors_cmd;

static void set_my_motor(int8_t port_id, int8_t speed){
	set_motor(port_id, speed);
	motors_speed[port_id-1] = speed;
	last_time_motor[port_id-1] = seconds();
}
static int8_t get_my_motor(int8_t port_id){
	return motors_speed[port_id-1];
}

// 控制电机超时停止
void motor_thread_back(){
	float time_tmp;
	while (1)
	{
		for(int i=0; i<MOTOR_MAX; i++){
			time_tmp = seconds();
			if(time_tmp - last_time_motor[i] > TIME_STOP){
				if(motor_state[i] != 0){
					set_motor(i+1, 0);
					motors_speed[i] = 0;
					motor_state[i] = 0;
				}
			}
			else{
				if(motor_state[i]!=1){
					motor_state[i] = 1;
				}
			}
		}
		wait(0.1);
	}
}

void motos_rx_process(uint8_t* params)
{
	motors_data_cmd_t *motors_cmd = (motors_data_cmd_t *)params;
	switch (motors_cmd->cmd_type)
	{
	case RESET_CMD:
		for(int i=0; i<MOTOR_NUM; i++){
			set_my_motor(i+1, motors_cmd->speed[i]);
		}
		break;
	case WRITE_CMD:
		for(int i=0; i<MOTOR_NUM; i++){
			// 获取速度参数，并限制在-100-100之间
			motors_cmd->speed[i] = LIMIT_VALUE(motors_cmd->speed[i], -100, 100);
			set_my_motor(i+1, motors_cmd->speed[i]);
		}
		break;
	default:
		break;
	}
}

typedef struct _motor{
	enum cmd_type cmd_type;
	int8_t port_id;
	int8_t speed;
}motor_data_cmd_t;
static motor_data_cmd_t motor_cmd;

void motor_rx_process(uint8_t* params)
{
	motor_data_cmd_t *motor_cmd = (motor_data_cmd_t *)params;
	// 数据错误处理
	if(motor_cmd->port_id>MOTOR_MAX || motor_cmd->port_id<1){
		// 发的数据错误
		
		motor_cmd->speed = 0;
		// SetServo = 0;
		return;
	}
	// 设置速度限制
	motor_cmd->speed = LIMIT_VALUE(motor_cmd->speed, -100, 100);

	switch (motor_cmd->cmd_type)
	{
	case RESET_CMD:
		motor_cmd->speed = 0;
		set_my_motor(motor_cmd->port_id, motor_cmd->speed);
		break;
	case WRITE_CMD:
		// 获取速度参数，并限制在-100-100之间
		motor_cmd->speed = LIMIT_VALUE(motor_cmd->speed, -100, 100);
		set_my_motor(motor_cmd->port_id, motor_cmd->speed);
		break;
	case READ_CMD:
		// 获取速度参数
		motor_cmd->speed = get_my_motor(motor_cmd->port_id);
		break;
	default:
		break;
	}
}

#define ENCODER_NUM 4
#define ENCODER_MAX 6
// static int32_t encoders_set[ENCODER_MAX];

typedef struct _encoders{
	enum cmd_type cmd_type;
	int32_t encoders_set[ENCODER_NUM];
}encoders_data_cmd_t;
static encoders_data_cmd_t encoders_cmd;

void encoders_rx_process(uint8_t* params){
	encoders_data_cmd_t *encoders_cmd = (encoders_data_cmd_t *)params;
	// 实现四个电机编码器值的重置设置和获取
	switch (encoders_cmd->cmd_type)
	{
	case RESET_CMD:
		for(int i=0; i<ENCODER_NUM; i++){
			encoders_cmd->encoders_set[i] = 0;
			reset_motor_encoder(i+1);
		}
		break;
	case WRITE_CMD:
		break;
	case READ_CMD:
		for(int i=0; i<ENCODER_NUM; i++){
			// 获取四个电机编码器值
			encoders_cmd->encoders_set[i] = motor_encoder(i+1);
		}
		break;
	default:
		break;
	}
}

typedef struct _encoder{
	enum cmd_type cmd_type;
    int8_t port_id;
    int32_t encoder_val;
}encoder_data_cmd_t;

static encoder_data_cmd_t encoder_cmd;
void encoder_rx_process(uint8_t* params){
	encoder_data_cmd_t *encoder_cmd = (encoder_data_cmd_t *)params;
	// 错误处理
	if(encoder_cmd->port_id>ENCODER_MAX || encoder_cmd->port_id<1){
		encoder_cmd->encoder_val = 0;
		return;
	}

	switch (encoder_cmd->cmd_type)
	{
	case RESET_CMD:
		encoder_cmd->encoder_val = 0;
		reset_motor_encoder(encoder_cmd->port_id);
		break;
	case WRITE_CMD:
		break;
	case READ_CMD:
		encoder_cmd->encoder_val = motor_encoder(encoder_cmd->port_id);
		break;
	default:
		break;
	}
}

typedef struct _led_light_cmd_t
{
	enum cmd_type cmd_type;
	uint8_t port_id;
	uint8_t led_id;
	uint8_t r;
	uint8_t g;
	uint8_t b;
}led_light_t;
static led_light_t led_light_cmd;
void led_light_rx_process(uint8_t* params){
	led_light_t *led_light_set = (led_light_t *)params;
	switch (led_light_set->cmd_type){
		case RESET_CMD:
			set_rgb_led_strip(led_light_set->port_id + 6, led_light_set->led_id, 0, 0, 0);
			break;
		case READ_CMD:
			break;
		case WRITE_CMD:
		// D7;
			// printf("port_id:%d\nled_id:%d\nr:%d\ng:%d\nb:%d\n",
			// led_light_set->port_id, led_light_set->led_id, led_light_set->r, led_light_set->g, led_light_set->b);

			set_rgb_led_strip(led_light_set->port_id + 6, led_light_set->led_id, led_light_set->r, led_light_set->g, led_light_set->b);
			break;
		default:
			break;
	}
}

typedef struct _board_key{
	enum cmd_type cmd_type;
	uint8_t val_up;
	uint8_t val_down;
}board_key_data_cmd_t;
static board_key_data_cmd_t board_key_cmd;

void board_key_rx_process(uint8_t* params){
	board_key_data_cmd_t *board_key_cmd = (board_key_data_cmd_t *)params;

	if (board_key_cmd->cmd_type == READ_CMD || board_key_cmd->cmd_type == NONE_CMD)
	{
		board_key_cmd->val_up = button_pressed(key_up);
		board_key_cmd->val_down = button_pressed(key_down);
		// printf("key_val:%d\n", board_key_cmd->val);
	}
}

typedef struct _power{
	enum cmd_type cmd_type;
	int32_t batt;
}power_data_cmd_t;
static power_data_cmd_t power_cmd;

void power_rx_process(uint8_t* params){
	power_data_cmd_t *power_cmd = (power_data_cmd_t *)params;
	if (power_cmd->cmd_type == READ_CMD)
	{
		power_cmd->batt = getBatt_AVG();
	}
}
#define DIS_MAX_LEN 100
typedef struct _led_show{
	enum cmd_type cmd_type;
	char dis[DIS_MAX_LEN];
}led_show_cmd_t;

static led_show_cmd_t led_show_cmd;
void led_show_rx_process(uint8_t* params){
	led_show_cmd_t *led_show_cmd = (led_show_cmd_t *)params;
	switch (led_show_cmd->cmd_type)
	{
	case RESET_CMD:
		printf("\n\n");
		break;
	case WRITE_CMD:
		printf("%s", led_show_cmd->dis);
		break;
	default:
		break;
	}
}

typedef struct _nixietube_cmd{
	enum cmd_type cmd_type;
	uint8_t port_id;
	int32_t num;
}nixietube_cmd_t;
static nixietube_cmd_t nixietube_cmd;
void nixietube_rx_process(uint8_t* params){
    nixietube_cmd_t *nixietube_cmd = (nixietube_cmd_t *)params;
    switch (nixietube_cmd->cmd_type)
    {
    case RESET_CMD:
        nixietube_cmd->num = 0;
		display_digital_tube(nixietube_cmd->port_id, nixietube_cmd->num);
        break;
    case WRITE_CMD:
        nixietube_cmd->num = LIMIT_VALUE(nixietube_cmd->num, 0, 9999);
        display_digital_tube(nixietube_cmd->port_id, nixietube_cmd->num);
		break;
	default:
		break;
	}
}

typedef struct _Dout_cmd{
	enum cmd_type cmd_type;
	uint8_t port_id;
	uint8_t val;
}Dout_cmd_t;
static Dout_cmd_t Dout_cmd;
void Dout_rx_process(uint8_t* params){
    Dout_cmd_t *Dout_param = (Dout_cmd_t *)params;
    switch (Dout_param->cmd_type)
    {
    case RESET_CMD:
        Dout_param->val = 0;
		SetDO(Dout_param->port_id, Dout_param->val);
        break;
    case WRITE_CMD:
        Dout_param->val = LIMIT_VALUE(Dout_param->val, 0, 1);
        SetDO(Dout_param->port_id, Dout_param->val);
		break;
	default:
		break;
	}
}

typedef struct _stepper_cmd_t{
	enum cmd_type cmd_type;
	uint8_t port_id;
	int vel_stepper;
	int cnt_stepper;
}stepper_cmd_t;
static stepper_cmd_t stepper_cmd;

void stepper_rx_process(uint8_t* params){
	stepper_cmd_t *stepper_cmd_p = (stepper_cmd_t*)params;
	// printf("step id:%d vel:%d", stepper_cmd_p->port_id, stepper_cmd_p->vel_stepper);
	switch (stepper_cmd_p->cmd_type)
	{
	case RESET_CMD:
		/* code */
		break;
	case READ_CMD:
		stepper_cmd_p->cnt_stepper = get_stepmotor_distance(stepper_cmd_p->port_id);
		break;
	case WRITE_CMD:
		set_stepmotor(stepper_cmd_p->port_id, stepper_cmd_p->vel_stepper);
		break;
	default:
		break;
	}
}

typedef struct _version_driver{
	enum cmd_type cmd_type;
	int version;
} version_driver_t;
static version_driver_t version_cmd;
static int prtl_version = 20250612; // 固件版本号
static void version_driver_process(uint8_t *data){
	version_driver_t *ver_cmd = (version_driver_t *)data;
	switch (ver_cmd->cmd_type)
	{
	case READ_CMD:
		ver_cmd->version = prtl_version; // 固件版本号
		break;
	default:
		break;
	}
}
#pragma pack(pop)       //恢复push前的值

void rx_process_start(void){
	// int i=1;
	protocol_set_devfunc(version_driver_process, (uint8_t *)&version_cmd, sizeof(version_driver_t), 0);
	// 电机控制相关1,2
	protocol_set_devfunc(motos_rx_process,(uint8_t*)&motors_cmd, sizeof(motors_cmd), 1);
	protocol_set_devfunc(motor_rx_process, (uint8_t*)&motor_cmd, sizeof(motor_cmd), 2);

	//电机编码值相关 3,4
	protocol_set_devfunc(encoders_rx_process, (uint8_t*)&encoders_cmd, sizeof(encoders_cmd), 3);
	protocol_set_devfunc(encoder_rx_process, (uint8_t*)&encoder_cmd, sizeof(encoder_cmd), 4);

	//pwm舵机控制相关
	protocol_set_devfunc(servo_pwm_rx_process, (uint8_t*)&servo_p_cmd, sizeof(servo_p_cmd), 5); 

	//总线舵机控制
	protocol_set_devfunc(servo_bus_rx_process, (uint8_t*)&servo_bus_cmd, sizeof(servo_bus_cmd), 6);

	// sensor获取 p口, a口
	protocol_set_devfunc(sensor_portp_rx_process, (uint8_t*)&sensor_a_portp, sizeof(sensor_a_portp), 7);
	protocol_set_devfunc(sensor_porta_rx_process, (uint8_t*)&sensor_a_porta, sizeof(sensor_a_porta), 8);

	//读取蓝牙值
	protocol_set_devfunc(bluetooth_rx_process, (uint8_t*)&bluetooth_cmd, sizeof(bluetooth_cmd), 9);
	// beep
	protocol_set_devfunc(beep_rx_process, (uint8_t*)&beep_cmd, sizeof(beep_cmd), 10);

	// led show
	protocol_set_devfunc(led_show_rx_process, (uint8_t*)&led_show_cmd, sizeof(led_show_cmd), 11);
	
	// power
	protocol_set_devfunc(power_rx_process, (uint8_t*)&power_cmd, sizeof(power_cmd), 12);
	// board_key
	protocol_set_devfunc(board_key_rx_process, (uint8_t*)&board_key_cmd, sizeof(board_key_cmd), 13);
	// led light
	protocol_set_devfunc(led_light_rx_process, (uint8_t*)&led_light_cmd, sizeof(led_light_cmd), 14);
	// nixietube
	protocol_set_devfunc(nixietube_rx_process, (uint8_t*)&nixietube_cmd, sizeof(nixietube_cmd), 15);
	// Dout
	protocol_set_devfunc(Dout_rx_process, (uint8_t*)&Dout_cmd, sizeof(Dout_cmd), 16);
	// stepper
	protocol_set_devfunc(stepper_rx_process, (uint8_t*)&stepper_cmd, sizeof(stepper_cmd), 17);
	//IMU控制
	// protocol_set_devfunc(imu_rx_process, (uint8_t*)&imu_set, sizeof(imu_set), 7);

	// protocol_set_devfunc(odom_rx_process, (uint8_t*)&odom_set, sizeof(odom_set), 50);
	
	FunType rx_handle_pi = protocol_config(UartPi_Sendbytes);
	FunType rx_handle_usb = protocol_config(UartPC_Sendbytes);

	// 电机线程
	ThreadStart(motor_thread_back);
	ThreadStart(beep_thread);

	setUartPi_RxHandle(rx_handle_pi);
	setUartPC_RxHandle(rx_handle_usb);
	
}

