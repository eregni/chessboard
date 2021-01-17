#include "Wire.h"
#include "an32183a.h"
#include "Arduino.h"

const long I2C_CLOCK = 1000000;

void AN32183A::begin(){
    pinMode(NRST, OUTPUT);
    digitalWrite(NRST, HIGH);
    delayMicroseconds(4000); // Start up the led drivers and wait >3 ms (datasheet P14)
    Wire.setClock(I2C_CLOCK);
    Wire.begin();
    reset_drivers();
    led_setup();
}

void AN32183A::test(){
    Wire.beginTransmission(LED0);
    Wire.write(DTA1);
    for (int i = 0; i < 81; i++){
        Wire.write(0xFF);
    }
    Wire.endTransmission();
}

int AN32183A::read(int reg){
    Wire.beginTransmission(LED0);
    Wire.write(reg);
    Wire.endTransmission();
    Wire.requestFrom((int)LED0, 1);
    Serial.println("Reading...");
    while (Wire.available() == 0);  // Wait for incoming data
    int incoming = Wire.read();
    return incoming;
}

// private
void AN32183A::reset_drivers(){
    for (int i = 0; i < sizeof(ADDRESS_LED); i++){
        Wire.beginTransmission(ADDRESS_LED[i]);
        Wire.write(RST);
        Wire.write(0x03);               //TODO: 'RAM reset' or 'Soft reset'
        Wire.endTransmission();
    }   
}

void AN32183A::led_setup(){
    for (int i = 0; i < sizeof(ADDRESS_LED); i++){
        // Wire.beginTransmission(ADDRESS_LED[i]);
        // Wire.write(POWERCNT);   
        // Wire.write(0x01);               //Internal oscilltor ON
        // Wire.endTransmission();

        // Wire.beginTransmission(ADDRESS_LED[i]);
        // Wire.write(OPTION);             // OPTIONS: ghost prevention OFF (TODO: test!), external melody off, 
        //                                 //internal clock output off, internal clock syncronos clock selected
        // Wire.write(0x00);               // THIS IS REDUNDANT SINCE 0 IS THE DEFAULT VALUE 
        // Wire.endTransmission();

        Wire.beginTransmission(ADDRESS_LED[i]);
        Wire.write(MTXON);              // Max current setup
        Wire.write(0x15);               // Matrix on + max current 22.5mA (Max = 60mA)
        Wire.endTransmission();

        // Wire.beginTransmission(ADDRESS_LED[i]);
        // Wire.write(PWMEN1);             // PWM mode setup
        // for (int j = 0; j < 11; j++){
        //     Wire.write(0xFF);               // All pwm enabled 
        // }
        // Wire.endTransmission();

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
}