/*
 * sensors.h
 *
 *  Created on: Oct 25, 2026
 *      Author: zachary
 */

/*
 * Handles ADC DMA buffer and conversions to physical Volts and Amps.
 */

#ifndef INC_SENSORS_H_
#define INC_SENSORS_H_

#include "main.h"

// --- SENSOR CALIBRATION CONSTANTS (Update to match your breadboard!) ---
#define ADC_MAX_COUNTS          4095.0f
#define ADC_VREF_VOLTS          3.3f

// Channel 1: Hall-Effect Current Sensor (Into 24V SLA Battery)
#define CURR_SENSOR_OFFSET_V    1.65f   // Voltage at 0A (e.g., 1.65V or 2.5V)
#define CURR_SENSOR_SENSITIVITY 0.100f  // Volts per Amp (e.g., 100mV/A = 0.100f)

// Channel 2: Voltage Divider (At Buck Output / 24V SLA Battery)
// Ratio = (R1 + R2) / R2
#define VOLT_DIVIDER_RATIO      11.0f   // Example: 100k and 10k -> (100+10)/10 = 11.0f

// Function Prototypes
void Sensors_Init_Start(ADC_HandleTypeDef *hadc);
float Sensors_Get_Buck_Current_Amps(void);
float Sensors_Get_Buck_Voltage_Volts(void);

// Boost Voltage Divider Ratio (Update based on your resistors!)
// Example: 120k and 10k -> (120 + 10) / 10 = 13.0f
#define BOOST_VOLT_DIVIDER_RATIO 18.3f

void Sensors_Init_Start_Boost(ADC_HandleTypeDef *hadc2);
float Sensors_Get_Boost_Voltage_Volts(void);

#endif /* INC_SENSORS_H_ */
