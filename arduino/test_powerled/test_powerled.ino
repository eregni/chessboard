const byte powerLedPin = 6;
const long SERIAL_BAUDRATE = 115200;
const char START_CHAR = '<';
const char STOP_CHAR = '>';
const char SPLIT_CHAR = '\t';
bool bootOk = false;

void setup(){
    pinMode(powerLedPin, OUTPUT);
    Serial.begin(115200);
}

void loop(){
    if (bootOk != true){
        onBoot();
    }
    // Empty
}

// *** Power ***//
void onBoot(){
  // Perform tasks only necessary during boot of the rpi zero. Wait for an 'H' message.
  while (bootOk != true){
    fade_in_analog(powerLedPin);
    wait(50);
    fade_out_analog(powerLedPin);
    wait(50);
    delayMicroseconds(2000);
    if (Serial.available() > 0){
      checkSerial();
    }
  }
}

// *** POWER LED *** //
void wait(int time){
    unsigned long timestamp = millis();
    while (millis() - timestamp < time);
}

void fade_in_analog(int ledPin){
  byte brightness = 0;
  byte step = 2;
  for (byte brightness = 2; brightness <= 64; brightness += step){
      analogWrite(ledPin, brightness);
      wait(30);
  }
}

void fade_out_analog(int ledPin){
  byte brightness = 255;
  byte step = 2;
  for (byte brightness = 64; brightness >= 2; brightness -= step){
      analogWrite(ledPin, brightness);
      wait(30);
  }
}

// *** Serial ***//
void checkSerial() { 
  //Handler for incoming serial data. Read incoming message and execute according functions
  if (Serial.read() == START_CHAR){
    char in = Serial.read();
    // if (Serial.available() > 0){
    //   Serial.read();
    // }
    // MESSAGES
    // H --> say 'hello'
    if (in == 'H'){
        Serial.write(START_CHAR);
        Serial.write("hello");
        Serial.write(STOP_CHAR);
        bootOk = true;
    }
    // Clear buffer
    Serial.flush();
    in = 0;
  }
}