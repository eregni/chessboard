- Assing commands to led squares:
  ON
  OFF
  FADE IN
  FADE OUT
  SET SPEED FADING

/*
    Basic Pin setup:
    ------------                                  ---u----
    ARDUINO   13|-> SCLK (pin 25)           OUT1 |1     28| OUT channel 0
              12|                           OUT2 |2     27|-> GND (VPRG)
              11|-> SIN (pin 26)            OUT3 |3     26|-> SIN (pin 11)
              10|-> BLANK (pin 23)          OUT4 |4     25|-> SCLK (pin 13)
               9|-> XLAT (pin 24)             .  |5     24|-> XLAT (pin 9)
               8|                             .  |6     23|-> BLANK (pin 10)
               7|                             .  |7     22|-> GND
               6|                             .  |8     21|-> VCC (+5V)
               5|                             .  |9     20|-> 2K Resistor -> GND
               4|                             .  |10    19|-> +5V (DCPRG)
               3|-> GSCLK (pin 18)            .  |11    18|-> GSCLK (pin 3)
               2|                             .  |12    17|-> SOUT
               1|                             .  |13    16|-> XERR
               0|                           OUT14|14    15| OUT channel 15
    ------------                                  --------
*/

/*
    Fades a line down the channels, with max value and duration based on
    the voltage of analog pin 0.
    Try grounding analog 0: everything should turn off.
    Try putting +5V into analog 0: everything should turn on.

    See the BasicUse example for hardware setup.

    Alex Leone <acleone ~AT~ gmail.com>, 2009-02-03 */
// TODO look at instructables for 'STATE MACHINE'
#include "Tlc5940.h"
#include "tlc_fades.h"

TLC_CHANNEL_TYPE channel;
bool ledsOn = false;
long stamp;
bool buttonPressed = false;
unsigned int leds[] = {511, 0, 0, 0, 0, 0, 0, 0, 0};
bool fade = true;
int fadeTime = 2000;
int brightness = 511;
int ledRow = 0;

void ledButton(){
    if (millis() - stamp < 200){
      // Serial.println("debats");
    }
    else{
      // buttonPressed = true;
      ledsOn = !ledsOn;
      if (ledsOn){
        Serial.println("*** ON ***");
      }
      else{
        Serial.println("*** OFF ***");
      }
      stamp = millis();
    }  
}

void updateLeds(){
  noInterrupts();  //remove this eventually???
  // ledsOn = !ledsOn;
  // while (ledsOn){
   
  for (int i = 0; i < 9 * 9; i++){
      int led = leds[ledRow] >> i;
      Tlc.set(i * ledRow, brightness);
    // }
    // leds[5] = 0x10;
    // leds[6] = 0x04; // --> update led array with data from raspberry pi
  }
    // Tlc.update();
    // for (int i = 0; i < 9; i++){
    //   leds[i] = 0;
    // }
  ledRow++;
  // buttonPressed = false;
  interrupts();
}

/// SETUP ///
void setup(){
  Tlc.init();
  Serial.begin(115200);
  pinMode(2, INPUT);
  attachInterrupt(0, ledButton, RISING);
  Serial.println("Start!");
}

/// LOOP ///
void loop()
{
  // if (ledsOn){  //if leds are active
  //       // executeLedCyle();
  //       updateLeds();
  //     }

  if (ledsOn){  // will be replaced by int: triggered by serial message from raspberry pi
    updateLeds();

  }
    Tlc.update();
    Tlc.clear();
    delay(3);

  // if reed switch etc...
}



// OLD CODE 26/9/18


// void executeLedCyle(){
//   // if (fade){
//   //   executeFadeCycle();  //DEBUG
//   //   fade = false;
//   // }
//   fading();

//   Serial.println("\nExecute led cycle");
//   for (int i = 0; i < 9; i++){
//     Serial.print("Led array nr: ");
//     Serial.println(i);
//     Serial.print("Value: ");
//     Serial.println(leds[i]);
//     bool update = false;

//     if (leds[i] != 0){  // if ,at least, on of the leds was on
//       update = true;
//       unsigned int mask = 1;
//       for (int y = 1; y < 15; y++){
//         if (leds[i] >> y - 1 & mask != 0){
//           Tlc.set(y, brightness);
//         }    
//       }
//     }

//     if (update){
//       Serial.println("*** Tlc update ***");
//       Tlc.update();
//       update = false;
//     }
//     // pulse clk pin 4017
//   }
// }

// void fading(){
//   unsigned int mask = 1;
//   int brightness = 0;
//   unsigned int brightness_difference = 1023;  //DEBUG
//   int steps = round(brightness_difference / (fadeTime / brightness_difference));
//   Serial.println(steps);


//   while (steps > 0){
//     Serial.print("Step ");
//     Serial.print(steps);
//     Serial.print(" of ");
//     Serial.println((int)fadeTime / 3);

//     for (int i = 0; i < 9; i++){
//       Serial.print("Led array nr: ");
//       Serial.println(i);
//       Serial.print("Value: ");
//       Serial.println(leds[i]);
//       bool update = false;

//       if (leds[i] != 0){  // if ,at least, on of the leds has on
//         Serial.print("current brightness = ");
//         Serial.println(brightness);
//         update = true;
//         for (int y = 1; y < 15; y++){
//           if (leds[i] >> y - 1 & mask != 0){
//             Tlc.set(y, brightness);
//           }    
//         }
//       }

//       if (update){
//         Serial.println("*** Tlc update fades with tlc.update()***");
//         Tlc.update();
//         update = false;
//       }

   
//     // pulse clk pin 4017
//     }
//     brightness += 3;
//  ledsOn = !ledsOn;
//  ledsOn = !ledsOn;
// }ledsOn = !ledsOn;

// void executeFadeCycle(){
//   float fading = fadeTime / 3;  //DEBUG 667 4017 cycles each 3ms
//   unsigned int mask = 1;
//   int brightness = 0;

//   for (int i = 0; i < fading; i++){
//     Serial.println("\nExecute fade cycle");
//     int startTime = millis();

//     for (int i = 0; i < 9; i++){
//       Serial.print("Led array nr: ");
//       Serial.println(i);
//       Serial.print("Value: ");
//       Serial.println(leds[i]);
//       bool update = false;

//       if (leds[i] != 0){  // if ,at least, on of the leds has on
//         update = true;
//         for (int y = 1; y < 15; y++){
//           if (leds[i] >> y - 1 & mask != 0){
//             tlc_addFade(y, brightness, brightness + 3, startTime, startTime + 3);
//             Serial.print("Fade time = ");
//             Serial.println(startTime + 3);
//           }    
//         }
//       }

//     if (update){
//       Serial.println("*** Tlc update fades***");
//       tlc_updateFades();
//       update = false;
//     }

//     startTime += 3;
//     brightness += 3;
//     // pulse clk pin 4017
//     }
//   }

// }
