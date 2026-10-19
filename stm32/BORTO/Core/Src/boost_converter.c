/*
 * boost_converter.c
 *
 *  Created on: Oct 18, 2026
 *      Author: Zachary Barber
 */

#include "boost_converter.h"

static TIM_HandleTypeDef *boost_htim = NULL;

void Boost_Init(TIM_HandleTypeDef *htim) {
    boost_htim = htim;
    if (boost_htim != NULL) {
        __HAL_TIM_SET_COMPARE(boost_htim, TIM_CHANNEL_2, 0);
    }
}

void Boost_Start(void) {
    if (boost_htim == NULL) return;

    // Start complementary output pair on TIM1 Channel 2 (CH2 and CH2N)
    HAL_TIM_PWM_Start(boost_htim, TIM_CHANNEL_2);
    HAL_TIMEx_PWMN_Start(boost_htim, TIM_CHANNEL_2);
}

void Boost_Stop(void) {
    if (boost_htim == NULL) return;

    // Safely turn off both Channel 2 outputs
    HAL_TIMEx_PWMN_Stop(boost_htim, TIM_CHANNEL_2);
    HAL_TIM_PWM_Stop(boost_htim, TIM_CHANNEL_2);
    __HAL_TIM_SET_COMPARE(boost_htim, TIM_CHANNEL_2, 0);
}

void Boost_SetDutyCycle(float duty_percent) {
    if (duty_percent < BOOST_MIN_DUTY_PCT) {
        duty_percent = BOOST_MIN_DUTY_PCT;
    } else if (duty_percent > BOOST_MAX_DUTY_PCT) {
        duty_percent = BOOST_MAX_DUTY_PCT;
    }

    uint16_t compare_val = (uint16_t)((duty_percent / 100.0f) * BOOST_TIMER_ARR);
    Boost_SetRawCompare(compare_val);
}

void Boost_SetRawCompare(uint16_t compare_val) {
    if (boost_htim == NULL) return;

    uint16_t min_raw = (uint16_t)((BOOST_MIN_DUTY_PCT / 100.0f) * BOOST_TIMER_ARR);
    uint16_t max_raw = (uint16_t)((BOOST_MAX_DUTY_PCT / 100.0f) * BOOST_TIMER_ARR);

    if (compare_val < min_raw) compare_val = min_raw;
    if (compare_val > max_raw) compare_val = max_raw;

    __HAL_TIM_SET_COMPARE(boost_htim, TIM_CHANNEL_2, compare_val);
}

