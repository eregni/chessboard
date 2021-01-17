#include <SD.h>

/*
Test datalogging with i2c
*/
#include <SPI.h>

#include <Wire.h>
#include "RTClib.h"

#define RTC_ADDR 0x00 
#define SS_PIN 4
#define TEST_FILE "test.txt"

RTC_DS1307 rtc;

Sd2Card card;
SdVolume volume;
SdFile root;

void setup(){
    if (! rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1);
  }
    // rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    Serial.begin(115200);

    if (!card.init(SPI_FULL_SPEED, SS_PIN)){
        Serial.println("problem with sd card!");
    }
    else{
        Serial.println("Sd card ok");
    }

    // Now we will try to open the 'volume'/'partition' - it should be FAT16 or FAT32
    if (!volume.init(card)) {
        Serial.println("Could not find FAT16/FAT32 partition");
        while (1);
    }
    else {
        Serial.println("Fat Partion ok");
    }

    // RTC
    if (!rtc.isrunning()){
        Serial.println("RTC NOK!");
        while(1);
    }
    File dataFile = SD.open(TEST_FILE, FILE_WRITE);
    delay(1000);
    DateTime dt = rtc.now();
    dataFile.println(dt.dayOfTheWeek(), DEC); 
    dataFile.println(dt.minute(), DEC);
    dataFile.println(dt.second(), DEC);
    dataFile.println("lepel");
    dataFile.close();
    Serial.println(dt.hour(), DEC); 
    Serial.println(dt.minute(), DEC);
    Serial.println(dt.second(), DEC);
    Serial.println("lepel");
    delay(2000);

    File test = SD.open(TEST_FILE, FILE_READ);
    while (test.available()){
        Serial.println(test.read());
    }
    test.close();
}

void loop(){
}