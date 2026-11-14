#ifndef __BLUE_TOOTH_H
#define __BLUE_TOOTH_H

extern uint16_t Action_Mode;
extern uint16_t Face_Mode;
extern uint16_t SpeedDelay;
extern uint16_t SwingDelay;
extern uint8_t WeiBa;
extern uint16_t AllLed;  //开启灯光
extern uint16_t BreatheLed;//开启呼吸灯
extern uint16_t Sustainedmove;

/* E1 实验全局 */
extern volatile uint32_t g_ms;         // 采集时间戳(ms)，R 命令清零
extern volatile uint8_t  g_pending_go; // G 置位 → 主循环补发 GO
extern volatile uint8_t  g_do_stand;   // S 置位 → 主循环站定
extern volatile uint8_t  g_fsm_on;     // FSM 开关标志

/* 自测模式（T 命令）全局：站3s测零偏→走200s积分yaw→自动停；Y 命令查询结果 */
extern volatile uint8_t  g_test_phase; // 0=空闲 1=站零偏 2=走积分
extern volatile uint32_t g_test_t0;    // 各相位起始 ms
extern float             g_test_bias;  // 站姿 Gz 零偏(LSB)
extern float             g_test_yaw;   // 积分偏航(deg)
extern int32_t           g_bias_sum;   // 零偏累加
extern int32_t           g_bias_n;     // 零偏样本数
extern volatile uint8_t  g_yaw_ready;  // 自测完成、结果有效
extern volatile uint8_t  g_report_cnt; // Y 命令后剩余报告次数(>0 则报告)
extern volatile uint8_t  g_trim_report;// U/D 改 trim 后置位，主循环回显新值

void BlueTooth_Init(void);
void BlueTooth_SendString(const char *str);

#endif
