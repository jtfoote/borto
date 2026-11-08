/*  stm_to_rasp_pi.c
 *  Created on: Nov 8, 2026
 *  Author: Jaden
 *  Description: This file contains functions for sending data from the STM32 to the Raspberry Pi
 */
#include "stm_to_rasp_pi.h"

int validate_data(BORTOData_t *data) {
    // First check if device is in error. If so, the 'status' field should be set to ERROR and the 'error' field should not be NO_ERROR. Otherwise, the 'status' field should be set to CHARGING_OK or DISCHARGING_OK and the 'error' field should be NO_ERROR.
    if (data->status == ERROR && data->error == NO_ERROR) {
        return 1; // Invalid: status is ERROR but error is NO_ERROR
    }
    if (data->status != ERROR && data->error != NO_ERROR) {
        return 2; // Invalid: status is not ERROR but error is not NO_ERROR
    }
    // Next, verify that the location matches the datatype sent
    switch (data->location) {
        case DC1:
        case DC2:
            if (data->voltage == 0) {
                return 3; // Invalid: DC locations should have a voltage value
            }
            else if (data->voltage > 50000) {
                    return 7; // Invalid: Voltage exceeds maximum expected value
            }
            break;
        case BATTERY:
            if (data->current == 0) {
                return 4; // Invalid: Battery location should have a current value
            }
            else if (data->current > 5000) {
                return 8; // Invalid: Current exceeds maximum expected value
            }
            break;
        case ENCLOSURE:
            if (data->temperature == 0) {
                return 5; // Invalid: Enclosure location should have a temperature value
            }
            break;
        case INVERTER:
            if (data->duty_cycle == 0) {
                return 9; // Invalid: Inverter location should have a duty cycle value
            }
            else if (data->duty_cycle > 1000) {
                return 10; // Invalid: Duty cycle exceeds maximum expected value
            }
            break;
        default:
            return 6; // Invalid: Unknown location
    }
    return 0; // Data is valid
}

int send_data_to_pi(UART_HandleTypeDef *huart, char *buffer, uint16_t buffer_size, BORTOData_t *data) {
    /*This function will first parse the data struct to ensure it is in the correct format, then send it over UART to the Raspberry Pi. The message format will be a comma-separated string with a newline at the end. The strings "ne" and "ee" will indicate the start and end of a new entry.
    */
    int valid_data = validate_data(data);
    if (valid_data != 0) return valid_data; // Return the error code from validate_data if data is invalid

    
    uint16_t uart_message_length;
    uart_message_length = snprintf(buffer, buffer_size, "ne%d,%d,%d,%d,%d,%d,%d,%d,%d,%dee\r\n",
        data->location,
        data->status,
        data->error,
        data->voltage,
        data->current,
        data->temperature,
        data->duty_cycle,
        data->setpoint,
        data->sensor_slope,
        data->sensor_offset
    );
    HAL_UART_Transmit(huart, (uint8_t *)buffer, uart_message_length, HAL_MAX_DELAY);
    return 0; // Return 0 for success
}