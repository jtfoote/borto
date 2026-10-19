/*
 * buck_converter.c
 *
 *  Created on: Oct 18, 2026
 *      Author: Zachary Barber
 */

#include "buck_converter.h"

static TIM_HandleTypeDef *buck_htim = NULL;

void Buck_Init(TIM_HandleTypeDef *htim) {
    buck_htim = htim;
    // Set raw compare to 0 initially
    if (buck_htim != NULL) {
        __HAL_TIM_SET_COMPARE(buck_htim, TIM_CHANNEL_1, 0);
    }
}

void Buck_Start(void) {
    if (buck_htim == NULL) return;

    // Start complementary high-side and low-side channels with BDTR dead-time
    HAL_TIM_PWM_Start(buck_htim, TIM_CHANNEL_1);
    HAL_TIMEx_PWMN_Start(buck_htim, TIM_CHANNEL_1);
}

void Buck_Stop(void) {
    if (buck_htim == NULL) return;

    // Safely turn off both channels
    HAL_TIMEx_PWMN_Stop(buck_htim, TIM_CHANNEL_1);
    HAL_TIM_PWM_Stop(buck_htim, TIM_CHANNEL_1);
    __HAL_TIM_SET_COMPARE(buck_htim, TIM_CHANNEL_1, 0);
}

void Buck_SetDutyCycle(float duty_percent) {
    // Clamp duty cycle within safe operating percentage bounds
    if (duty_percent < BUCK_MIN_DUTY_PCT) {
        duty_percent = BUCK_MIN_DUTY_PCT;
    } else if (duty_percent > BUCK_MAX_DUTY_PCT) {
        duty_percent = BUCK_MAX_DUTY_PCT;
    }

    uint16_t compare_val = (uint16_t)((duty_percent / 100.0f) * BUCK_TIMER_ARR);
    Buck_SetRawCompare(compare_val);
}

void Buck_SetRawCompare(uint16_t compare_val) {
    if (buck_htim == NULL) return;

    // Convert duty percentage limits into raw register limits
    uint16_t min_raw = (uint16_t)((BUCK_MIN_DUTY_PCT / 100.0f) * BUCK_TIMER_ARR);
    uint16_t max_raw = (uint16_t)((BUCK_MAX_DUTY_PCT / 100.0f) * BUCK_TIMER_ARR);

    // Enforce register-level clamping
    if (compare_val < min_raw) compare_val = min_raw;
    if (compare_val > max_raw) compare_val = max_raw;

    __HAL_TIM_SET_COMPARE(buck_htim, TIM_CHANNEL_1, compare_val);
}
