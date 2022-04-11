#include "an32183a.h"

// config
byte nrstPin = 2;
//
ChipSettings settings;
AN32183A leds(I2CAddressLOW, nrstPin);

void setup(){
    Serial.begin(115200);
    settings.pwmMode = false;
    settings.scanset = 8;
    settings.slpTimeSettings.slowFadeout = true;
    settings.slpTimeSettings.ledOnExtend = 1;
    leds.begin(settings);
    Serial.println("----- Start -----");
    Serial.print("SLPTIME: ");
    Serial.println(leds.getRegister(SLPTIME), BIN);
    Serial.print("POWERCNT: ");
    Serial.println(leds.getRegister(POWERCNT), BIN);
    Serial.print("MTXON: ");
    Serial.println(leds.getRegister(MTXON), BIN);
    Serial.print("PWMEN1: ");
    Serial.println(leds.getRegister(PWMEN1), BIN);
    Serial.print("DTA1: ");
    Serial.println(leds.getRegister(DTA1), BIN);

    leds.setLedFadeTime(LED_A1, 1);
    leds.setLedLuminance(LED_A1, 15);

    Serial.print("LED_A1: ");
    Serial.println(leds.getRegister(LED_A1), BIN);
    Serial.print("DTA1: ");
    Serial.println(leds.getRegister(DTA1), BIN);
}

void loop(){
  // test with pwm mode
//    leds.setPwmDuty(0, 255);
//    Serial.print("DTA1: ");
//    Serial.println(leds.getRegister(DTA1), BIN);
//    delay(1000);
//    leds.setPwmDuty(0, 31);
//    Serial.print("DTA1: ");
//    Serial.println(leds.getRegister(DTA1), BIN);
//    delay(1000);
}
