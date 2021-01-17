// TASKS
// - operate reed matrix. Send interrupt signal to rpi zero when moves are detected
// - operate led matrix. Recieve led instruction from rpi zero 
// - communicate (answer) to rpi zero 
#include "SPI.h"
#include "Wire.h"
#include "an32183a.h"

const bool DEBUG = true;

///////////
// POWER //
///////////
enum states{
  POWER,
  RPI_BOOT,
  MAIN,
  PLAY,
  REED,
};
int currentState = POWER;
const byte shutdownInterruptPin = 7;
const byte powerButtonPin = 3;
const byte powerLedPin = A7;


///////////////////
// COMMUNICATION //
///////////////////
const long SERIAL_BAUDRATE = 115200;
const SPISettings settings(8000000, MSBFIRST, SPI_MODE0);
const char START_CHAR = '<';
const char STOP_CHAR = '>';
const char SPLIT_CHAR = '\t';


////////////////
// LED MATRIX //
////////////////
// NEW AN32183A LED IC
// TODO
///////////////////////
 byte frames = 0b00000000;  //active frames


/////////////////
// REED MATRIX //
/////////////////
const byte INTERRUPT_TO_RPI_PIN = A3; //Interrupt to rpi zero
//Reed matrix wiring
//output ic 74hc595
//a595dataPin          // Connects MOSI 11 to the DS/SER, serial in,  pin of the 595
// a595clockPin        // Connects sck pin 13 to the SH_CP/SRCLK shiftregister clock,  of the 595
const byte a595slaveSelectPin  = 5;  // Connects to the ST_CP/RCLK, storage register clock, of the 595
// //input ic 74hc165
const byte b165ploadPin        = 4;  // Connects to PL/SH-LD Parallel load pin the 165
const byte b165clockEnablePin  = 2;  // Connects to CE/CLK INH Clock Enable pin the 165
// b165dataPin         // Connects MISO 12 pin to the Q7 pin of the 165
// b165clockPin        // Connects sck pin 13 to the CP/CLK Clock pin of the 165

//Variables
volatile bool buttonChangedFlag = false; //Set true for the first time
byte currentBoard[] = {0, 0, 0, 0, 0, 0, 0, 0};  //Representation of the board stored in memory. Board is represented by 8 bytes --> 8 x 8 bits for the 64 squares
byte incomingBoard[] = {0, 0, 0, 0, 0, 0, 0, 0}; //New board reading from reed switches
byte  new_move = 100;  // This value indicates thre's no move (situation when the python program just triggers the reed interrupt)


///////////
// SETUP //
///////////
void setup()
{
  digitalWrite(shutdownInterruptPin, HIGH);
  Serial.begin(SERIAL_BAUDRATE);
  if (DEBUG){
    Serial.write("START!");
  }
  pinMode(powerLedPin, OUTPUT);
  // The arduino will stay in this loop until it recieves an '<H' message from raspberry pi.
  currentState = POWER; //Set initial state
  digitalWrite(powerLedPin, HIGH);

  //DEBUG
  // ledTest();
}


///////////
// LOOP  //
///////////
void loop() 
{
  // The arduino loop:
  // polling reed matrix, control led matrix, check incoming serial

  if (currentState == POWER){
    stateMachine(RPI_BOOT);
  }

  if (currentState = RPI_BOOT){
    fade_in_analog(powerLedPin);
    wait(50);
    fade_out_analog(powerLedPin);
    wait(50);
  }

  // check reed matrix
  if (currentState == REED){
    readReedSwitchMatrix();
    checkBoard();
    // reed change detected
    if (buttonChangedFlag){
      reedInterrupt();
      display_pin_values();
    }
  }

  delayMicroseconds(2000);  // Delay is necessary for the serial
  // check serial
  if (Serial.available() > 0)
  {
    checkSerial();
  }

  if (powerButtonPin == HIGH){
    stateMachine(POWER);
  }
}


/////////////
//FUNCTIONS//
/////////////
// *** STATE MACHINE *** //
void stateMachine(int newState){
  switch(currentState){
    case REED:
      currentState = reedState(newState);
      break;
    case POWER:
      currentState = powerState(newState);
      break;
    case MAIN:
      currentState = mainState(newState);
    case RPI_BOOT:
      currentState = rpiBootState(newState);
      break;
    default: break;
  }
}

int powerState(int newState){
  //only POWER to RPI_BOOT
  // TODO led test?
  // *** Reed matrix ***//
  //initialize pins
  SPI.begin();
  pinMode(a595slaveSelectPin, OUTPUT);
  digitalWrite(a595slaveSelectPin, HIGH);
 
  pinMode(b165ploadPin, OUTPUT);
  pinMode(b165clockEnablePin, OUTPUT);
  digitalWrite(b165ploadPin, HIGH);
  digitalWrite(b165clockEnablePin, HIGH);
  
  pinMode(INTERRUPT_TO_RPI_PIN, OUTPUT);
  digitalWrite(INTERRUPT_TO_RPI_PIN, LOW);

  readReedSwitchMatrix();
  for (int i = 0; i < 8; i++){
    currentBoard[i] = incomingBoard[i];
  }
  return MAIN;
}

int mainState(int newState){
  if (newState == POWER){  // Start shutdown
    // TODO All leds off
    SPI.end();
    digitalWrite(shutdownInterruptPin, HIGH); // Send shutdown signal to rpi0
    while (true){
      // The power will be cut off when the rpi0 shuts down
      fade_in_analog(powerLedPin);
      wait(50);
      fade_out_analog(powerLedPin);
      wait(50);
    }
  }

  else if (newState == REED){
      // nothing to to :-)
  }
  return newState;
}

int reedState(int newState){
  if (newState == MAIN){
    return MAIN;
  }
  else if (newState == POWER){
    return mainState(POWER);
  }
}

int rpiBootState(int newState){
  //ONLY RPI_BOOT to MAIN
  analogWrite(powerLedPin, 0);
  return MAIN;
} 

void wait(int time){
    unsigned long timestamp = millis();
    while (millis() - timestamp < time);
}

void fade_in_analog(int ledPin){
  int step = 2;
  for (int brightness = 2; brightness <= 64; brightness += step){
      analogWrite(ledPin, brightness);
      wait(30);
  }
}

void fade_out_analog(int ledPin){
  int step = 2;
  for (int brightness = 64; brightness >= 2; brightness -= step){
      analogWrite(ledPin, brightness);
      wait(30);
  }
}

// *** Reed matrix ***//
void updateCurrentBoard(){
  for (int i = 0; i < 8; i++){
    currentBoard[i] = incomingBoard[i];
  }
}

void reedInterrupt(){
    digitalWrite(INTERRUPT_TO_RPI_PIN, HIGH); //Send interrupt to Rpi
    updateCurrentBoard();
    buttonChangedFlag = false;
    digitalWrite(INTERRUPT_TO_RPI_PIN, LOW);
}

void readReedSwitchMatrix(){
  //Puts every buttonstate into the incoming array
  for (byte row = 0; row < 8; row++) {
    //SEND to the 74hc595
    byte shift = 1 << row; 
    SPI.beginTransaction(settings);
    digitalWrite(a595slaveSelectPin,LOW);
    SPI.transfer(shift);
    digitalWrite(a595slaveSelectPin, HIGH);
    SPI.endTransaction();

    //READ 74hc165
    digitalWrite(b165ploadPin, LOW);
    digitalWrite(b165ploadPin,HIGH);
    
    SPI.beginTransaction(settings);
    digitalWrite(b165clockEnablePin, LOW);
    incomingBoard[row] = SPI.transfer(0);
    digitalWrite(b165clockEnablePin, HIGH);
    SPI.endTransaction();
  }
}

// get the new move
// CODE IS ADAPTED FOR THE INCORRECT SOLDERED REED MATRIX :-S
// void checkBoard(){
//   for (int i = 0; i < 8; i++)
//     {
//       byte mask = 00000001;
//       for (int j = 0; j < 8; j++)
//       {
//         if ((incomingBoard[i] & mask) != (currentBoard[i] & mask))
//         {
//           new_move = (i * 8) + j;
//           buttonChangedFlag = true;
//           return;    
//         }
//         mask <<= 1;
//       }    
//     }
// }

void checkBoard(){
  for (int i = 0; i < 8; i++)
    {
      byte mask = 00000001;
      for (int j = 0; j < 8; j++)
      {
        if ((incomingBoard[i] & mask) != (currentBoard[i] & mask))
        {
          new_move = 63 - (i + 8 * j);
          buttonChangedFlag = true;
          return;    
        }
        mask <<= 1;
      }    
    }
}

// DEBUG //
void display_pin_values(){
  char letters[9] = {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'};
  Serial.print("Switch States:\r\n");
  
  for (byte i = 0; i < 8; i++){
    byte index = 7 - i;  // Iterates incoming board in opposite direction because reed matrix was incorrectly soldered
    Serial.print("Row: ");
    Serial.print(letters[i]);
    Serial.print(": ");
    Serial.print(incomingBoard[index]);
    if (incomingBoard[7 - i] < 10){
      Serial.print("   ");
    }
    else if (incomingBoard[index] < 100){
      Serial.print("  ");
    }
    else{
      Serial.print(" ");
    }
    
    for (byte mask = (byte)10000000; mask > 0; mask >>= 1){
      if (mask & incomingBoard[index]){
        Serial.print(letters[i]);  
        Serial.print(8 - byte(log(mask)/log(2)));   
        Serial.print(" ");
      }
      else{
        Serial.print("-- ");
      }
    }
    Serial.print("\r\n");
  }
  Serial.print("\r\n");
  Serial.flush();
}


// *** Serial ***//
void checkSerial() { 
  //Handler for incoming serial data. Read incoming message and execute according functions
  if (Serial.read() == START_CHAR){
    char in = Serial.read();
    // Serial.write(in);
    while (Serial.available() > 0){
      Serial.read();
    }
    // MESSAGES
    // H --> say 'hello'
    // B --> send complete Board
    // M --> send Move
    // R --> reed on
    // O --> reed off
    // L --> execute led matrix instruction
    // I --> send reed interrupt signal to rpi (for debugging)
    // S --> send shutdown interrupt to rpi (for debugging)

    switch (in)
    {
      // Hello!
      case 'H':
        Serial.write(START_CHAR);
        Serial.write("hello pi!");
        Serial.write(STOP_CHAR);
        stateMachine(MAIN);
        break;
      
      // Send complete board to Rpi_zero.
      case 'B': 
        readReedSwitchMatrix();
        updateCurrentBoard();
        Serial.write(START_CHAR);
        Serial.write(currentBoard, sizeof(currentBoard));
        Serial.write(STOP_CHAR);
        break;

      //Send detected move to Rpi_zero.
      case 'M':
        Serial.write(START_CHAR);
        Serial.write(new_move);
        Serial.write(STOP_CHAR);
        new_move = 100;
        break;

      //Activate reed detection
      case 'R':
        readReedSwitchMatrix();
        updateCurrentBoard();
        Serial.write(START_CHAR);
        Serial.write(currentBoard, sizeof(currentBoard));
        Serial.write(STOP_CHAR);
        break;

      //Deactivate reed detection
      case 'O':
        readReedSwitchMatrix();
        updateCurrentBoard();
        Serial.write(START_CHAR);
        Serial.write(currentBoard, sizeof(currentBoard));
        Serial.write(STOP_CHAR);
        break;

      // Expect an 'action' and a 'leds' array
      case 'L':
        readReedSwitchMatrix();
        updateCurrentBoard();
        Serial.write(START_CHAR);
        Serial.write(currentBoard, sizeof(currentBoard));
        Serial.write(STOP_CHAR);
        break;

      // DEBUG
      // Send pulse with reed interrupt pin
      case 'I':
        readReedSwitchMatrix();
        updateCurrentBoard();
        Serial.write(START_CHAR);
        Serial.write(currentBoard, sizeof(currentBoard));
        Serial.write(STOP_CHAR);
        break;

      // DEBUG
      // Send pulse with shutdown interrupt pin
      case 'S':// DEBUG
        break;//...

      default:  // Don't understand
        Serial.write('x');
        break;
    }

    // Clear buffer
    Serial.flush();
    in = 0;
  }
  else {
    Serial.write("Not a start char");
  }
}


// *** Leds ***//
void ledControl(uint8_t action){
  /* Led actions: 
  commands are 1 byte followed by optional items
    - square(s) on:
            6 items --> byte 1: nr frame
                        0 - 64 byte(s) square nr(s)
                        SPLIT_CHAR
                        3 brightness settings for 3 color (byte RED, byte GREEN, byte BLUE)             
    - led(s) off:
            3 items --> byte 1: nr frame 
                        0 - 64 : nr square(s)
                        SPLIT_CHAR
    - play frames
    - stop frames
    - clear frame   --> byte 1: nr frame
  */
  switch (action){
    case 1: squareOn(); break;
    case 2: squareOff(); break;
    case 3: blinksquare(); break;
    case 4: allOff(); break;
    case 5: showBoard(); break;
    case 6: ledTest(); break;
    default: break;
  }
}

void squareOn(){
  // Turn square on
  // Parameters: square nr, color, frame(s)
}

void squareOff(){
  // Event: Player turn + correct piece lifted --> Indeicate lifted piece with green
  // Parameters: square nr, color, frame(s)
}

void blinksquare(){
  //turn on red square (now there is a green/blue and red square...)
  // Parameters: square nr, color, frame(s)
}

void allOff(){
  //Turn off all leds
}

void showBoard(){
  //indicate correct pieces with green and incorrect/missing pieces with red
}

void ledTest(){
  // DEBUG led test
}

//OLD IS31FL3731
// void squareOn(){
//   byte frame = Serial.read();
//   byte squares[64];
//   byte in = Serial.readBytesUntil(SPLIT_CHAR, squares, 64);
//   byte red = Serial.read();
//   byte green = Serial.read();
//   byte blue = Serial.read();
//   for (int i = 0; i < in; i++)
//     ledmatrix.squareOn(frame, squares[i], red, green, blue);
// }

// void squareOff(){
//   byte frame = Serial.read();
//   byte squares[64];
//   byte in = Serial.readBytesUntil(SPLIT_CHAR, squares, 64);

//   for (int i = 0; i < in; i++)
//     ledmatrix.squareOff(frame, squares[i]);
// }

// void playFrames(){
//   byte frames = Serial.read();
//   byte loops = Serial.read();
//   ledmatrix.play(frames, loops) ; 
// }

// void blankFrame(){
//   byte frame = Serial.read();
//   ledmatrix.clearFrame(frame);
// }

// void showFrame(){
//   byte frame = Serial.read();
//   ledmatrix.displayFrame(frame);
// }
