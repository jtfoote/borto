/*
 * pi_controller.c
 *
 *  Created on: Oct 25, 2026
 *      Author: zachary
 */

/*
 * Implementation of discrete-time PI control with anti-windup.
 */

#include "pi_controller.h"
#include <stddef.h>

/**
 * @brief Initializes a PI_Controller instance with gains, limits, and sample time.
 */
void PI_Init(PI_Controller *pi, float Kp, float Ki, float out_min, float out_max, float Ts) {
    if (pi == NULL) return;

    pi->Kp = Kp;
    pi->Ki = Ki;
    pi->out_min = out_min;
    pi->out_max = out_max;
    pi->Ts = Ts;
    pi->integral_sum = 0.0f;
}

/**
 * @brief Clears the accumulated integral sum (useful when stopping/restarting a converter).
 */
void PI_Reset(PI_Controller *pi) {
    if (pi == NULL) return;
    pi->integral_sum = 0.0f;
}

/**
 * @brief Computes one discrete step of the PI controller.
 * @param pi          Pointer to the PI_Controller instance
 * @param reference   Target setpoint (e.g., Target Volts or Target Amps)
 * @param measurement Current sensor reading from ADC (in matching Volts or Amps)
 * @return Clamped control output (e.g., Target Amps or PWM Duty Cycle %)
 */
float PI_Update(PI_Controller *pi, float reference, float measurement) {
    if (pi == NULL) return 0.0f;

    // 1. Calculate Error: Error[k] = Reference - Sensor_Reading[k]
    float error = reference - measurement;

    // 2. Accumulate Integral: Integral_Sum[k] = Integral_Sum[k-1] + (Error[k] * Ts)
    pi->integral_sum += (error * pi->Ts);

    // 3. Calculate RawPI Output: Output[k] = (Kp * Error[k]) + (Ki * Integral_Sum[k])
    float output = (pi->Kp * error) + (pi->Ki * pi->integral_sum);

    // 4. Output Clamping & Back-Calculation Anti-Windup
    if (output > pi->out_max) {
        output = pi->out_max;
        if (pi->Ki != 0.0f) {
            pi->integral_sum = (pi->out_max - (pi->Kp * error)) / pi->Ki;
        }
    }
    else if (output < pi->out_min) {
        output = pi->out_min;
        if (pi->Ki != 0.0f) {
            pi->integral_sum = (pi->out_min - (pi->Kp * error)) / pi->Ki;
        }
    }

    return output;
}
