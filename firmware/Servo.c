#include "stm32f10x.h"                  // Device header
#include "PWM.h"

/* ===== 逐腿校准（开机站得正不正就看这里）=====
 * 目标：命令 90° 时，四条腿都应正好「垂直地面」。
 * 若某条腿偏前/偏后，就调对应 ServoTrim 值，单位：度。
 * 左侧(1左前、3左后)为直接映射，实测：正值=往后退、负值=往前进。
 * 右前/右后(2、4)由 180- 反相处理；推导确认 trim 正负号与左侧一致（正值=往后退）。
 * 某条腿补反了（偏得更厉害）就把该腿正负号翻过来即可。
 */
float ServoTrim[4] = {-43.0f, 0.0f, 47.0f, 0.0f};	// 左上, 右上, 左下, 右下（2026-10-19 十二调：肉眼标定 +47 基本走直；陀螺60s积分被零偏漂移污染不可靠，最终以肉眼为准）

// 角度 -> 脉宽（500~2500us，含越界钳位）
static uint16_t angle_to_pulse(float a)
{
	if (a < 0)     a = 0;
	if (a > 180)   a = 180;
	return (uint16_t)(a / 180.0f * 2000 + 500);
}

void Servo_Init()
{
	PWM_Init();
}

void Servo_Angle1(float Angle)//左上
{
	PWM_SetCompare1(angle_to_pulse(Angle + ServoTrim[0]));
}

void Servo_Angle2(float Angle)//右上
{
	PWM_SetCompare2(angle_to_pulse(180 - (Angle + ServoTrim[1])));
}

void Servo_Angle3(float Angle)//左下
{
	PWM_SetCompare3(angle_to_pulse(Angle + ServoTrim[2]));
}

void Servo_Angle4(float Angle)//右下
{
	PWM_SetCompare4(angle_to_pulse(180 - (Angle + ServoTrim[3])));
}

void WServo_Angle(float Angle)//尾巴
{
	PWM_WSetCompare(angle_to_pulse(Angle));
}
