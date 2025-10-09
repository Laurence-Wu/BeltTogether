// =====================================================
// Configuration and Pin Definitions
// =====================================================
#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Pin configuration
const uint8_t adcPins[12] = {22,23,24,25,26,27,28,29,30,31,32,33};
const uint8_t clkPin = 6;           // PWM output
const uint8_t syncPin = 2;          // Interrupt input connected to clkPin

// Sampling configuration
const float sampleRate = 10000.0;   // Hz

// Global variables for ISR
extern volatile uint16_t latestSample;
extern volatile bool newSample;

#endif
