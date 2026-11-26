/*
 * sensors.h
 *
 *  Created on: Oct 25, 2026
 *      Author: zachary
 */

/*
 * Handles ADC DMA buffers and conversions to physical Volts and Amps
 * with STM32G474RE referenced to System GND (0V).
 */

#ifndef INC_SENSORS_H_
#define INC_SENSORS_H_

#include "main.h"

// --- ADC CONSTANTS ---
#define ADC_MAX_COUNTS              4095.0f
#define ADC_VREF_NOMINAL_VOLTS      3.300f

// --- ADC1 Rank 1: ACS722LLCTR-05AB-T via LM741 Difference Amp + 10k/10k Divider ---
// V_ADC = ((R6 / (R5 + R6)) * ((V_VIOUT - V_DD) + V_3V3)) = 0.5 * (V_VIOUT + V_3V3)
// ACS722LLCTR-05AB-T (+/-5A bidirectional): 0A = VCC/2 (~1.65V), Sensitivity = 264 mV/A
#define CURR_DIFFAMP_DIV_GAIN       2.0f    // Inverse of 10k / (10k + 10k) output divider
#define CURR_SENSOR_ZERO_OFFSET_V   1.650f  // IC1 VIOUT at 0A (half of IC1's 3.3V supply)
#define CURR_SENSOR_SENSITIVITY     0.264f  // Volts per Amp for ACS722LLCTR-05AB-T (264 mV/A)

// --- ADC1 Rank 2: Buck / 24V SLA Battery Voltage Divider (System GND referenced) ---
// Ratio = (R1 + R2) / R2 -> (100k + 10k) / 10k = 11.0f
#define VOLT_DIVIDER_RATIO          11.0f

// --- ADC2 Rank 1: Boost Output Voltage Divider (System GND referenced) ---
#define BOOST_VOLT_DIVIDER_RATIO    18.3f

// --- Function Prototypes ---
void Sensors_Init_Start(ADC_HandleTypeDef *hadc);
void Sensors_Init_Start_Boost(ADC_HandleTypeDef *hadc2);

float Sensors_Get_VDDA_Volts(void);
float Sensors_Get_Buck_Current_Amps(void);
float Sensors_Get_Buck_Voltage_Volts(void);
float Sensors_Get_Boost_Voltage_Volts(void);

#endif /* INC_SENSORS_H_ */
