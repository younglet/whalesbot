#ifndef _TOOL_WBT_H_
#define _TOOL_WBT_H_

#include "whalesbot.h"
// #define PI 3.14159265358979323846
#define _USE_MATH_DEFINES


#define LIMIT_VAL(a,min,max) ((a)<(min)?(min):((a)>(max)?(max):(a)))

#define PID_INTEGRAL_ON    //位置式PID是否包含积分项。如果仅用PD控制，注释本行
 
typedef struct PID
{ 
    float kp;               
    float ki;
    float kd;
#ifdef 	PID_INTEGRAL_ON
    float Integral;        //位置式PID积分项
    float IntegralMax;     //位置式PID积分项最大值，用于限幅
#endif	
    float Last_Error;      //上一次误差	
    float OutputMax;       //位置式PID输出最大值，用于限幅
}PID;

float pid_cal(PID *pid, float NowValue, float AimValue);
void pid_out_cfg(PID *pid, float now, float aim, float time, float min, float max);
void pid_out_cfg2(PID *pid, float now, float aim, float out_max, float time, float min, float max);

void float2d_mul(float *lelf, float *right, float *out, int row, int col, int mid);
#endif