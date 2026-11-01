/*
 * buck_converter.c
 *
 *  Created on: Oct 18, 2026
 *      Author: Zachary Barber
 */

#include "buck_converter.h"
#include "pi_controller.h"
#include "sensors.h"

// Private PI Controller instances for the Buck stage
static PI_Controller buck_voltage_ctrl;
static PI_Controller buck_current_ctrl;
static float target_battery_voltage = 27.9f; // 24V SLA charge target

volatile float buckdebug_measured_current = 0.0f;
volatile float buckdebug_measured_voltage = 0.0f;
volatile float buckdebug_duty_cycle = 0.0f;


// Call this inside Buck_Init() or from main.c
void Buck_PI_Init(void) {
    // Outer Voltage Loop: Outputs 0.0A to 2.0A target current
    PI_Init(&buck_voltage_ctrl, 2.5f, 60.0f, 0.0f, 2.0f, 0.00005f);

    // Inner Current Loop: Outputs 5.0% to 90.0% PWM duty cycle
    PI_Init(&buck_current_ctrl, 2.5f, 60.0f, BUCK_MIN_DUTY_PCT, BUCK_MAX_DUTY_PCT, 0.00005f);
}



void Buck_Control_Task(void) {
    float measured_current = Sensors_Get_Buck_Current_Amps();
    float measured_voltage = Sensors_Get_Buck_Voltage_Volts();

    float commanded_current = PI_Update(&buck_voltage_ctrl, target_battery_voltage, measured_voltage);
    float new_duty_cycle = PI_Update(&buck_current_ctrl, commanded_current, measured_current);

    buckdebug_measured_current = measured_current;
    buckdebug_measured_voltage = measured_voltage;
    buckdebug_duty_cycle = new_duty_cycle;

    Buck_SetDutyCycle(new_duty_cycle);
}



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

volatile float compare_val_watch = 0;

void Buck_SetDutyCycle(float duty_percent) {
    // Clamp duty cycle within safe operating percentage bounds
    if (duty_percent < BUCK_MIN_DUTY_PCT) {
        duty_percent = BUCK_MIN_DUTY_PCT;
    } else if (duty_percent > BUCK_MAX_DUTY_PCT) {
        duty_percent = BUCK_MAX_DUTY_PCT;
    }

    uint16_t compare_val = (uint16_t)((duty_percent / 100.0f) * BUCK_TIMER_ARR);
    Buck_SetRawCompare(compare_val);

    compare_val_watch = compare_val;
}

volatile float compare_val_watchh = 0;

void Buck_SetRawCompare(uint16_t compare_val) {
    if (buck_htim == NULL) return;

    // Convert duty percentage limits into raw register limits
    uint16_t min_raw = (uint16_t)((BUCK_MIN_DUTY_PCT / 100.0f) * BUCK_TIMER_ARR);
    uint16_t max_raw = (uint16_t)((BUCK_MAX_DUTY_PCT / 100.0f) * BUCK_TIMER_ARR);

    // Enforce register-level clamping
    if (compare_val < min_raw) compare_val = min_raw;
    if (compare_val > max_raw) compare_val = max_raw;

    compare_val_watchh = compare_val;

    __HAL_TIM_SET_COMPARE(buck_htim, TIM_CHANNEL_1, compare_val);
}


