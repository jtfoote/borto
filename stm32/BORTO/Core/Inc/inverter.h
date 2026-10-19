/*
 * inverter.h
 *
 *  Created on: Oct 18, 2026
 *      Author: zachary
 */

#ifndef INC_INVERTER_H_
#define INC_INVERTER_H_

#include "main.h"

/* ============================================================================
 * Configuration Constants
 * ============================================================================
 */

// Matching TIM8 setup: ARR = 4166 for 20.4 kHz center-aligned mode
#define INVERTER_TIMER_ARR      4166

// Quarter-wave sine lookup table size (90 degrees = 85 samples)
#define QUARTER_SAMPLES         85
#define HALF_CYCLE_STEPS        (QUARTER_SAMPLES * 2) // 170 steps for 180 degrees

/* ============================================================================
 * Function Prototypes
 * ============================================================================
 */

/**
 * @brief Binds the TIM8 handle to the inverter module and resets output compare registers.
 * @param htim Pointer to the initialized TIM handle (&htim8)
 */
void Inverter_Init(TIM_HandleTypeDef *htim);

/**
 * @brief Starts PWM generation on TIM8 Channels 1-4 and enables the update interrupt.
 */
void Inverter_Start(void);

/**
 * @brief Safely disables all 4 PWM outputs and stops the timer base interrupt.
 */
void Inverter_Stop(void);

#endif /* INC_INVERTER_H_ */
