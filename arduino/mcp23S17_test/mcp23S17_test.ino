#include <SPI.h>


#define  RESET_PIN 7
#define  INT_PIN 2

#define  IOCON 0x0A

#define  IODIRA 0x00
#define  IODIRB 0x01
#define  IPOLA 0x02
#define  IPOLB 0x03
#define  GPINTENA 0x04
#define  GPINTENB 0x05
#define  DEFVALA 0x06
#define  DEFVALB 0x07
#define  INTCONA 0x08
#define  INTCONB 0x09
#define  GPPUA 0x0C
#define  GPPUB 0x0D
#define  INTFA 0x0E
#define  INTFB 0x0F
#define  INTCAPA 0x10
#define  INTCAPB 0x11
#define  GPIOA 0x12
#define  GPIOB 0x13
#define  OLATA 0x14
#define  OLATB 0x15

const SPISettings settings(8000000, MSBFIRST, SPI_MODE0);
const byte SPIRead = 0x41;
const byte SPIWrite = 0x40;
const byte slaveSelect = 10;
const byte debounceTime = 150;

int counter = 0;
volatile bool intFlag = false;
bool ledState = true;
unsigned long debounceTimeStamp;

void spiWrite(int reg, int value){
    SPI.beginTransaction(settings);
    digitalWrite(slaveSelect,LOW);
    SPI.transfer(SPIWrite);
    SPI.transfer(reg);
    SPI.transfer(value);
    digitalWrite(slaveSelect, HIGH);
    SPI.endTransaction();
}

int spiRead(int reg){
    SPI.beginTransaction(settings);
    digitalWrite(slaveSelect,LOW);
    SPI.transfer(SPIRead);
    SPI.transfer(reg);
    int value = SPI.transfer(0);
    digitalWrite(slaveSelect, HIGH);
    return value;
}

void isr(){
    intFlag = true;
    Serial.write("ping");
}

void MCP23017Setup(){
    // digitalWrite(RESET_PIN, LOW);
    // delay(2);
    // digitalWrite(RESET_PIN, HIGH);
    spiWrite(IOCON, 0x28);

    spiWrite(IODIRB, 0x00);
    spiWrite(IODIRA, 0x40);
    spiWrite(GPPUA, 0x40);
    spiWrite(DEFVALA, 0x40);
    spiWrite(GPINTENA, 0x40);
    spiWrite(INTCONA, 0x40);

    spiRead(INTCAPA);
    spiRead(INTCAPB);  
}

void setup(){
    SPI.begin();
    pinMode(slaveSelect, OUTPUT);
    digitalWrite(slaveSelect, HIGH);
    MCP23017Setup();

    Serial.begin(115200);
    pinMode(13, OUTPUT);
    pinMode(RESET_PIN, OUTPUT);
    pinMode(INT_PIN, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(INT_PIN), isr, FALLING);
    spiWrite(GPIOB, 0x02);

    Serial.println("Start");
}

void loop(){
    while (Serial.available() > 0){
        int value;
        char input = Serial.read();
        switch (input){
            case 'H':
                Serial.println("BOE");
                break;
            case 'S':
                Serial.print("State intpin: ");
                Serial.println(digitalRead(INT_PIN)); // read state of interrupt pin
                break;
            case 'C':
                value = spiRead(INTCAPA);
                Serial.print("INTCAPA: 0b");
                Serial.println(value, BIN);
                break;
            case 'G':
                value = spiRead(GPIOA);
                Serial.print("GPIOA: 0b");
                Serial.println(value, BIN);
                break;
            case 'g':
                value = spiRead(GPIOB);
                Serial.print("GPIOB: 0b");
                Serial.println(value, BIN);
                break;
            case 'F':
                value = spiRead(INTFA);
                Serial.print("INTFA: 0b");
                Serial.println(value, BIN);
                break;
            case 'R':
                Serial.println("Reset\n");
                counter = 0;
                detachInterrupt(digitalPinToInterrupt(2));
                MCP23017Setup();
                attachInterrupt(digitalPinToInterrupt(2), isr, FALLING);
                break;
            case 'I':
                Serial.println("Manual interrupt!");
                intFlag = true;
                break;
            case 'c':
                Serial.print("IOCON: 0x");
                value = spiRead(IOCON);
                Serial.println(value, HEX);
                break;
            case 'V':
                Serial.print("DEFVALA: 0b");
                value = spiRead(DEFVALA);
                Serial.println(value, BIN);
                break;
            case 'D':
                Serial.print("IODIRA: 0b");
                value = spiRead(IODIRA);
                Serial.println(value, BIN);
                break;
        }
    }

    if (intFlag){
        debounceTimeStamp = millis();
        detachInterrupt(digitalPinToInterrupt(2));
        spiWrite(GPINTENA, 0x00);
        counter++;
        ledState = !ledState;
        ledState ? spiWrite(GPIOB, 0x02) : spiWrite(GPIOB, 0x00);
        Serial.print("MCP23017 GPIOA: ");
        byte value = spiRead(GPIOA);
        Serial.println(value, BIN);
        intFlag = false;
        Serial.print("Int count: ");
        Serial.println(counter);
    }

    if ((millis() - debounceTimeStamp > debounceTime) && (spiRead(GPIOA) == 0x40)){
        spiWrite(GPINTENA, 0x40);
        attachInterrupt(digitalPinToInterrupt(2), isr, FALLING);
    }
}