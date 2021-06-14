#include "Wire.h"
#include "an32183a.h"
#include "Arduino.h"

const long I2C_CLOCK = 100000; // i2c "Fast mode"

void AN32183A::begin(byte nrst){
    Wire.setClock(I2C_CLOCK);
    Wire.begin();
    delayMicroseconds(5000); // Start up the led drivers and wait >4 ms (datasheet P14)
    pinMode(nrst, OUTPUT);
    digitalWrite(nrst, HIGH);
    reset_drivers();
}
  
void AN32183A::test(){
    Wire.beginTransmission(LED0);
    Wire.write(DTA1);
    for (int j = 0; j < 31; j++){
            Wire.write(0xFF);         
        }
    Wire.endTransmission();

    Wire.beginTransmission(LED0);
    Wire.write(DTA1);
    for (int j = 0; j < 31; j++){
            Wire.write(0xFF);         
        }
    Wire.endTransmission();

    Wire.beginTransmission(LED0);
    Wire.write(DTA1);
    for (int j = 0; j < 19; j++){
            Wire.write(0xFF);         
        }
    Wire.endTransmission();
    
    // Wire.beginTransmission(LED0);
    // Wire.write(DTA1);
    // Wire.endTransmission();
    // for (int i = 0; i < 81; i++){
    //     Serial.print("DT*");
    //     Serial.print(i + 1);
    //     Serial.print(":\t");
    //     Wire.requestFrom((int)LED0, 1);
    //     while (Wire.available() == 0);  // Wait for incoming data
    //     int incoming = Wire.read();
    //     Serial.println(incoming, BIN);
    // }
}

int AN32183A::read(int reg){
    Wire.beginTransmission(LED0);
    Wire.write(reg);
    Wire.endTransmission();
    
    Wire.requestFrom((int)LED0, 1);
    while (Wire.available() == 0);  // Wait for incoming data
    int incoming = Wire.read();
    return incoming;
}

// private
void AN32183A::reset_drivers(){
        Wire.beginTransmission(LED0);
        Wire.write(RST);
        Wire.write(0x02);               //RAM reset (Can't figure out what 'Soft reset' exactly does with the driver)
        Wire.endTransmission();
    // for (int i = 0; i < sizeof(ADDRESS_LED); i++){
    //     Wire.beginTransmission(ADDRESS_LED[i]);
    //     Wire.write(RST);
    //     Wire.write(0x02);               //RAM reset (Can't figure out what 'Soft reset' exactly does with the driver)
    //     Wire.endTransmission();
    // }   
}

void AN32183A::led_setup(){
      Wire.beginTransmission(LED0);
      Wire.write(MTXON);           
      Wire.write(0b00011111);               // Matrix on, max current Serial(= 60mA)
      Wire.endTransmission();

      Wire.beginTransmission(LED0);
      Wire.write(SCANSET);
      Wire.write(0b00001000);
      Wire.endTransmission();
      
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

      Wire.beginTransmission(LED0);  // Enable pwm for all leds
      Wire.write(PWMEN1);             // PWM mode setup
      for (int j = 0; j < 10; j++){
          Wire.write(0xFF);               //  pwm enabled 
      }
      Wire.write(0x01);               // The 11'th PWMEN register controls only 1 led
      Wire.endTransmission();

      
      Wire.beginTransmission(LED0);  // set pwm duty on led A1
      Wire.write(DTA1);
      for (int i=0; i<81; i++){
        Wire.write(0xFF);
      }
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
