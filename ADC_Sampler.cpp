// =====================================================
// ADC Sampling Implementation
// =====================================================
#include "ADC_Sampler.h"

void initADCSampler() {
  // Configure ADC input pins
  for (int i = 0; i < 12; i++) {
    pinMode(adcPins[i], INPUT);
  }

  // Sync interrupt setup
  pinMode(syncPin, INPUT);
  attachInterrupt(digitalPinToInterrupt(syncPin), sampleISR, RISING);
}

// Interrupt: read all 12 bits on rising clock edge
void sampleISR() {
  uint16_t val = 0;
  for (int i = 0; i < 12; i++) {
    val |= (digitalRead(adcPins[i]) << i);
  }
  latestSample = val;
  newSample = true;
}
