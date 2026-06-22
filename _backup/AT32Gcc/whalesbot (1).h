#ifndef __PROTOCOL_WB_H__
#define __PROTOCOL_WB_H__
enum cmd_type{
	NONE_CMD = 0,
	READ_CMD = 1,
	WRITE_CMD = 2,
	RESET_CMD = 3,
	START_CMD = 4,
	END_CMD = 5
};
#include "whalesbot.h"


typedef void (*DevFunc)(uint8_t*);
typedef void(*TxFunc)(uint8_t *, int);
typedef void(*RxFunc)(int);

uint8_t get_ping_status();
RxFunc protocol_config(TxFunc TxHandle);
// void UartPI_RevCallback(int revdata);
// 添加控制函数 数据 长度 对应到序号
void protocol_set_devfunc(DevFunc devfunc, uint8_t* data_dev, uint8_t length, uint8_t index);
#endif