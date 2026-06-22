#include "serial_protocol.h"

#define TX_LEN 256
#define RX_LEN 256

#define HEAD_1 0x77
#define HEAD_2 0x68
#define REG_LEN 0x02
#define REAR 0x0A

// 接收处理数据
static uint8_t re_data[RX_LEN] = {0};
// 临时接收数据
static uint8_t re_data_tmp[RX_LEN] = {0};

/***
 * cmd:	01 read    02 write    03 reset    04 start *
tx  head1	head2	lenght	class	cmd     port	data	csr8	rear
	77		68		xxx		01-10	01		01-10	xxxx	xxxx	0a
									moto	1
									encoder	2
									imu		3
**/

/****
 * tx 	head1	head2	lenght	[class	*data]	null	rear
 * 		 77		 68		 xxx	 01-10	 xxxx	 fe		 0a
 */
/***
 * tx  head1	head2	lenght	[class	data]	null	rear
 * 		77		 68		 xxx	01-10	xxxx	 fe		 0a
 *
 */
/***
 * cmd:	01 read    02 write    03 reset    04 start *
tx  head1	head2	lenght	class	cmd     	port	data	rear
	77		68		xxx		01-10	01			01-10	xxxx	0a
**/

#define DEV_MAX 100

static DevFunc dev_process[DEV_MAX] = {NULL};
static uint8_t *dev_data[DEV_MAX] = {NULL};
static uint8_t dev_cmd_len[DEV_MAX] = {0};

#define PING_LENGTH 8
static uint8_t PING_DATA[PING_LENGTH] = {0x55, 0xaa, 0x00, 0x01, 0x08, 0x00, 0x00, 0xf7};

// 添加控制函数 数据 长度 对应到序号
void protocol_set_devfunc(DevFunc devfunc, uint8_t *data_dev, uint8_t length, uint8_t index)
{	
	// printf("dev:%d\n p:%d\n", index, devfunc);
	dev_process[index] = devfunc;
	dev_data[index] = data_dev;
	dev_cmd_len[index] = length;
	// wait(0.5);
}

// 定义发送数据的函数
static void (*uart_send)(uint8_t *data_src, int length);

// enum cmd_type cmd_comand = NONE_CMD;
static uint8_t tx_data[TX_LEN] = {HEAD_1, HEAD_2};

static volatile uint8_t flag_handle = -1;
// 接收数据处理程序，只进行数据检验与接收
static void rx_handle(void)
{
	uint8_t index;
	int data_len;
	int cmd_len;
	uint8_t dev_type;
	while (1)
	{
		if (flag_handle == 1)
		{
			// 读取从数据长度开始
			index = 2;
			data_len = re_data[index++];
			// 如果操作类型存在则进入操作函数，否则不做任何事情
			// printf("dev:%d\ndev_process:\n%p\n",dev_type, dev_process[dev_type]);
			// 检测不是结束标志, 且数据在数据长度范围内
			dev_type = re_data[index];
			while (dev_type < DEV_MAX && index < data_len-1 && dev_process[dev_type] != NULL)
			{
				// 获取处理长度
				cmd_len = dev_cmd_len[dev_type];
				// 根据长度获取数据处理命令
				memcpy(dev_data[dev_type], re_data + index + 1, cmd_len);
				// 处理程序
				dev_process[dev_type](dev_data[dev_type]);
				// 有时反应时间会慢，需要处理
				// 返回数据处理
				tx_data[index] = dev_type;
				memcpy(tx_data + index + 1, dev_data[dev_type], cmd_len);
				index = index + cmd_len + 1;
				// 更新处理类型
				dev_type = re_data[index];
			}
			// 最后一个数据
			tx_data[index++] = REAR;
			// 长度赋值
			tx_data[REG_LEN] = index;
			// 发送数据
			uart_send(tx_data, index);
			flag_handle = 0;
		}
		wait(0.001);
	}
}

// uint8_t check_sum(uint8_t *data, uint8_t length){
// 	uint8_t sum = 0;
// 	for(int i=0; i<length; i++){
// 		sum += data[i];
// 	}
// 	if(sum == data[length-1]){
// 		return -1;
// 	}
// 	else{
// 		return 1;
// 	}
// }

volatile static int rx_idx = 0;
static uint8_t ping_flag = 0;
static uint8_t ping_status = 0;
// 获取ping状态
uint8_t get_ping_status(){
	return ping_status;
}

// 串口接收到1个字节的中断回调
static float time_last = 0;
static void Uart_RevCallback(int revdata)
{
	// 超时处理
	if (seconds() - time_last > 0.1)
	{
		rx_idx = 0;
	}
	time_last = seconds();
	// 接收数据处理
	switch(rx_idx)
	{
		case 0:
		case 1:
			if(revdata == PING_DATA[rx_idx])
			{
				rx_idx++;
				ping_flag = 1;
				break;
			}

			// 数据头
			if (revdata == HEAD_1)
			{
				rx_idx = 0;
				re_data_tmp[rx_idx++] = revdata;
			}
			else if (revdata == HEAD_2 && rx_idx == 1)
			{
				re_data_tmp[rx_idx++] = revdata;
			}
			break;

		// 长度超过了限制
		case RX_LEN:
			rx_idx = 0;
			break;

		default:
			if(revdata == PING_DATA[rx_idx])
			{
				if(rx_idx == PING_LENGTH-1){
					ping_status = 1;
					rx_idx = 0;
					ping_flag = 0;
					break;
				}
				rx_idx++;
				ping_flag = 1;
				break;
			}

			// 数据接收
			re_data_tmp[rx_idx++] = revdata;
			// 数据结尾长度校验判断准确
			if (revdata == REAR)
			{
				// 数据长度校验处理
				if (re_data_tmp[REG_LEN] < rx_idx)
				{
					rx_idx = 0;
				}
				else if (re_data_tmp[REG_LEN] == rx_idx)
				{
					// check_sum(re_data, order_t);		// 验证数据是否错误
					memcpy(re_data, re_data_tmp, rx_idx);
					// 标记来了串口数据
					flag_handle = 1;
					rx_idx = 0;
				}
			}
			break;
	}

}

RxFunc protocol_config(TxFunc TxHandle)
{
	// ser_rx_process所有数据置零
	// memset(dev_process, 0, DEV_MAX*4);
	// 设置中断函数
	uart_send = TxHandle;
	// uart_send("test!",5);
	// printf("test!\n");
	// setUartPi_RxHandle(UartPI_RevCallback);
	// 中断函数处理，如果有完整的数据进行处理
	// ThreadStart(rx_process);
	ThreadStart(rx_handle);

	return Uart_RevCallback;
	// moto_ser_t moto_tmps;
	// moto_tmps.id = 1;
	// moto_tmps.speed = 20;
	// memcpy(re_data+4, &moto_tmps, sizeof(moto_tmps));
	// ThreadStart(show_test);
}