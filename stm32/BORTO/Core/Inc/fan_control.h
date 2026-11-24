#ifndef FAN_CONTROL_H
#define FAN_CONTROL_H

/* Call once after ADC1 and TIM1 initialization. */
void Fan_Init(void);

/* Call repeatedly from the main loop. */
void Fan_Update(void);

#endif /* FAN_CONTROL_H */
