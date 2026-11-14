#include "stm32f10x.h"                  // Device header
#include <stdio.h>
#include "Delay.h"
#include "BlueTooth.h"
#include "Servo.h"
#include "PetAction.h"
#include "PWM.h"
#include "FSR.h"
#include "MPU6050.h"


/***************************************************************************************
  * 本程序由博主我Sngels_wyh创建并免费开源共享
  * 你可以任意查看、使用和修改，并应用到自己的项目之中
  * 
  * 程序名称：				基于STM32F103C8T6单片机的桌面宠物小项目
  * 此程序更新时间：			2024.2.16
  * 
  * 主要在立创开源平台、CSDN网站、哔哩哔哩、抖音分享自己的作品。
	*	相关的资料可以去立创开源硬件平台网站上搜索,作品附件放置更新网盘，如有更新可方便快速查看
	* 地址:https://oshwhub.com/sngelswyh/stm32-smart-desktop-pet
  ***************************************************************************************/


uint16_t Time;
uint16_t HuXi;
uint16_t PanDuan=1;
uint16_t Wait=0;

/* ===== 非阻塞前进步态（替代阻塞式 Action_advance，采样不卡死）=====
 * 原 Action_advance 是 8 相位 × 300ms 的阻塞循环，采样会断。
 * 这里改成每 10ms 推进一步：相位 0~7 与原舵机序列、300ms 时序完全一致。
 */
#define G_WALK_FWD   60    // 前进摆动角
#define G_WALK_BACK  120   // 回摆角
#define G_WALK_TICKS 30    // 每相位保持 30 个 tick = 300ms

static uint8_t  gait_phase = 0;
static uint16_t gait_hold  = 0;

void Gait_Tick(void)
{
	if (Action_Mode != 4)          // 非前进态：复位，不动作
	{
		gait_phase = 0;
		gait_hold  = 0;
		return;
	}

	if (gait_hold > 0)             // 当前姿势还没保持够 300ms
	{
		gait_hold--;
		return;
	}

	switch (gait_phase)
	{
		case 0: Servo_Angle2(G_WALK_FWD);  Servo_Angle3(G_WALK_FWD);  break;
		case 1: Servo_Angle1(G_WALK_BACK); Servo_Angle4(G_WALK_BACK); break;
		case 2: Servo_Angle2(90);          Servo_Angle3(90);          break;
		case 3: Servo_Angle1(90);          Servo_Angle4(90);          break;
		case 4: Servo_Angle1(G_WALK_FWD);  Servo_Angle4(G_WALK_FWD);  break;
		case 5: Servo_Angle2(G_WALK_BACK); Servo_Angle3(G_WALK_BACK); break;
		case 6: Servo_Angle1(90);          Servo_Angle4(90);          break;
		case 7: Servo_Angle2(90);          Servo_Angle3(90);          break;
	}
	gait_hold  = G_WALK_TICKS;
	gait_phase = (gait_phase + 1) & 7;
}

int main(void)
{
	Servo_Init();
	// 上电立刻站定：避免传感器初始化期间舵机无 PWM 信号被重力带偏
	Servo_Angle1(90); Servo_Angle2(90);
	Servo_Angle3(90); Servo_Angle4(90);
	FSR_Init();          // 四路 FSR ADC（PA4/PA5/PA6/PA7）
	MPU6050_Init();      // MPU6050 软件 I2C（PB8/PB9）
	BlueTooth_Init();    // 蓝牙初始化

	uint16_t fsr[4];
	int16_t accel[3], gyro[3];
	char line[64];
	char rpt[32];   // 自测模式报告缓冲
	uint16_t tick_target;

	// 上电自检：确认固件版本 + MPU 供电/接线（WHO_AM_I 应为 0x68）
	sprintf(line, "E1_FW MPU=0x%02X\r\n", (unsigned)MPU6050_ReadID());
	BlueTooth_SendString(line);

	while(1)
	{
		// 100Hz 定频：TIM4 为 10kHz 自由运行计数（0.1ms 粒度），+100 = 10ms
		tick_target = (uint16_t)TIM4->CNT + 100;

		// 1) 采样（每拍只读一次，不再做 WHO_AM_I 诊断）
		FSR_Read(fsr);
		MPU6050_GetData(accel, gyro);
		MPU6050_Wakeup();   // 每拍补唤醒：克隆 MPU 会自回睡眠（E1 删了此调用→A/G 全 0），九次会话已证根治

		// 2) G 命令置位 → 补发 GO 标记
		if (g_pending_go)
		{
			BlueTooth_SendString("GO\r\n");
			g_pending_go = 0;
		}

		// 3) S 命令置位 → 四腿站定（无延时）
		if (g_do_stand)
		{
			Servo_Angle1(90); Servo_Angle2(90);
			Servo_Angle3(90); Servo_Angle4(90);
			g_do_stand = 0;
		}

		// 4) 组帧发送：ms,LF,RF,LH,RH,Ax,Ay,Az,Gx,Gy,Gz
		//    LF=fsr0(PA7) RF=fsr1(PA6) LH=fsr3(PA5) RH=fsr2(PA4)
		sprintf(line, "%u,%u,%u,%u,%u,%d,%d,%d,%d,%d,%d\r\n",
			(unsigned)g_ms,
			(unsigned)fsr[0], (unsigned)fsr[1], (unsigned)fsr[3], (unsigned)fsr[2],
			(int)accel[0], (int)accel[1], (int)accel[2],
			(int)gyro[0], (int)gyro[1], (int)gyro[2]);
		BlueTooth_SendString(line);

		// 5) 时间戳递增（100Hz → 每拍 +10ms）
		g_ms += 10;

		// 5.5) 自测模式状态机（T 命令触发，绕开蓝牙掉线：yaw 在内部算、走完自动停）
		if (g_test_phase == 1)
		{
			// 相位1：站定 3s 累加 Gz 零偏
			g_bias_sum += gyro[2];
			g_bias_n++;
			if (g_ms - g_test_t0 >= 3000)
			{
				g_test_bias = (float)g_bias_sum / (float)g_bias_n;
				g_test_phase = 2;
				g_test_t0 = g_ms;
				Sustainedmove = 1; Action_Mode = 4;   // 开走
			}
		}
		else if (g_test_phase == 2)
		{
			// 相位2：走 200s，积分 (Gz - 零偏) → 偏航角(deg)（耐力测试：看电池/舵机能否坚持走完）
			g_test_yaw += (gyro[2] - g_test_bias) / 131.0f * 0.01f;
			if (g_ms - g_test_t0 >= 200000)
			{
				// 走完自动停，结果存好待查（蓝牙掉线期间也丢不了）
				g_test_phase = 0;
				g_yaw_ready = 1;
				Sustainedmove = 0; Action_Mode = 2;   // 自动停
				Servo_Angle1(90); Servo_Angle2(90);
				Servo_Angle3(90); Servo_Angle4(90);
			}
		}

		// 5.6) Y 命令查询结果：结果就绪且有待发次数 → 连发 YAW
		if (g_report_cnt > 0 && g_yaw_ready)
		{
			// 整数格式化（microlib 不支持 %f）：转百分之一度再拼
			int yi = (int)(g_test_yaw * 100.0f + (g_test_yaw < 0.0f ? -0.5f : 0.5f));
			int ab = (yi < 0) ? -yi : yi;
			sprintf(rpt, "YAW=%c%d.%02d\r\n", (yi < 0 ? '-' : '+'), ab / 100, ab % 100);
			BlueTooth_SendString(rpt);
			g_report_cnt--;
		}

		// 5.7) U/D 改 trim 后回显新值（整数格式化，规避 microlib 不支持 %f）
		if (g_trim_report)
		{
			int ti = (int)(ServoTrim[2] * 10.0f + (ServoTrim[2] < 0.0f ? -0.5f : 0.5f));
			int tab = (ti < 0) ? -ti : ti;
			sprintf(rpt, "TRIM=%c%d.%d\r\n", (ti < 0 ? '-' : '+'), tab / 10, tab % 10);
			BlueTooth_SendString(rpt);
			g_trim_report = 0;
		}

		// 6) 非阻塞步态推进（前进时每 10ms 推一帧，不卡采样）
		Gait_Tick();

		// 7) 等满 10ms，锁 100Hz
		while ((int16_t)(TIM4->CNT - tick_target) < 0);
	}
}


void TIM3_IRQHandler(void)
{
	if(TIM_GetITStatus(TIM3,TIM_IT_Update)==SET)
	{	
		if(AllLed==1 && BreatheLed==0)//如果灯光开启且不开启呼吸灯,亮度拉满
		{
			PWM_LED1(20000);
			PWM_LED2(20000);
		}
		else if(AllLed==1 && BreatheLed==1)//如果灯光开启且开启呼吸灯
		{
			if(PanDuan==1)
			{
				HuXi+=100;
				PWM_LED1(HuXi);
				PWM_LED2(HuXi);
				if(HuXi==20000)
					PanDuan=2;
			}
			else if(PanDuan==2)
			{
				HuXi-=100;
				PWM_LED1(HuXi);
				PWM_LED2(HuXi);
				if(HuXi==0)
				{
					PanDuan=3;
				}
			}
			else if(PanDuan==3)
			{
				Wait+=1000;
				if(Wait==20000)
				{
					PanDuan=1;
					Wait=0;
				}
			}
		}
		else if(AllLed==0)
		{
			PWM_LED1(0);
			PWM_LED2(0);
		}
		
		TIM_ClearITPendingBit(TIM3,TIM_IT_Update);
	}
}
