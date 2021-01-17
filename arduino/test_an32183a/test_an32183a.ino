#include "an32183a.h"

// config
byte nrst_pin = 2;
//

AN32183A leds = AN32183A();

void setup(){
    Serial.begin(115200);
    
    leds.begin(nrst_pin);
    Serial.println("Start");
    // leds.test();
    Serial.print("MTXON: ");
    Serial.println(leds.read(MTXON));
    Serial.print("PWMA1: ");
    Serial.println(leds.read(PWMEN1));
    Serial.println("driver test done!");
}

void loop(){
    //loop
}