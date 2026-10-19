/*
 * buck_converter.h
 *
 *  Created on: Oct 18, 2026
 *      Author: Zachary Barber
 */

#ifndef INC_BUCK_CONVERTER_H_
#define INC_BUCK_CONVERTER_H_

#include "main.h"

// Matching TIM1 setup: ARR = 4166 for 20.4 kHz center-aligned
#define BUCK_TIMER_ARR      4166

// Duty cycle limits to protect IRS21867 high-side bootstrap charging
#define BUCK_MIN_DUTY_PCT   5.0f   // 5% minimum
#define BUCK_MAX_DUTY_PCT   90.0f  // 90% maximum (guarantees low-side refresh time)

/**
 * @brief Binds the TIM handle to the buck module and resets duty cycle.
 * @param htim Pointer to TIM1 handle (&htim1)
 */
void Buck_Init(TIM_HandleTypeDef *htim);

/**
 * @brief Enables complementary PWM generation on TIM1 CH1 and CH1N.
 */
void Buck_Start(void);

/**
 * @brief Safely disables PWM generation on TIM1 CH1 and CH1N.
 */
void Buck_Stop(void);

/**
 * @brief Sets the duty cycle as a float percentage (5.0% to 90.0%).
 * @param duty_percent Target duty cycle percentage
 */
void Buck_SetDutyCycle(float duty_percent);

/**
 * @brief Sets raw compare register value directly (clamped to safe limits).
 * @param compare_val Raw CCR1 register value
 */
void Buck_SetRawCompare(uint16_t compare_val);


#endif /* INC_BUCK_CONVERTER_H_ */
