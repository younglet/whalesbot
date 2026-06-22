#include "whalesbot.h"
#include "protocol_rx.h"

void battary_process(){
	while(1){
        
        if ((getBatt_AVG() >9000&& getBatt_AVG()< 11000) || getBatt_AVG()< 7500){
            beep_play(262, 0.1);
        }
		wait(1);
    }
}


void user_main()
{
    // 电量显示
    printf("batt=%f\n",(float)getBatt_AVG()/1000);
	// 关闭自动关机
    SetAutoPowerDisable();
	// 修改舵机pid
    // PO16_WriteRegister(0xfe, 19, 50);//P 60
    // PO16_WriteRegister(0xfe, 20, 40);//I 65
    // PO16_WriteRegister(0xfe, 21, 20);//D 40
	set_stepmotor(1, 0);
	// servo_bus_cmd_t servo_bus_cmd1={.cmd_type=WRITE_CMD,.port_id=4,.speed=100,.angle=0,.mode=1};
	// servo_bus_apend(&servo_bus_cmd1);
	// 开启usb传输协议
	rx_process_start();
	// set_stepmotor(1, 360);
	wait(1);
	// set_stepmotor(1, 0);
	// 多线程监控电池电量
	ThreadStart((void *)battary_process);
	while(1)
	{	
		if(get_ping_status())
		{
			// 准备进行程序下载，关掉这个程序
			Program_Reset();
		}
		wait(0.1);
	}
    
// python .\AI_Module_GCC\MC_602P\pybuilder\pydownload.py  -address 0x0800D000 -run false
// python .\AI_Module_GCC\MC_602P\pybuilder\pymake.py -all true
}
