const byte voltPin = A0;
const byte shutdownIntPin = 2;
const float warning = 3.6;
const char LOW_VOLT = 'L';
const byte interval = 60; //seconds
long timeStamp = millis();
char powerButton = '0';


void powerButtonInt(){
    powerButton = true;
}


void pulseShutdownInt(){
    digitalWrite(shutdownIntPin, LOW);
    delayMicroseconds(20);
    digitalWrite(shutdownIntPin, HIGH);
}


void setup(){
    pinMode(voltPin, INPUT);
    Serial.begin(115200);
    attachInterrupt(digitalPinToInterrupt(2), powerButtonInt, FALLING);
}


// The first situation should be: User pressed the power button to shut down
// The second situation should be: the coulomb counter reaches his minimum
// The third, 'backup', situation is triggered when the voltage is too low.
void loop(){
    while (millis() - timeStamp < interval);

    int voltage = map(analogRead(voltPin), 0, 1023, 0, 5);
    Serial.println(voltage);
    if powerButton{
        Serial.println("Power button pressed");
        powerButton = 'P';
        pulseShutdownInt();
    }

    // If coulomb < minimum...
    if (voltage <= warning){
        Serial.println("Volt below minimum!");
        powerButton = 'L';
        pulseShutdownInt();
    }

    delayMicroseconds(2000);

    if (Serial.available() > 0){
        char in = Serial.read();
        // rpi asks: why shutdown?
        if (in == 'D'){  
            Serial.write(powerButton); // arduino answers: reason is power button pressed/batt empty/low voltage -
                                            // -> rpi shows info on epaper and and starts the shutdown (after confirmation from user if neccessary)
        }
    }
}