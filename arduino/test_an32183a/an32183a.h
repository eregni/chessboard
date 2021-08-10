//Library for the an32183a led driver

//Important: the internal pull-up resistors  for the I2C (TWI) have to be turned off in the Wire library. 
// The chessboard pcb has 2 pull-ups (4.7Kohm) already 
#include <Arduino.h>

//Adress
const byte LED0 = 0x5C;         //right led driver on pcb
const byte LED1 = 0x5D;         //middle led driver on pcb
const byte LED2 = 0x5F;         //left led driver on pcb
const byte ADDRESS_LED[3] = {LED0, LED1, LED2};

// Registers    
const byte RST = 0x01;          // 'RAM' reset or 'soft reset'
const byte POWERCNT = 0x02;     // Set internal oscilator
const byte OPTION = 0x04;       // Ghost Image Prevention, External Melody Input, Internal clock output, Internal/external synchronous clock
const byte MTXON = 0x05;        // Maximum led current
const byte PWMEN1 = 0x06;       // PWM enable PWMEN1 - PWMEN11 0x06 - 0x10
const byte CONSTX6_1 = 0x2C;    // Constant current settings for matrix row X6 -> X1
const byte CONSTX10_7 = 0x2D;   // Constant current settings for matrix row X9 -> X7
const byte CONSTY6_1 = 0x2E;    // Constant current settings for matrix column Y6 -> Y1
const byte CONSTY9_7 = 0x2F;    // Constant current settings for matrix column Y6 -> Y1
const byte MASKY6_1 = 0x30;     // Constant current mask setting for matrix column X6 -> X1
const byte MASKY9_7 = 0x31;
const byte SLPTIME = 0x32;      // Fade in-out settings
const byte SCANSET = 0x36;      // ??? (Not used)
const byte DTA1 = 0x40;         // Pwm duty control. The next registers are the same until 0x90 (81 registers)
const byte LED_A1 = 0x91;       // Luminece + fading setup. The next registers are the same until 0xE1 (81 registers)
 

class AN32183A {
    public:
      void begin(byte nrstPin);
      void squareOn(byte frame, byte square, byte red, byte green, byte blue, bool blink);
      void squareOff(byte frame, byte square);
      void test();
      int read(int reg);  // Read register
      void reset_drivers();
      void led_setup();

};

enum Color{ 
  RED,
  GREEN,
  BLUE
};
