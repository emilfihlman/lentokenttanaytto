// directions as seen by the LCD
#define LD_PIN 11
#define CL_PIN 10
#define DI_PIN 9 // LCD data input
#define FL_PIN 8
#define DISPLAY_BITS 480
#define DISPLAY_BYTES DISPLAY_BITS/8

// Use timer interrupt to generate 64 Hz square wave for FL pin.
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

void shiftBit(int b) {
  digitalWrite(CL_PIN, HIGH);
  //delayMicroseconds(1);
  if (b) {
    digitalWrite(DI_PIN, HIGH);
  } else {
    digitalWrite(DI_PIN, LOW);
  }
  //delayMicroseconds(1);
  digitalWrite(CL_PIN, LOW);
  //delayMicroseconds(1);
}

void latch() {
  digitalWrite(LD_PIN, HIGH);
  delayMicroseconds(100);
  digitalWrite(LD_PIN, LOW);
}

void clear() {
  // clear out existing values
  for (int i = 0; i < DISPLAY_BITS; i++) {
    shiftBit(0);
  }
  latch();
}

void setup() {
  pinMode(LD_PIN, OUTPUT);
  pinMode(CL_PIN, OUTPUT);
  pinMode(DI_PIN, OUTPUT);
  pinMode(FL_PIN, OUTPUT);
  digitalWrite(LD_PIN, LOW);
  setupTimer1();

  Serial.begin(115200);
  // Serial.begin(230400);

  clear();
}

int index = 0;

void loop() {
  int incomingByte = Serial.read();
  if (incomingByte != -1) {
    Serial.write(index); // load-bearing print statement
    byte compress = 1;
    if (compress) {
      byte x = incomingByte;
      for (byte c = 0; c < 8; c++) {
        shiftBit((x & 0x80) != 0);
        x <<= 1;
      }
      index += 8;
    } else {
      shiftBit(incomingByte != 0);
      index++;
    }
    if (index == 480) {
      latch();
      Serial.write('.');
      index = 0;
    }
  }
}
