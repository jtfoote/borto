
/*
 * sensors.c
 *
 *  Created on: Oct 25, 2026
 *      Author: zachary
 */

/*
 * Implementation of ADC DMA readings, physical unit conversions, and EMA filtering.
 */

#include "sensors.h"
#include "buck_converter.h"
#include "boost_converter.h"

// Private DMA buffers:
// adc_raw[0]  -> Rank 1 (ADC1 Channel 1: Battery Current)
// adc_raw[1]  -> Rank 2 (ADC1 Channel 2: Battery Voltage)
// adc2_raw[0] -> Rank 1 (ADC2 Channel 7: Boost Voltage)
static volatile uint16_t adc_raw[2] = {0, 0};
static volatile uint16_t adc2_raw[1] = {0};

// --- NEW: Rolling Average (EMA Filter) State Variables ---
static float filt_buck_current = 0.0f;
static float filt_buck_voltage = 24.0f;  // Pre-seeded near 24V target
static float filt_boost_voltage = 33.9f; // Pre-seeded near 33.9V target

// --- NEW: Smoothing Factors (0.0 to 1.0) ---
// Smaller value = heavier smoothing, Larger value = faster response
#define ALPHA_CURRENT  0.50f  // Light filter for fast inner current loop
#define ALPHA_VOLTAGE  0.05f  // Moderate filter for outer voltage loops


void Sensors_Init_Start(ADC_HandleTypeDef *hadc) {
    if (hadc == NULL) return;

    // 1. Calibrate the STM32G4 ADC for accurate single-ended readings
    HAL_ADCEx_Calibration_Start(hadc, ADC_SINGLE_ENDED);

    // 2. Start ADC in DMA mode, automatically filling adc_raw[0] and adc_raw[1]
    HAL_ADC_Start_DMA(hadc, (uint32_t*)adc_raw, 2);
}

// --- UPDATED: Added EMA filter before returning ---
float Sensors_Get_Buck_Current_Amps(void) {
    // Convert raw 0-4095 count to pin voltage (0.0V - 3.3V)
    float pin_voltage = ((float)adc_raw[0] / ADC_MAX_COUNTS) * ADC_VREF_VOLTS;

    // Convert pin voltage to real Amps
    float raw_amps = (pin_voltage - CURR_SENSOR_OFFSET_V) / CURR_SENSOR_SENSITIVITY;

    // Apply rolling average (EMA)
    filt_buck_current = (ALPHA_CURRENT * raw_amps) + ((1.0f - ALPHA_CURRENT) * filt_buck_current);
    return filt_buck_current;
}

// --- UPDATED: Added EMA filter before returning ---
float Sensors_Get_Buck_Voltage_Volts(void) {
    // Convert raw 0-4095 count to pin voltage (0.0V - 3.3V)
    float pin_voltage = ((float)adc_raw[1] / ADC_MAX_COUNTS) * ADC_VREF_VOLTS;

    // Multiply by voltage divider ratio to get real Buck output voltage
    float raw_volts = pin_voltage * VOLT_DIVIDER_RATIO;

    // Apply rolling average (EMA)
    filt_buck_voltage = (ALPHA_VOLTAGE * raw_volts) + ((1.0f - ALPHA_VOLTAGE) * filt_buck_voltage);
    return filt_buck_voltage;
}

void Sensors_Init_Start_Boost(ADC_HandleTypeDef *hadc2) {
    if (hadc2 == NULL) return;
    HAL_ADCEx_Calibration_Start(hadc2, ADC_SINGLE_ENDED);
    HAL_ADC_Start_DMA(hadc2, (uint32_t*)adc2_raw, 1);
}

// --- UPDATED: Added EMA filter before returning ---
float Sensors_Get_Boost_Voltage_Volts(void) {
    float pin_voltage = ((float)adc2_raw[0] / ADC_MAX_COUNTS) * ADC_VREF_VOLTS;
    float raw_volts = pin_voltage * BOOST_VOLT_DIVIDER_RATIO;

    // Apply rolling average (EMA)
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
