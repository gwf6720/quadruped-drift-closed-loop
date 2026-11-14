#include "stm32f10x.h"                  // Device header
#include "PWM.h"
#include "PetAction.h"
#include "Servo.h"

uint16_t AllLed=1;        //开启灯光
uint16_t BreatheLed=0;    //开启呼吸灯
uint16_t Sustainedmove=0; //持续运动

uint16_t Action_Mode=2;   //开机即站立（原为0=放松趴下，上电会自动动一下）
uint16_t SpeedDelay=200;
uint16_t SwingDelay=6;
uint16_t Face_Mode=0;
uint8_t WeiBa=0;

/* ===== E1 实验新增全局 ===== */
volatile uint32_t g_ms          = 0;   // 采集时间戳(ms)，R 命令清零
volatile uint8_t  g_pending_go  = 0;   // G 命令置位，主循环补发 GO 标记
volatile uint8_t  g_do_stand    = 0;   // S 命令置位，主循环站定
volatile uint8_t  g_fsm_on      = 0;   // FSM 开关（E1 固定关，仅存标志）

/* ===== 自测模式（T 命令）：站3s测零偏→走200s积分yaw→自动停；Y 命令查询结果 ===== */
volatile uint8_t  g_test_phase  = 0;   // 0=空闲 1=站零偏 2=走积分
volatile uint32_t g_test_t0     = 0;   // 各相位起始 ms
float             g_test_bias   = 0.0f;// 站姿 Gz 零偏(LSB)
float             g_test_yaw    = 0.0f;// 积分偏航(deg)
int32_t           g_bias_sum    = 0;   // 零偏累加(LSB)
int32_t           g_bias_n      = 0;   // 零偏样本数
volatile uint8_t  g_yaw_ready   = 0;   // 自测完成、结果有效
volatile uint8_t  g_report_cnt  = 0;   // Y 命令后剩余报告次数
volatile uint8_t  g_trim_report = 0;   // U/D 改 trim 后置位，主循环回显新值

void BlueTooth_Init(void)
{
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB,ENABLE);//开启GPIOB时钟
	RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART3,ENABLE);//开启串口3时钟（蓝牙）

	//蓝牙 JDY-31 -> USART3
	GPIO_InitTypeDef GPIO_InitStructure;
	GPIO_InitStructure.GPIO_Mode=GPIO_Mode_AF_PP;//复用推挽输出
	GPIO_InitStructure.GPIO_Pin=GPIO_Pin_10;//PB10=USART3_TX
	GPIO_InitStructure.GPIO_Speed=GPIO_Speed_50MHz;
	GPIO_Init(GPIOB,&GPIO_InitStructure);
	GPIO_InitStructure.GPIO_Mode=GPIO_Mode_IPU;//上拉输入
	GPIO_InitStructure.GPIO_Pin=GPIO_Pin_11;//PB11=USART3_RX
	GPIO_InitStructure.GPIO_Speed=GPIO_Speed_50MHz;
	GPIO_Init(GPIOB,&GPIO_InitStructure);

	USART_InitTypeDef USART_InitStructure;//USART初始化
	USART_InitStructure.USART_BaudRate=115200;//波特率115200（100Hz 流需要）
	USART_InitStructure.USART_HardwareFlowControl=USART_HardwareFlowControl_None;
	USART_InitStructure.USART_Mode=USART_Mode_Rx|USART_Mode_Tx;
	USART_InitStructure.USART_Parity=USART_Parity_No;
	USART_InitStructure.USART_StopBits=USART_StopBits_1;
	USART_InitStructure.USART_WordLength=USART_WordLength_8b;
	USART_Init(USART3,&USART_InitStructure);

	USART_ITConfig(USART3,USART_IT_RXNE,ENABLE);//蓝牙接收中断

	//中断
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);
	NVIC_InitTypeDef NVIC_InitStructure;
	NVIC_InitStructure.NVIC_IRQChannel=USART3_IRQn;
	NVIC_InitStructure.NVIC_IRQChannelCmd=ENABLE;
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority=2;
	NVIC_InitStructure.NVIC_IRQChannelSubPriority=1;
	NVIC_Init(&NVIC_InitStructure);

	USART_Cmd(USART3,ENABLE);//USART3使能
}

/*
 * E1 实验指令（ASCII 单字节，USART3 接收中断）：
 *   'R' (0x52) —— 开始采集：时间戳 ms 清零
 *   'G' (0x47) —— 前进（连续步态），并打 GO 标记
 *   'S' (0x53) —— 停止并站定
 *   'F' (0x46) —— FSM 开（E1 无 FSM 逻辑，仅存标志）
 *   'N' (0x4E) —— FSM 关
 *   'T' (0x54) —— 自测模式：站3s测零偏→走200s积分yaw→自动停（结果存好待查）
 *   'Y' (0x59) —— 查询自测结果：连发 YAW（蓝牙重连后发 Y 即可取到）
 *   'U' (0x55) —— 左后 trim +1°（运行时微调，立即生效）
 *   'D' (0x44) —— 左后 trim -1°（运行时微调，立即生效）
 *   '1' (0x31) / '2' (0x32) —— 兼容旧指令：停 / 前进
 * 注意：不再回显，保证数据流干净。
 */
void USART3_IRQHandler(void)
{
	if(USART_GetITStatus(USART3,USART_IT_RXNE)==SET)
	{
		uint8_t cmd = USART_ReceiveData(USART3);

		switch(cmd)
		{
			case 'R': g_ms = 0; break;
			case 'G': Sustainedmove = 1; Action_Mode = 4; g_pending_go = 1; break;
			case 'S': Sustainedmove = 0; Action_Mode = 2; g_do_stand = 1;   break;
			case 'F': g_fsm_on = 1; break;
			case 'N': g_fsm_on = 0; break;
			case 'T':
				// 自测模式：先站定，清零累加器，进入相位1（站零偏）
				g_test_phase = 1;
				g_test_t0    = g_ms;
				g_bias_sum   = 0;
				g_bias_n     = 0;
				g_test_bias  = 0.0f;
				g_test_yaw   = 0.0f;
				g_yaw_ready  = 0;
				g_report_cnt = 0;
				Sustainedmove = 0; Action_Mode = 2; g_do_stand = 1;
				break;
			case 'Y':
				g_report_cnt = 5;   // 连发 5 次 YAW，确保至少一次到 PC
				break;
			case 'U':
				ServoTrim[2] += 1.0f;   // 左后 trim +1°
				g_trim_report = 1;
				break;
			case 'D':
				ServoTrim[2] -= 1.0f;   // 左后 trim -1°
				g_trim_report = 1;
				break;
			case '1': Sustainedmove = 0; Action_Mode = 2; g_do_stand = 1;   break;
			case '2': Sustainedmove = 1; Action_Mode = 4; g_pending_go = 1; break;
			default: break;
		}

		USART_ClearITPendingBit(USART3,USART_IT_RXNE);
	}
}

/* 通过蓝牙串口发送一个字符串（阻塞，逐字节等 TXE） */
void BlueTooth_SendString(const char *str)
{
	while(*str)
	{
		while(USART_GetFlagStatus(USART3, USART_FLAG_TXE) == RESET);
		USART_SendData(USART3, (uint8_t)(*str));
		str++;
	}
}
