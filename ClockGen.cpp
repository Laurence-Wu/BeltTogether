// =====================================================
// Clock Generation Implementation
// =====================================================
#include "ClockGen.h"

void setupClockPWM(uint8_t pin, float freq) {
  pinMode(pin, OUTPUT);
  const uint16_t prescaler = 8;  // prescaler = 8 → up to ~100 kHz clock
  uint16_t top = (16000000.0 / (2 * prescaler * freq)) - 1;

  TCCR4A = 0;
  TCCR4B = 0;
  TCNT4  = 0;

  TCCR4A |= (1 << COM4A0); // toggle OC4A (pin 6)
  TCCR4B |= (1 << WGM42);  // CTC mode
  TCCR4B |= (1 << CS41);   // prescaler 8
  OCR4A = top;
}
