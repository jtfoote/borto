/*
 * boost_converter.h
 *
 *  Created on: Oct 18, 2026
 *      Author: Zachary Barber
 */

#include "main.h"

#ifndef INC_BOOST_CONVERTER_H_
#define INC_BOOST_CONVERTER_H_

// Matching TIM1 setup: ARR = 4166 for 20.4 kHz center-aligned mode
#define BOOST_TIMER_ARR      4166

// Boost converter duty cycle limits.
// - Minimum D (5%): Prevents near-zero energy transfer.
// - Maximum D (85%): Limits maximum theoretical boost ratio (Vout = Vin / (1 - D))
//   to prevent extreme inductor saturation, output over-voltage, and driver UVLO.
#define BOOST_MIN_DUTY_PCT   5.0f   // 5.0% minimum duty cycle
#define BOOST_MAX_DUTY_PCT   85.0f  // 85.0% maximum duty cycle

/* ============================================================================
 * Function Prototypes
 * ============================================================================
 */

/**
 * @brief Binds the target TIM handle to the boost converter module and clears CCR2.
 * @param htim Pointer to the initialized TIM handle (&htim1)
 */
void Boost_Init(TIM_HandleTypeDef *htim);

/**
 * @brief Enables complementary PWM generation on TIM1 CH2 and CH2N (with BDTR dead-time active).
 */
void Boost_Start(void);

/**
 * @brief Safely disables PWM generation on both CH2 and CH2N and clears compare register.
 */
void Boost_Stop(void);

/**
 * @brief Sets the boost low-side switch duty cycle as a float percentage.
 *        Clamps input between BOOST_MIN_DUTY_PCT and BOOST_MAX_DUTY_PCT.
 * @param duty_percent Target low-side duty cycle percentage (5.0 to 85.0)
 */
void Boost_SetDutyCycle(float duty_percent);

/**
 * @brief Sets the raw capture/compare register (CCR2) value directly.
 *        Enforces clamping against BOOST_MIN_DUTY_PCT and BOOST_MAX_DUTY_PCT raw limits.
 * @param compare_val Target raw CCR2 register value (0 to 4166)
 */
void Boost_SetRawCompare(uint16_t compare_val);



#endif /* INC_BOOST_CONVERTER_H_ */
