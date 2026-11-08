/*  stm_to_rasp_pi.h
 *  Created on: Nov 8, 2026
 *  Author: Jaden
 *  Description: This file contains the header for functions that send data from the STM32 to the Raspberry Pi
 */
#ifndef STM_TO_RASP_PI_H
#define STM_TO_RASP_PI_H

#include <stdio.h>
#include <stdint.h>
/*
    The idea here is that each location will have a specific type of value associated with it. 

    DC1 -> Voltage (c/w voltage sensor slope and offset)
    BATTERY -> Current (c/w current sensor slope and offset)
    DC2 -> Voltage (c/w voltage sensor slope and offset)
    ENCLOSURE -> Temperature (c/w temperature sensor slope and offset)

    If enabled, the STM32 can also send debug information such as the current duty cycle and setpoint to the Raspberry Pi for logging and analysis. By default, the STM32 will always send these values, but the Pi will only read them if debug mode is enabled.
*/
typedef enum {
    DC1,
    BATTERY,
    DC2,
    INVERTER,
    ENCLOSURE
} Location_t;

typedef enum {
    CHARGING_OK,
    DISCHARGING_OK,
    ERROR,
} Status_t;

typedef enum {
    NO_ERROR,
    OVER_VOLTAGE,
    UNDER_VOLTAGE,
    OVER_CURRENT,
    UNDER_CURRENT,
    OVER_TEMPERATURE,
    UNDER_TEMPERATURE,
    PWM_FAULT
} Error_t;

typedef struct {
    Location_t location;
    Status_t status;
    Error_t error;
    uint16_t voltage; // in millivolts
    uint16_t current; // in milliamps
    uint16_t temperature; // in tenths of degrees Celsius
    uint16_t duty_cycle; // in tenths of percent
    uint16_t setpoint; // in millivolts or milliamps depending on context
    uint16_t sensor_slope;
    uint16_t sensor_offset;
} BORTOData_t;

// Function prototypes
int validate_data(BORTOData_t *data);

int send_data_to_pi(UART_HandleTypeDef *huart, char *buffer, uint16_t buffer_size, BORTOData_t *data);

#endif