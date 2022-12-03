#include <SPI.h>

// SPI: SS MOSI MISO SCK = 10 11 12 13
#define SPI_DATA_PIN 11
#define SPI_BACK_PIN 12
#define SPI_SCLK_PIN 13

#define DO_PIN SPI_BACK_PIN
#define CL_PIN SPI_SCLK_PIN
#define DI_PIN SPI_DATA_PIN
#define LD_PIN 9
#define FL_PIN 8

// Use timer interrupt to generate 64 Hz square wave for FL pin.
// TODO: HW PWM on an "analog" pin.
void setupTimer1() {
  // AVR Timer CTC Interrupts Calculator
  // v. 8
  // http://www.arduinoslovakia.eu/application/timer-calculator
  // Microcontroller: ATmega328P
  // Created: 2022-11-10T19:24:40.156Z
  noInterrupts();
  // Clear registers
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;

  // 128 Hz (16000000/((15624+1)*8))
  OCR1A = 15624;
  // CTC
  TCCR1B |= (1 << WGM12);
  // Prescaler 8
  TCCR1B |= (1 << CS11);
  // Output Compare Match A Interrupt Enable
  TIMSK1 |= (1 << OCIE1A);
  interrupts();
}

ISR(TIMER1_COMPA_vect) {
  digitalWrite(FL_PIN, digitalRead(FL_PIN) ^ 1);
}

inline void spi_wait_idle() {
  while (!(SPSR & _BV(SPIF)))
    ;
}

void latch() {
  spi_wait_idle();
  digitalWrite(LD_PIN, HIGH);
  // 'duino is slow enough so no explicit delay needed
  //delayMicroseconds(1);
  digitalWrite(LD_PIN, LOW);
}

void spi_transmit(byte data) {
  spi_wait_idle();
  SPDR = data;
}

// autodetected SPI loopback length
static int max_index;
// fallback to one screen if autodetection fails; it works, but flickers
#define FALLBACK_MAX 60
// timeout for autodetection (max 0x7fff/60 = 546)
// smaller timeout means faster boot if the HW doesn't have loopback set up
#define MAX_SCREENS 100

static int loopback_pattern(byte pattern) {
  for (int n = 0; n < MAX_SCREENS * 60; n++) {
    byte back = SPI.transfer(pattern);
    if (back == pattern) {
      return n;
    }
  }
  return FALLBACK_MAX;
}

void detect_size(void) {
  // each lcd size is a multiple of 8 bits
  // triple check with different bit patterns
  int n1 = loopback_pattern(0x55);
  int n2 = loopback_pattern(0x33);
  int n3 = loopback_pattern(0x0f);
  if (n1 == n2 && n1 == n3) {
    max_index = n1;
  } else {
    max_index = FALLBACK_MAX;
  }
}

void setup() {
  pinMode(DO_PIN, INPUT);
  pinMode(LD_PIN, OUTPUT);
  pinMode(CL_PIN, OUTPUT);
  pinMode(DI_PIN, OUTPUT);
  pinMode(FL_PIN, OUTPUT);
  digitalWrite(LD_PIN, LOW);
  setupTimer1();

  SPI.begin();
  // CPOL=0, CPHA=1 (clock normally low, data sampled at trailing edge)
  // 500 kHz rate not verified
  SPI.beginTransaction(SPISettings(500000, MSBFIRST, SPI_MODE1));

  detect_size();

  // mark the first SPIF for spi_wait_idle
  SPDR = 0;

  Serial.begin(115200);
  Serial.write((byte)max_index / 60);
  // faster uart seems to be glitchy
  // Serial.begin(230400);
}

static int index = 0;

void loop() {
  int incomingByte = Serial.read();
  if (incomingByte != -1) {
    Serial.write(index); // load-bearing print statement
    byte x = incomingByte;
    spi_transmit(x);
    index++;

    if (index == max_index) {
      index = 0;
      Serial.write('.');
      latch();
    }
  }
}
