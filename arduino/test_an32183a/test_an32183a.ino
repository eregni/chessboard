#include "an32183a.h"

// config
byte nrstPin = 2;
//

AN32183A leds(I2CAddressLOW, nrstPin);

void setup(){
  
    Serial.begin(115200);
    leds.begin();
//    Serial.println("----- Start -----");
//    // leds.test();
//    Serial.print("POWERCNT: ");
//    Serial.println(leds.getRegister(POWERCNT), BIN);
//    Serial.print("MTXON: ");
//    Serial.println(leds.getRegister(MTXON), BIN);
//    Serial.print("PWMEN1: ");
//    Serial.println(leds.getRegister(PWMEN1), BIN);
//    Serial.print("DTA1: ");
//    Serial.println(leds.getRegister(DTA1), BIN);
//    
//    Serial.println("Led init");
    leds.led_setup();
//    Serial.print("POWERCNT: ");
//    Serial.println(leds.getRegister(POWERCNT), BIN);
//    Serial.print("MTXON: ");
//    Serial.println(leds.getRegister(MTXON), BIN);
//    Serial.print("PWMEN1: ");
//    Serial.println(leds.getRegister(PWMEN1), BIN);
//    Serial.print("DTA1: ");
//    Serial.println(leds.getRegister(DTA1), BIN);
}

void loop(){
    //loop
}
