/*
 * sensors.c
 *
 *  Created on: Oct 25, 2026
 *      Author: zachary
 */

/*
 * Implementation of ADC DMA readings, LM741 difference-amp current reconstruction,
 * physical unit conversions, and EMA filtering.
 */

#include "sensors.h"
#include "buck_converter.h"
#include "boost_converter.h"
#include "stm32g4xx_ll_adc.h" // For __LL_ADC_CALC_VREFANALOG_VOLTAGE

// Private DMA buffers:
// adc_raw[0]  -> ADC1 Rank 1: Battery Current (LM741 diff-amp + 10k/10k divider)
// adc_raw[1]  -> ADC1 Rank 2: Battery / Buck Voltage (100k/10k divider to System GND)
// adc_raw[2]  -> ADC1 Rank 3: Internal VREFINT (optional; falls back to 3.3V if 0)
//
// adc2_raw[0] -> ADC2 Rank 1: Boost Voltage (divider to System GND)
#define ADC1_CHANNEL_COUNT  2   // Change to 3 once VREFINT is enabled as Rank 3 in CubeMX

static volatile uint16_t adc_raw[3]  = {0, 0, 0};
static volatile uint16_t adc2_raw[1] = {0};

// --- Rolling Average (EMA Filter) State Variables ---
static float filt_buck_current  = 0.0f;
static float filt_buck_voltage  = 24.0f;  // Pre-seeded near 24V target
static float filt_boost_voltage = 33.9f;  // Pre-seeded near 33.9V target

// --- Smoothing Factors (0.0 to 1.0) ---
#define ALPHA_CURRENT   0.05f  // Light filter for fast inner current loop
#define ALPHA_VOLTAGE   0.05f  // Moderate filter for outer voltage loops

void Sensors_Init_Start(ADC_HandleTypeDef *hadc) {
    if (hadc == NULL) return;

    // 1. Calibrate the STM32G4 ADC for accurate single-ended readings
    HAL_ADCEx_Calibration_Start(hadc, ADC_SINGLE_ENDED);

    // 2. Start ADC1 in DMA mode
    HAL_ADC_Start_DMA(hadc, (uint32_t*)adc_raw, ADC1_CHANNEL_COUNT);
}

void Sensors_Init_Start_Boost(ADC_HandleTypeDef *hadc2) {
    if (hadc2 == NULL) return;

    HAL_ADCEx_Calibration_Start(hadc2, ADC_SINGLE_ENDED);
    HAL_ADC_Start_DMA(hadc2, (uint32_t*)adc2_raw, 1);
}

float Sensors_Get_VDDA_Volts(void) {
    uint16_t raw_vref = adc_raw[2];

    // Uses 3.300V nominal until VREFINT is enabled as Rank 3 in CubeMX
    if (raw_vref == 0) {
        return ADC_VREF_NOMINAL_VOLTS;
    }

    uint32_t vdda_mv = __LL_ADC_CALC_VREFANALOG_VOLTAGE(raw_vref, LL_ADC_RESOLUTION_12B);
    return (float)vdda_mv * 0.001f;
}

float Sensors_Get_Buck_Current_Amps(void) {
    float vdda_volts = Sensors_Get_VDDA_Volts();

    // 1. Convert raw 0-4095 count to STM32 pin voltage (e.g., ~2.475V at 0A)
    float pin_voltage = ((float)adc_raw[0] / ADC_MAX_COUNTS) * vdda_volts;

    // 2. Undo the 10k/10k divider (x2) and subtract the STM32 +3.3V reference bias
    //    to recover IC1's VIOUT relative to VDD (0.33V to 2.97V, 1.65V @ 0A)
    float v_viout = (CURR_DIFFAMP_DIV_GAIN * pin_voltage) - vdda_volts;

    // 3. Convert VIOUT to signed Amps (+/- 5.0A)
    float raw_amps = (v_viout - CURR_SENSOR_ZERO_OFFSET_V) / CURR_SENSOR_SENSITIVITY;

    // 4. Apply rolling average (EMA)
    filt_buck_current = (ALPHA_CURRENT * raw_amps) + ((1.0f - ALPHA_CURRENT) * filt_buck_current);
    return filt_buck_current;
}

float Sensors_Get_Buck_Voltage_Volts(void) {
    float vdda_volts = Sensors_Get_VDDA_Volts();

    // Direct System-GND-referenced conversion
    float pin_voltage = ((float)adc_raw[1] / ADC_MAX_COUNTS) * vdda_volts;
    float raw_volts   = pin_voltage * VOLT_DIVIDER_RATIO;

    filt_buck_voltage = (ALPHA_VOLTAGE * raw_volts) + ((1.0f - ALPHA_VOLTAGE) * filt_buck_voltage);
    return filt_buck_voltage;
}

float Sensors_Get_Boost_Voltage_Volts(void) {
    float vdda_volts = Sensors_Get_VDDA_Volts();

    // Direct System-GND-referenced conversion
    float pin_voltage = ((float)adc2_raw[0] / ADC_MAX_COUNTS) * vdda_volts;
    float raw_volts   = pin_voltage * BOOST_VOLT_DIVIDER_RATIO;

    filt_boost_voltage = (ALPHA_VOLTAGE * raw_volts) + ((1.0f - ALPHA_VOLTAGE) * filt_boost_voltage);
    return filt_boost_voltage;
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) {
    if (hadc->Instance == ADC1) {
        Buck_Control_Task();
    }
    else if (hadc->Instance == ADC2) {
        Boost_Control_Task();
    }
}
