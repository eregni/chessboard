#include <Wire.h>

#define  RESET_PIN 7
#define  INT_PIN 2
#define  ADDR 0x20

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

volatile int counter = 0;
volatile bool intFlag = false;
volatile bool ledState = false;
volatile int btnState = 0;

void i2cSend(int reg, int value){
    Wire.beginTransmission(ADDR);
    Wire.write(byte(reg));
    Wire.write(byte(value));
    Wire.endTransmission();
}

int i2cRead(int reg){
    Wire.beginTransmission(ADDR);
    Wire.write(byte(reg));
    Wire.endTransmission();
    Wire.requestFrom(ADDR, 1);
    int value = Wire.read();
    while (Wire.available()){
        Serial.println(Wire.read());
    }
    return value;
}

void ping(){
    intFlag = true; 
    counter++;
    cli();
    detachInterrupt(digitalPinToInterrupt(INT_PIN));
    sei();
    ledState = !ledState;
    if (ledState){
        i2cSend(GPIOB, 0x80);
    }
    else{
        i2cSend(GPIOB, 0x00);
    }
    btnState = i2cRead(INTCAPA);
}

void MCP23017Setup(){
    digitalWrite(RESET_PIN, LOW);
    delay(2);
    digitalWrite(RESET_PIN, HIGH);
    i2cSend(IOCON, 0x24);
    i2cSend(IODIRB, 0x00);
    i2cSend(IODIRA, 0xFF);
    i2cSend(GPPUA, 0xFF);
    i2cSend(GPINTENA, 0xFF);
    i2cSend(DEFVALA, 0xFF);
    i2cSend(INTCONA, 0xFF);

    i2cRead(INTCAPA);
    i2cRead(INTCAPB);
}

void setup(){
    Serial.begin(115200);
    pinMode(13, OUTPUT);
    pinMode(RESET_PIN, OUTPUT);
    pinMode(INT_PIN, INPUT_PULLUP);
    Wire.begin();
    // Wire.setClock(1700000);
    MCP23017Setup();
    cli();
    attachInterrupt(digitalPinToInterrupt(INT_PIN), ping, FALLING);
    sei();
    Serial.println("Start");
}

void loop(){
    delayMicroseconds(300);
    while (Serial.available() > 0){
        int value;
        char input = Serial.read();
        switch (input){
            case 'H':
                Serial.println("BOE");
                break;
            case 'S':
                Serial.print("State interrupt pin: ");
                Serial.println(digitalRead(INT_PIN)); // read state of interrupt pin
                break;
            case 'C':
                value = i2cRead(INTCAPA);
                Serial.println(value);
                break;
            case 'G':
                value = i2cRead(GPIOA);
                Serial.println(value);
                break;
            case 'F':
                value = i2cRead(INTFA);
                Serial.println(value);
                break;
            case 'R':
                Serial.println("Reset");
                MCP23017Setup();
            case 'I':
                Serial.println("Manual interrupt!");
                i2cSend(GPINTENA, 0x00);
                i2cSend(IODIRA, 0x00);
                i2cSend(GPIOA, 0x40);
                i2cSend(GPIOA, 0x00);
                i2cSend(IODIRA, 0xFF);
                i2cSend(GPINTENA, 0x40);
        }
    }

    if (intFlag){
    //     cli();
    //     detachInterrupt(digitalPinToInterrupt(INT_PIN));
    //     sei();
    //     ledState = !ledState;
    //     Serial.print("Led state: ");
    //     Serial.println(ledState);
    //     Serial.print("int flag");
    //     Serial.println(intFlag);
    //     if (ledState){
    //         i2cSend(GPIOB, 0x80); 
    //     }
    //     else{
    //         i2cSend(GPIOB, 0x00);
    //     }
        Serial.print("MCP23017 GPIOA: ");
        Serial.println(btnState);
        intFlag = false;

    //     int value = i2cRead(INTCAPA);
    //     Serial.println(value);
    //     intFlag = false;
    //     Serial.print("Int count: ");
    //     Serial.println(counter);
    }
}