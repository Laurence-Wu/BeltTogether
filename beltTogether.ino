// =====================================================
// AD9226 Parallel Read + Clock Output + CSV Logging
// Board: Arduino Mega 2560
// D0..D11 -> 22..33
// CLK -> pin 6 (PWM)
// Also wire pin 6 -> pin 2 for ISR sync
// Open Serial Monitor or Plotter (Ctrl+Shift+L) at 115200 baud
// To save: use any serial logger and save output as data.csv
// =====================================================

#include "config.h"
#include "ClockGen.h"
#include "ADC_Sampler.h"

// Define global variables declared in config.h
volatile uint16_t latestSample = 0;
volatile bool newSample = false;

void setup() {
  Serial.begin(115200);
  Serial.println("Time_us,Sample");   // CSV header with timestamp

  // Initialize ADC sampler
  initADCSampler();

  // Clock output setup
  setupClockPWM(clkPin, sampleRate);
}

void loop() {
  if (newSample) {
    noInterrupts();
    uint16_t value = latestSample;
    newSample = false;
    interrupts();

    // Print in CSV format with timestamp
    Serial.print(micros());  // Timestamp in microseconds
    Serial.print(",");
    Serial.println(value);
  }
}