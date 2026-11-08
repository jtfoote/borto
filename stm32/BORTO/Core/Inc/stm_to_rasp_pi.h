/*  stm_to_rasp_pi.h
 *  Created on: Nov 8, 2026
 *  Author: Jaden
 *  Description: This file contains the header for functions that send data from the STM32 to the Raspberry Pi
 */
#ifndef STM_TO_RASP_PI_H
#define STM_TO_RASP_PI_H

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#include "main.h"
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
    CHARGING,
    DISCHARGING,
    CHARGED,
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
    int16_t current; // in milliamps
    uint16_t temperature; // in tenths of degrees Celsius
    uint16_t duty_cycle; // in tenths of percent
    uint16_t setpoint; // in millivolts or milliamps depending on context
    int16_t sensor_slope;
    int16_t sensor_offset;
} BORTOData_t;

// Reverse-UART Command Types (Pi -> STM32)
typedef enum {
    CMD_SET_PARAM  = 0, // Update setpoint, slope, and offset for a Location_t
    CMD_SET_MODE   = 1, // Switch power stage state (Standby, Charge, Discharge)
    CMD_SYS_ACTION = 2  // System-level action (Clear Fault, Reboot MCU, Safe Shutdown)
} CommandType_t;

typedef enum {
    MODE_STANDBY   = 0, // Idle / Stage 3 Float maintenance
    MODE_CHARGE    = 1, // Force or TOU Off-Peak Charging (AC -> DC1 -> Battery)
    MODE_DISCHARGE = 2  // Force or TOU On-Peak Discharging (Battery -> DC2 -> Inverter)
} OperatingMode_t;

typedef enum {
    SYS_CLEAR_FAULT = 0, // Clear latched error state
    SYS_REBOOT_MCU  = 1, // Trigger NVIC_SystemReset() on STM32
    SYS_SHUTDOWN    = 2  // Disable all PWM gate drivers & open relays safely
} SysAction_t;

typedef struct {
    CommandType_t cmd_type;
    uint8_t target;         // Location_t (if CMD_SET_PARAM), OperatingMode_t (if CMD_SET_MODE), or SysAction_t (if CMD_SYS_ACTION)
    int16_t setpoint;       // val1: in mV or mA
    int16_t sensor_slope;   // val2: scaled x1000
    int16_t sensor_offset;  // val3: scaled x1000
} BORTOCommand_t;

// Function prototypes
int validate_data(BORTOData_t *data);

int send_data_to_pi(UART_HandleTypeDef *huart, char *buffer, uint16_t buffer_size, BORTOData_t *data);

int parse_command_from_pi(const char *rx_buffer, BORTOCommand_t *cmd_out);

#endif