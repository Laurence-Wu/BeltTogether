// =====================================================
// ADC Sampling Module
// =====================================================
#ifndef ADC_SAMPLER_H
#define ADC_SAMPLER_H

#include <Arduino.h>
#include "config.h"

// Initialize ADC sampler
void initADCSampler();

// Interrupt service routine - reads all 12 bits
void sampleISR();

#endif
