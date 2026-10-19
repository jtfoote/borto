/*
 * inverter.c
 *
 *  Created on: Oct 18, 2026
 *      Author: zachary
 */

#include "inverter.h"

/* ============================================================================
 * State Machine & Private Variables
 * ============================================================================
 */

typedef enum {
    STATE_POSITIVE_HALF,
    STATE_DEADTIME_POS_TO_NEG,
    STATE_NEGATIVE_HALF,
    STATE_DEADTIME_NEG_TO_POS
} InverterState_t;

static TIM_HandleTypeDef *inverter_htim = NULL;
static volatile uint16_t sample_index = 0;
static volatile InverterState_t inv_state = STATE_POSITIVE_HALF;

// 85-element Quarter-Wave Lookup Table (Scaled to ARR = 4166)
static const uint16_t sine_table_quarter[QUARTER_SAMPLES] = {
    0, 77, 154, 231, 307, 384, 461, 537, 614, 690,
    765, 841, 916, 991, 1066, 1140, 1214, 1287, 1360, 1433,
    1505, 1576, 1647, 1718, 1788, 1857, 1926, 1994, 2061, 2127,
    2193, 2258, 2323, 2386, 2449, 2511, 2572, 2632, 2691, 2749,
    2807, 2863, 2919, 2973, 3027, 3079, 3130, 3181, 3230, 3278,
    3325, 3371, 3415, 3459, 3501, 3542, 3582, 3621, 3658, 3695,
    3730, 3763, 3796, 3827, 3857, 3885, 3912, 3938, 3962, 3986,
    4007, 4028, 4047, 4064, 4081, 4095, 4109, 4121, 4132, 4141,
    4149, 4155, 4160, 4164, 4166
};

/* ============================================================================
 * Helper Functions
 * ============================================================================
 */

static uint16_t get_sine_duty(uint16_t step) {
    if (step < QUARTER_SAMPLES) {
        // Ramp UP: Read forward (0 to 84)
        return sine_table_quarter[step];
    } else {
        // Ramp DOWN: Read backward (84 down to 0)
        return sine_table_quarter[(HALF_CYCLE_STEPS - 1) - step];
    }
}

/* ============================================================================
 * Public Module API
 * ============================================================================
 */

void Inverter_Init(TIM_HandleTypeDef *htim) {
    inverter_htim = htim;
    if (inverter_htim != NULL) {
        __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_1, 0);
        __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_2, 0);
        __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_3, 0);
        __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_4, 0);
    }
}

void Inverter_Start(void) {
    if (inverter_htim == NULL) return;

    // Enable PWM generation on all 4 independent channels
    HAL_TIM_PWM_Start(inverter_htim, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(inverter_htim, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(inverter_htim, TIM_CHANNEL_3);
    HAL_TIM_PWM_Start(inverter_htim, TIM_CHANNEL_4);

    // Enable timer update interrupt for 60 Hz sine table execution
    HAL_TIM_Base_Start_IT(inverter_htim);
}

void Inverter_Stop(void) {
    if (inverter_htim == NULL) return;

    HAL_TIM_Base_Stop_IT(inverter_htim);
    HAL_TIM_PWM_Stop(inverter_htim, TIM_CHANNEL_1);
    HAL_TIM_PWM_Stop(inverter_htim, TIM_CHANNEL_2);
    HAL_TIM_PWM_Stop(inverter_htim, TIM_CHANNEL_3);
    HAL_TIM_PWM_Stop(inverter_htim, TIM_CHANNEL_4);

    __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_1, 0);
    __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_2, 0);
    __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_3, 0);
    __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_4, 0);
}

/* ============================================================================
 * Hardware Interrupt Handler
 * ============================================================================
 */

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    if (inverter_htim != NULL && htim->Instance == inverter_htim->Instance) {

        switch (inv_state) {

            case STATE_POSITIVE_HALF: {
                uint16_t duty = get_sine_duty(sample_index);
                // Positive Half: Q1 (CH1) PWM, Q4 (CH4) 100% ON
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_1, duty);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_2, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_3, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_4, INVERTER_TIMER_ARR + 1);

                sample_index++;
                if (sample_index >= HALF_CYCLE_STEPS) {
                    sample_index = 0;
                    inv_state = STATE_DEADTIME_POS_TO_NEG;
                }
                break;
            }

            case STATE_DEADTIME_POS_TO_NEG: {
                // Zero-Crossing Pause: Force ALL gates OFF for 1 cycle (~49 us)
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_1, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_2, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_3, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_4, 0);

                inv_state = STATE_NEGATIVE_HALF;
                break;
            }

            case STATE_NEGATIVE_HALF: {
                uint16_t duty = get_sine_duty(sample_index);
                // Negative Half: Q3 (CH3) PWM, Q2 (CH2) 100% ON
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_1, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_2, INVERTER_TIMER_ARR + 1);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_3, duty);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_4, 0);

                sample_index++;
                if (sample_index >= HALF_CYCLE_STEPS) {
                    sample_index = 0;
                    inv_state = STATE_DEADTIME_NEG_TO_POS;
                }
                break;
            }

            case STATE_DEADTIME_NEG_TO_POS: {
                // Zero-Crossing Pause: Force ALL gates OFF for 1 cycle (~49 us)
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_1, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_2, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_3, 0);
                __HAL_TIM_SET_COMPARE(inverter_htim, TIM_CHANNEL_4, 0);

                inv_state = STATE_POSITIVE_HALF;
                break;
            }
        }
    }
}
