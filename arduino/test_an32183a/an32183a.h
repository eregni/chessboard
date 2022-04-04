//Library for the an32183a led driver

//Important: the internal pull-up resistors  for the I2C (TWI) have to be turned off in the Wire library. 
// The chessboard pcb has 2 pull-ups (4.7Kohm) already 

#include <Arduino.h>

// i2c address -> datasheet p40
enum I2CAddress : uint8_t {
  I2CAddressLOW =   0b1011100,
  I2CAddressHIGH =  0b1011101,
  I2CAddressSCL =   0b1011110,
  I2CAddressSDA =   0b1011111,
};

enum Register : uint8_t {
  // Registers -> datasheet p15
  RST = 0x02,          // 'RAM' reset or 'soft reset' TODO can't understand what these resets are actually resetting
  POWERCNT = 0x02,     // Set internal oscilator
  OPTION = 0x04,       // Ghost Image Prevention, External Melody Input, Internal clock output, Internal/external synchronous clock
  MTXON = 0x05,        // Maximum led current
  PWMEN1 = 0x06,       // PWM enable PWMEN1 - PWMEN11 0x06 - 0x10
  MLDEN1 = 0x11,       // MLDEN1 - MLDEN11 0x11 - 0x1B
  MLDMODE1 = 0x2A,     
  THOLD = 0x2B,
  CONSTX6_1 = 0x2C,
  CONSTX10_7 = 0x2D,   // Constant current settings for matrix row X9 -> X7
  CONSTY6_1 = 0x2E,    // Constant current settings for matrix column Y6 -> Y1
  CONSTY9_7 = 0x2F,    // Constant current settings for matrix column Y6 -> Y1
  MASKY6_1 = 0x30,     // Constant current mask setting for matrix column X6 -> X1
  MASKY9_7 = 0x31,
  SLPTIME = 0x32,      // Fade in-out settings
  MLDCOM = 0x33,
  SCANSET = 0x36,      // ??? (Not used)
  DTA1 = 0x40,         // Pwm duty control. The next registers are the same until 0x90 (81 registers)
  LED_A1 = 0x91,       // Luminece + fading setup. The next registers are the same until 0xE1 (81 registers)
};

enum RegisterDefaults : uint8_t {
  RST_DEFAULT = 0x00,
  POWERCNT_DEFAULT = 0x00,
  OPTION_DEFAULT = 0x00,
  MTXON_DEFAULT = 0x1E,   // 11110 -> IMAX: 60mA, MTXON: 0
  PWMEN_DEFAULT = 0x00,
  MLDEN_DEFAULT = 0x00,
  MLDMODE1_DEFAULT = 0x00,
  THOLD_DEFAULT = 0x00,
  CONSTX6_1_DEFAULT = 0x00,
  CONSTX10_7_DEFAULT = 0x00,
  CONSTY6_1_DEFAULT = 0x00,
  CONSTY9_7_DEFAULT = 0x00,
  MASKY6_1_DEFAULT = 0x00,
  MASKY9_7_DEFAULT = 0x00,
  SLPTIME_DEFAULT = 0x00,
  MLDCOM_DEFAULT = 0x03,    // 11 -> MLDCOM: 5.8µs
  SCANSET_DEFAULT = 0x08,   // 1000 -> scanset: Scan all columns
  DT_DEFAULT = 0x00,
  LED_DEFAULT = 0x00
};

// Fucntions are ordered the same way as in the datasheet
class AN32183A {
  public:
      AN32183A(I2CAddress i2cAddress, uint8_t nrstPin);
      void begin(bool internalOscillator = true, bool ghostPrevention = false, bool melodyMode = false, bool clkOut = false, bool extClk = false, uint8_t maxLuminance = 8);
      void reset(bool ramrst = true, bool srst = true);
//      void test();
      uint8_t getRegister(Register reg);
      void led_setup();

    private:
      void setInternalOscillator(bool oscen);
      void setOptions(bool ghostPrevention, bool melodyMode, bool clkOut, bool extClk);
      void toggleMatrix(bool active);
      void setMaxLuminence(uint8_t imax);
      uint8_t readRegister(Register reg);
      void writeToRegister(Register reg, uint8_t value);
      void multiWriteToRegister(uint8_t reg, uint8_t value);
      
    private:
      
      I2CAddress _i2cAddress;
      uint8_t _nrstPin;
};

