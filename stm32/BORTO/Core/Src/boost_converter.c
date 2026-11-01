/*
 * boost_converter.c
 *
 *  Created on: Oct 18, 2026
 *      Author: Zachary Barber
 */

#include "boost_converter.h"
#include "pi_controller.h"
#include "sensors.h"

static TIM_HandleTypeDef *boost_htim = NULL;

// Private PI Controller instance for the Boost stage
static PI_Controller boost_voltage_ctrl;
static float target_boost_voltage = 33.941f; // Target DC link for inverter

volatile float debug_boost_voltage = 0.0f;
volatile float debug_boost_duty_cycle = 0.0f;
volatile float debug_compare_val = 0.0f;


void Boost_PI_Init(void) {
    // Voltage Loop directly outputs 5.0% to 95.0% PWM duty cycle
    // Note: Start with low gains! Boost converters have a Right-Half-Plane zero.
    PI_Init(&boost_voltage_ctrl, 0.1f, 30.0f, BOOST_MIN_DUTY_PCT, BOOST_MAX_DUTY_PCT, 0.00005f);
}



void Boost_Control_Task(void) {
    float measured_voltage = Sensors_Get_Boost_Voltage_Volts();
    float new_duty_cycle = PI_Update(&boost_voltage_ctrl, target_boost_voltage, measured_voltage);


    debug_boost_voltage = measured_voltage;
    debug_boost_duty_cycle = new_duty_cycle;
    Boost_SetDutyCycle(new_duty_cycle);
}

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
    debug_compare_val = compare_val;
    Boost_SetRawCompare(compare_val);
}

void Boost_SetRawCompare(uint16_t compare_vall) {
    if (boost_htim == NULL) return;

    uint16_t min_raw = (uint16_t)((BOOST_MIN_DUTY_PCT / 100.0f) * BOOST_TIMER_ARR);
    uint16_t max_raw = (uint16_t)((BOOST_MAX_DUTY_PCT / 100.0f) * BOOST_TIMER_ARR);

    if (compare_vall < min_raw) compare_vall = min_raw;
    if (compare_vall > max_raw) compare_vall = max_raw;

    __HAL_TIM_SET_COMPARE(boost_htim, TIM_CHANNEL_2, compare_vall);
}

