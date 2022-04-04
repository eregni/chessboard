#include <an32183a.h>

  AN32183A leds(I2CAddressLOW, 2);

void setup() {
  leds.begin();
  Serial.begin(115200);
  Serial.println("--------------------------");
  
  checkRegister("POWERCNT", POWERCNT, 0x00);
  checkRegister("OPTION", OPTION, 0x00);
  checkRegister("MTXON", MTXON, 0x1E);
  checkRegisterArray("PWMEN", PWMEN1, 11, 0x00);
  checkRegisterArray("MLDEN", MLDEN1, 11, 0x00);
  checkRegister("MLDMODE1", MLDMODE1, 0x00);
  checkRegister("THOLD", THOLD, 0x00);
  checkRegister("CONSTX6_1", CONSTX6_1, 0x00);
  checkRegister("CONSTX10_7", CONSTX10_7, 0x00);
  checkRegister("CONSTY6_1", CONSTY6_1, 0x00);
  checkRegister("CONSTY9_7", CONSTY9_7, 0x00);
  checkRegister("MASKY6_1", MASKY6_1, 0x00);
  checkRegister("MASKY9_7", MASKY9_7, 0x00);
  checkRegister("SLPTIME", SLPTIME, 0x00);
  checkRegister("MLDCOM", MLDCOM, 0x03);
  checkRegister("SCANSET", SCANSET, 0x08);
  checkRegisterArray("DT", DTA1, 81, 0x00);
  checkRegisterArray("LED", LED_A1, 81, 0x00);

  Serial.println("--------------------------");
}

void loop() {
  // put your main code here, to run repeatedly:

}

// Functions
void checkRegisterArray(String name, int startAddress, int arraySize, int defaultValue){
    for (int i = 0; i < arraySize; i++){
    checkRegister(name + (i + 1), startAddress + i, defaultValue);
  }
}

void checkRegister(String name, int address, int defValue){
  int readValue = leds.read(address);
  String result;
  defValue - readValue == 0 ? result = "OK" : result = "NOK";

  Serial.print(name);
  Serial.print(", address: h");
  Serial.print(address, HEX);
  Serial.print(", default value: b");
  Serial.print(defValue, BIN);
  Serial.print(", read value: b");
  Serial.print(readValue, BIN);
  Serial.print(",\t Check: ");
  Serial.println(result);
}
