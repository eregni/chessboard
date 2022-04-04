#include <Wire.h>
#include <Arduino.h>
#include "an32183a.h"


const long I2C_CLOCK = 100000; // i2c "Fast mode"


AN32183A::AN32183A(I2CAddress i2cAddress, uint8_t nrstPin)
{
    _i2cAddress = i2cAddress;
    _nrstPin = nrstPin;
}

/*
Flow:
RST: do full reset (???)
POWERCNT: set to internal oscillator
OPTION: set options
MTXON -> MTXON: activate matrix
MXTON -> IMAX: set led max luminence
*/
void AN32183A::begin(bool internalOscillator, bool ghostPrevention, bool melodyMode, bool clkOut, bool extClk, uint8_t maxLuminance){
    if (maxLuminance > 8) maxLuminance = 8;  // -> datasheet p23 
    //Wire.setClock(I2C_CLOCK);
    Wire.begin();
    pinMode(_nrstPin, OUTPUT);
    digitalWrite(_nrstPin, HIGH);
    delayMicroseconds(5000); // Start up led driver and wait >4 ms (datasheet P14)
    reset();
    setInternalOscillator(internalOscillator);
    setOptions(ghostPrevention, melodyMode, clkOut, extClk);
    toggleMatrix(true);
    setMaxLuminence(7);
}

// void AN32183A::test(){
//     Wire.beginTransmission(_i2cAddress);
//     Wire.write(DTA1);
//     for (int j = 0; j < 31; j++){
//             Wire.write(0xFF);         
//         }
//     Wire.endTransmission();

//     Wire.beginTransmission(_i2cAddress);
//     Wire.write(DTA1);
//     for (int j = 0; j < 31; j++){
//             Wire.write(0xFF);         
//         }
//     Wire.endTransmission();

//     Wire.beginTransmission(_i2cAddress);
//     Wire.write(DTA1);
//     for (int j = 0; j < 19; j++){
//             Wire.write(0xFF);         
//         }
//     Wire.endTransmission();
// }

// Full reset resets all registers. RAMRST only resets the pwm duty and led intensity settings. (datasheet -> p 22) 
void AN32183A::reset(bool ramrst, bool srst){
    uint8_t value = RST_DEFAULT || (ramrst << 1);
    value |= srst;
    writeToRegister(RST, value);  
}

void AN32183A::led_setup(){
    
      Wire.beginTransmission(_i2cAddress);
      Wire.write(MTXON);           
      Wire.write(0b00011111);               // Matrix on, max current Serial(= 60mA)
      Wire.endTransmission();

      Wire.beginTransmission(_i2cAddress);  // Turn on internal oscillator
      Wire.write(POWERCNT);           
      Wire.write(0x01);               
      Wire.endTransmission();

//      Wire.beginTransmission(LED0);
//      Wire.write(SCANSET);
//      Wire.write(0b00001000);
//      Wire.endTransmission();
      
      // Wire.beginTransmission(ADDRESS_LED[i]);
      // Wire.write(CONSTY6_1);      
      // Wire.write(0x3F);              
      // Wire.endTransmission();

      // Wire.beginTransmission(ADDRESS_LED[i]);
      // Wire.write(CONSTY9_7);          
      // Wire.write(0x07);           
      // Wire.endTransmission();

      // Wire.beginTransmission(ADDRESS_LED[i]);
      // Wire.write(CONSTX6_1);          
      // Wire.write(0x07);           
      // Wire.endTransmission();

      // Wire.beginTransmission(ADDRESS_LED[i]);
      // Wire.write(CONSTX10_7);          
      // Wire.write(0x0F);           
      // Wire.endTransmission();

      Wire.beginTransmission(_i2cAddress);
      Wire.write(LED_A1);
      Wire.write(0b11110000);
    //   for (int i=0; i<81; i++){
    //     Wire.write(0b11110000);
    //   }

      Wire.endTransmission();
      Wire.beginTransmission(_i2cAddress);  // Enable pwm for all leds
      Wire.write(PWMEN1);             // PWM mode setup
      Wire.write(0b00000001);
    //   for (int j = 0; j < 10; j++){
    //       Wire.write(0xFF);               //  pwm enabled 
    //   }
      Wire.write(0x01);               // The 11'th PWMEN register controls only 1 led
      Wire.endTransmission();

      Wire.beginTransmission(_i2cAddress);  // set pwm duty on led A1
      Wire.write(DTA1);
      Wire.write(0xFF);
    //   for (int i=0; i<80; i++){
    //     Wire.write(0xFF);
    //   }
      Wire.endTransmission();
      

      // Wire.beginTransmission(ADDRESS_LED[i]);
      // Wire.write(SLPTIME);            // Fade time setup
      // Wire.write(0x00);                // TODO: choose...
      // Wire.endTransmission();

      // Wire.beginTransmission(ADDRESS_LED[i]);
      // Wire.write(LINE_A1);   // PWM fade in/out operation
      // for (int j = 0; j < 81; j++){  // A1 - I8
      //     Wire.write(0x07);       // = ~23ms between each pwm step
      // }
      // Wire.endTransmission();
}

uint8_t AN32183A::getRegister(Register reg){
    return readRegister(reg);
}

// Private
void AN32183A::setInternalOscillator(bool oscen){
    writeToRegister(POWERCNT, oscen);
}

void AN32183A::setOptions(bool zpden, bool mldact, bool clkout, bool extclk){
    uint8_t value = zpden << 3 | mldact << 2 | clkout << 1 | extclk;
    writeToRegister(OPTION, value);
}

void AN32183A::toggleMatrix(bool active){
    uint8_t value = readRegister(MTXON);
    active ? value |= 1 : value &= 0b00011110;
    writeToRegister(MTXON, value);
}

// Todo test!
void AN32183A::setMaxLuminence(uint8_t imax){
    if (imax > 7) imax = 7;
    uint8_t bitsOn = imax << 1;
    uint8_t bitsOff = imax << 1 | 0b11110001;  // OR with bitmask: set bits to be ignored to 1
    uint8_t value = readRegister(MTXON);
    value | bitsOn;
    value & bitsOff;
    writeToRegister(MTXON, value);
}

uint8_t AN32183A::readRegister(Register reg){
    Wire.beginTransmission(_i2cAddress);
    Wire.write(reg);
    Wire.endTransmission();
    
    Wire.requestFrom((int)_i2cAddress, 1);
    while (Wire.available() == 0);  // Wait for incoming data
    int incoming = Wire.read();
    return incoming;
}

void AN32183A::writeToRegister(Register reg, uint8_t value){
     Wire.beginTransmission(_i2cAddress);
     Wire.write(reg);
     Wire.write(value);
     Wire.endTransmission();
}

void AN32183A::multiWriteToRegister(uint8_t reg, uint8_t value){
// TODO
}

