#include "main.h"
#include "fan_control.h"

/* Peripheral handles owned by the main project. */
extern ADC_HandleTypeDef hadc1;
extern TIM_HandleTypeDef htim1;

static float adcValue = 0.0;
static float adcVoltage = 0.0f;
static float rtdResistance = 0.0f;
static float temperatureC = 0.0f;
static uint32_t dutyCycle = 100;

static uint32_t adcSum = 0;
static uint8_t sampleCount = 0;

// Update timing
static uint32_t lastUpdate = 0;
static uint8_t firstUpdate = 1;


void Fan_Init(void)
{
    dutyCycle = 100;
    firstUpdate = 1;
    lastUpdate = 0;
    HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1,
        ((htim1.Init.Period + 1U) * dutyCycle) / 100U);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
}

void Fan_Update(void)
{

    if (firstUpdate || (HAL_GetTick() - lastUpdate >= 500U))
    {
        firstUpdate = 0;
        lastUpdate = HAL_GetTick();

        adcSum = 0;
        sampleCount = 0;

        // Take 16 ADC samples
        for (uint8_t i = 0; i < 16; i++)
        {
            if (HAL_ADC_Start(&hadc1) != HAL_OK)
            {
                HAL_ADC_Stop(&hadc1);
                break;
            }

            if (HAL_ADC_PollForConversion(&hadc1, 100) != HAL_OK)
            {
                HAL_ADC_Stop(&hadc1);
                break;
            }

            adcSum += HAL_ADC_GetValue(&hadc1);
            sampleCount++;

            HAL_ADC_Stop(&hadc1);
        }

        // Assume sensor failure until a valid reading is confirmed
        uint8_t sensorValid = 0;

        if (sampleCount == 16)
        {
            adcValue = adcSum / 16.0f;

            adcVoltage = (adcValue * 3.3f) / 4095.0f;

            if (adcValue > 0.0f && adcValue < 4095.0f)
            {
                rtdResistance = (10000.0f * adcVoltage) /
                                (3.3f - adcVoltage);

                temperatureC = (rtdResistance - 1000.0f) / 3.85f;
                //temperatureC = 50.0f;  // TEMPORARY TEST ONLY
                // Plausible operating temperature range
                if (temperatureC >= -20.0f &&
                    temperatureC <= 100.0f)
                {
                    sensorValid = 1;
                }
            }
        }

        if (sensorValid == 0)
        {
            // Sensor failure: request maximum cooling
            dutyCycle = 100;
        }
        else
        {
            // Immediately increase speed when temperature rises
            if (temperatureC >= 60.0f)
            {
                dutyCycle = 100;
            }
            else if (temperatureC >= 45.0f && dutyCycle < 75)
            {
                dutyCycle = 75;
            }
            else if (temperatureC >= 30.0f && dutyCycle < 50)
            {
                dutyCycle = 50;
            }

            // Reduce speed with 2-degree hysteresis
            if (dutyCycle == 100 && temperatureC < 58.0f)
            {
                dutyCycle = 75;
            }
            else if (dutyCycle == 75 && temperatureC < 43.0f)
            {
                dutyCycle = 50;
            }
            else if (dutyCycle == 50 && temperatureC < 28.0f)
            {
                dutyCycle = 30;
            }
        }

        // Update PWM for both normal and fault conditions
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1,
            ((htim1.Init.Period + 1U) * dutyCycle) / 100U);

    }
}
