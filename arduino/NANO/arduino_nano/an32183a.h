//Library for the an32183a led driver
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
const byte THOLD = 0x2B;        // Voltage threshold
const byte CONSTX6_1 = 0x2C;    // Constant current mode led 1 - 6
const byte CONSTX10_7 = 0x2D;   // Constant current mode led 7 - 10
const byte CONSTY6_1 = 0x2E;
const byte CONSTY9_7 = 0x2F;
const byte MASKY6_1 = 0x30;    
const byte MASKY9_7 = 0x31;
const byte SLPTIME = 0x32;      // Fade in-out settings
const byte SCANSET = 0x36;      // ???

const byte DTA1 = 0x40;         // Pwm duty control. The next registers are the same until 0x8F
// const byte DTB1 = 0x49;         
// const byte DTC1 = 0x52;         
// const byte DTD1 = 0x5B;
// const byte DTE1 = 0x64;
// const byte DTF1 = 0x6D;
// const byte DTG1 = 0x76;
// const byte DTH1 = 0x7F;

const byte LINE_A1 = 0x91;      // Luminece + fading setup. The next registers are the same until 0xE0
// const byte LINE_B1 = 0x9A;      
// const byte LINE_C1 = 0xA3;      
// const byte LINE_D1 = 0xAC;
// const byte LINE_E1 = 0xB5;
// const byte LINE_F1 = 0xBE;
// const byte LINE_G1 = 0xC7;
// const byte LINE_H1 = 0xD0;
// const byte LINE_I1 = 0xD9;

const byte NRST = A0;

class AN32183A {
    public:
      void begin();
      void squareOn(byte frame, byte square, byte red, byte green, byte blue, bool blink);
      void squareOff(byte frame, byte square);
      void test();
      
    private:
      int read(int reg);  // Read register
      int write(int reg);  // Write register
      void reset_drivers();
      void led_setup();

};

enum Color{ 
  RED,
  GREEN,
  BLUE
};