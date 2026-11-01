/*
 * pi_controller.h
 *
 *  Created on: Oct 25, 2026
 *      Author: zachary
 */

/*
 * Discrete-time PI Controller with Anti-Windup Clamping
 */

#ifndef INC_PI_CONTROLLER_H_
#define INC_PI_CONTROLLER_H_

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float Kp;              // Proportional gain
    float Ki;              // Integral gain
    float integral_sum;    // Accumulated error over time
    float out_min;         // Minimum output clamp limit
    float out_max;         // Maximum output clamp limit
    float Ts;              // Discrete sampling period in seconds (1 / f_sample)
} PI_Controller;

// Function Prototypes
void PI_Init(PI_Controller *pi, float Kp, float Ki, float out_min, float out_max, float Ts);
void PI_Reset(PI_Controller *pi);
float PI_Update(PI_Controller *pi, float reference, float measurement);

#ifdef __cplusplus
}
#endif

#endif /* INC_PI_CONTROLLER_H_ */
