/*
 * Reference implementation of the single-axis heading-feedback P-controller
 * (Section 3.3 of the ICCAI 2026 paper). Reconstructed from the paper's
 * specification; the exact on-target source was not archived, but this is the
 * complete control law.
 *
 *   u = K_P * e,   K_P = 0.15,   dead zone = 3 deg,   |u| <= 12 deg
 *
 * e  = integrated yaw error (gyro z, zero bias subtracted during a 3 s
 *      standing phase before each run).
 * u  = trim offset (degrees) added to the left-hind servo neutral position.
 *
 * The stock gait is a non-blocking 8-phase trot at 300 ms/phase, driven by
 * TIM2 PWM on 4 SG90 servos. The IMU is an MPU6050 on software I2C, gyro
 * scale +-2000 dps -> 16.4 LSB/(deg/s). The loop runs at 100 Hz.
 */

#include <math.h>

#define KP             0.15f   /* proportional gain */
#define DEAD_ZONE_DEG  3.0f    /* yaw dead zone (deg) */
#define U_LIMIT_DEG    12.0f   /* output limit (deg) */
#define GYRO_SCALE     16.4f   /* LSB per deg/s at +-2000 dps */
#define DT             0.01f   /* 100 Hz control period (s) */
#define TRIM_LEFT_HIND 50.0f   /* baseline trim2 for the left-hind servo */

typedef struct {
    float yaw;      /* integrated yaw (deg) */
    float bias;     /* gyro z zero bias (deg/s), measured while standing */
    int   bias_n;   /* number of bias samples */
} heading_ctrl_t;

static heading_ctrl_t ctrl;

/* Call during the 3 s standing phase, before each run. */
void heading_bias_sample(float gz_raw)
{
    ctrl.bias = (ctrl.bias * ctrl.bias_n + gz_raw / GYRO_SCALE) / (ctrl.bias_n + 1);
    ctrl.bias_n += 1;
}

/* Call every 100 Hz control tick while walking. Returns the trim offset to add
 * to the left-hind servo (in degrees). */
float heading_controller_tick(float gz_raw)
{
    float gz_dps = gz_raw / GYRO_SCALE - ctrl.bias;   /* bias-corrected deg/s */
    ctrl.yaw += gz_dps * DT;                          /* integrate yaw (deg)  */

    float e = ctrl.yaw;                               /* setpoint = 0 deg      */
    if (fabsf(e) < DEAD_ZONE_DEG) {
        e = 0.0f;
    }
    float u = KP * e;
    if (u >  U_LIMIT_DEG) u =  U_LIMIT_DEG;
    if (u < -U_LIMIT_DEG) u = -U_LIMIT_DEG;

    return u;   /* left-hind servo angle = TRIM_LEFT_HIND + u */
}
