#include "tool.h"

/**********************************************************************************************************
*	函 数 名：PID_Cal
*	功能说明：位置式PID控制
*   输    入：
    NowValue:当前值
    AimValue:目标值
*   输    出：PID控制值，直接赋值给执行函数
**********************************************************************************************************/ 
float pid_cal(PID *pid, float NowValue, float AimValue)
{
 
    float  iError,     //当前误差
            Output;    //控制输出	
 
    iError = AimValue - NowValue;                   //计算当前误差
	
#ifdef 	PID_INTEGRAL_ON	
	if(pid->Last_Error * iError < 0){
		pid->Integral = 0;
	}
    pid->Integral += iError;	            //位置式PID积分项累加
	// pid->Integral = pid->Integral*0.8;
    pid->Integral = pid->Integral > pid->IntegralMax?pid->IntegralMax:pid->Integral;  //积分项上限幅
    pid->Integral = pid->Integral <-pid->IntegralMax?-pid->IntegralMax:pid->Integral; //积分项下限幅
	
#endif		
	
    Output = pid->kp * iError                        //比例P            
           + pid->kd * (iError - pid->Last_Error);   //微分D
	
#ifdef 	PID_INTEGRAL_ON		
    Output += pid->Integral*pid->ki;                        //积分I
#endif	
 
    Output = Output > pid->OutputMax?pid->OutputMax:Output;  //控制输出上限幅
    Output = Output <-pid->OutputMax?-pid->OutputMax:Output; //控制输出下限幅
	
	pid->Last_Error = iError;		  	                     //更新上次误差，用于下次计算 
	return Output;	//返回控制输出值
}

void pid_out_cfg(PID *pid, float now, float aim, float time, float min, float max)
{
	pid->OutputMax = fabs(aim - now) / time;
	pid->OutputMax = LIMIT_VAL(pid->OutputMax, min, max);
}

void pid_out_cfg2(PID *pid, float now, float aim, float out_max, float time, float min, float max)
{
	if(fabs(time)<1e-4){
		pid->OutputMax = fabs(out_max);
	}
	else{
		pid->OutputMax = fabs(aim - now) / time;
	}
	pid->OutputMax = LIMIT_VAL(pid->OutputMax, min, max);
}

// 矩阵乘法, 左侧矩阵乘以右侧矩阵
// l(row,mid)*r(mid,col)
void float2d_mul(float *lelf, float *right, float *out, int row, int col, int mid){
	int i, j, k;
	float tmp = 0.0;
	for(i=0;i<row;i++){
		for(j=0;j<col;j++){
			// 计算矩阵某个元素的结果
			tmp = 0.0;
			for(k=0;k<mid;k++){
				tmp += lelf[i*mid+k] * right[k*col+j];
			}
			out[i*col + j] = tmp;
		}
	}
}


// __unused static void mat_float_print(float *mat, int row, int col)
__unused static void mat_float_print(float *mat, int row, int col)
{
	char buf[128] ="";
	char tmp[24];
	for(int i=0;i<row;i++){
		for(int j=0;j<col;j++){
			if(j!=0){
				strcat(buf," ");
			}
			sprintf(tmp,"%.2f",mat[i*col+j]);
			// 连接字符串
			strcat(buf,tmp);
		}
		strcat(buf,"\n");
	}
	Printf(buf);
}