// TASKS
// - operate reed matrix. Send interrupt signal to rpi zero when moves are detected
// - operate led matrix. Recieve led instruction from rpi zero 
// - communicate (answer) to rpi zero 
#include "SPI.h"
#include "Wire.h"

const bool DEBUG = true;

///////////
// POWER //
///////////
const byte powerButtonPin = 3;
const byte powerLedPin = 7;
volatile bool powerInterruptFlag = false;

/////////////////
// BUTTONPANEL //
/////////////////
const byte buttonInterruptPin = 2;
volatile bool buttonInterruptFlag = false;
bool buttonActive = false;

///////////////////
// COMMUNICATION //
///////////////////
const long SERIAL_BAUDRATE = 115200;
const SPISettings settings(8000000, MSBFIRST, SPI_MODE0);
const char START_CHAR = '<';
const char STOP_CHAR = '>';
const char SPLIT_CHAR = '\t';
const byte interruptToRpiPin = A1; //Interrupt to rpi zero
enum interrupt_flags{
  NONE,
  MOVE,
  SHUTDOWN,
  BUTTONPRESS
};
byte rpi_int_flag =  NONE;

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
//Reed matrix wiring
//output ic 74hc595
//a595dataPin          // Connects MOSI 11 to the DS/SER, serial in,  pin of the 595
// a595clockPin        // Connects sck pin 13 to the SH_CP/SRCLK shiftregister clock,  of the 595
const byte a595slaveSelectPin  = 5;  // Connects to the ST_CP/RCLK, storage register clock, of the 595
// //input ic 74hc165
const byte b165ploadPin        = 4;  // Connects to PL/SH-LD Parallel load pin the 165
const byte b165clockEnablePin  = 10;  // Connects to CE/CLK INH Clock Enable pin the 165
// b165dataPin         // Connects MISO 12 pin to the Q7 pin of the 165
// b165clockPin        // Connects sck pin 13 to the CP/CLK Clock pin of the 165

//Variables
bool boardChangedFlag = false;
byte currentBoard[] = {0, 0, 0, 0, 0, 0, 0, 0};  //Representation of the board stored in memory. Board is represented by 8 bytes --> 8 x 8 bits for the 64 squares
byte incomingBoard[] = {0, 0, 0, 0, 0, 0, 0, 0}; //New board reading from reed switches
byte  new_move = 100;  // The 100 value indicates thre's no move
bool reedActive = false;

/////////////
// PROGRAM //
/////////////
void setup()
{
  pinMode(a595slaveSelectPin, OUTPUT);
  pinMode(b165ploadPin, OUTPUT);
  pinMode(b165clockEnablePin, OUTPUT);
  pinMode(interruptToRpiPin, OUTPUT); 
  pinMode(buttonInterruptPin, INPUT_PULLUP);
  pinMode(powerButtonPin, INPUT_PULLUP);
  pinMode(powerLedPin, OUTPUT);
  digitalWrite(a595slaveSelectPin, HIGH);
  digitalWrite(b165ploadPin, HIGH);
  digitalWrite(b165clockEnablePin, HIGH);
  digitalWrite(interruptToRpiPin, LOW);
  digitalWrite(powerLedPin, LOW); // TODO connect powerbutton led

  attachInterrupt(digitalPinToInterrupt(buttonInterruptPin), ISR_button, FALLING);
  // attachInterrupt(digitalPinToInterrupt(3), ISR_power, FALLING);  // TODO connect powerbutton

  SPI.begin();
  Serial.begin(SERIAL_BAUDRATE);
  if (DEBUG){
    Serial.println("START!");
    display_pin_values();
  }

  // The arduino will stay in this loop until it recieves a message from raspberry pi
  while (true){
    delayMicroseconds(2000);  // Delay is necessary for the serial
    if (Serial.available() > 0){
      checkSerial();
      break;
    }
  }
  buttonActive = true;
  Serial.print("BUTTONACTIVE: ");
  Serial.println(buttonActive);
}

void loop() 
{
  // The arduino loop:
  // polling reed matrix 
  // control led matrix 
  // check incoming serial
  // Button signal to rpi0
  // Powerbutton signal to Rpi0

  if (reedActive){
    readReedSwitchMatrix();
    checkBoard();
    if (boardChangedFlag){
      rpiZeroInterrupt(MOVE);
      updateCurrentBoard();
      boardChangedFlag = false;
      if (DEBUG){display_pin_values();}
    }
  }

  delayMicroseconds(2000);  // Delay is necessary for the serial
  if (Serial.available() > 0){
    checkSerial();
  }

  if (buttonActive && buttonInterruptFlag){
    if (DEBUG){Serial.println("Button interrupt!");}
    rpiZeroInterrupt(BUTTONPRESS);
    buttonActive = false;  // TODO the rpi0 needs to reactivate this after each button press
    buttonInterruptFlag = false;
  }

  if (powerInterruptFlag){
    if (DEBUG){Serial.println("Shutdown interrupt!");}
    rpiZeroInterrupt(SHUTDOWN);
    powerInterruptFlag = false;
  }
}

// TODO LEDS


/////////////
//FUNCTIONS//
/////////////
void ISR_button(){
  buttonInterruptFlag = true;
}

void ISR_power(){
  powerInterruptFlag = true;
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

void rpiZeroInterrupt(interrupt_flags flag){
    digitalWrite(interruptToRpiPin, HIGH); //Send interrupt to Rpi
    rpi_int_flag = flag;
    digitalWrite(interruptToRpiPin, LOW);  
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

void checkBoard(){
  for (int i = 0; i < 8; i++)
    {
      byte mask = 00000001;
      for (int j = 0; j < 8; j++)
      {
        if ((incomingBoard[i] & mask) != (currentBoard[i] & mask))
        {
          new_move = 63 - (i + 8 * j);
          boardChangedFlag = true;
          return;    
        }
        mask <<= 1;
      }    
    }
}

// DEBUG //
void display_pin_values(){
  char letters[8] = {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'};
  Serial.print("Reed switch States:\r\n");
  
  for (byte i = 0; i < 8; i++){
    Serial.print("Row: ");
    Serial.print(8 - i);
    Serial.print(": ");
    Serial.print(incomingBoard[7 - i]);
    Serial.print("\t|");
    
    byte mask = 1;
    for (byte j = 0; j < 8; j++){
      if ((0b10000000 >> i) & incomingBoard[7 - j]){
        Serial.print(letters[j]);  
        Serial.print(8 - i);   
        Serial.print(" ");
      }
      else{
        Serial.print("-- ");
      }
    }
    Serial.print("\r\n");
    mask <<= 1;
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
    // F --> send reason for interrupt/interrupt flag
    // B --> send complete Board
    // M --> send Move
    // R --> reed on
    // O --> reed off
    // V --> button interrupt on
    // X --> button interrupt off
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
        break;

      // send reason for interrupt/interrupt flag
      case 'F':
        Serial.write(START_CHAR);
        Serial.write(rpi_int_flag);
        Serial.write(STOP_CHAR);
        rpi_int_flag = NONE;
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

      //Activate button interrupt
      case 'V':
        buttonActive = true;
        Serial.write(START_CHAR);
        Serial.write('V');
        Serial.write(STOP_CHAR);
        break;

      //Activate button interrupt
      case 'X':
        buttonActive = false;
        Serial.write(START_CHAR);
        Serial.write('X');
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

void send_int_rpi_zero(interrupt_flags flag){
  if (DEBUG){
    Serial.write("Sending interrupt flag: ");
    Serial.write(rpi_int_flag);
  }
  rpi_int_flag = flag;
  digitalWrite(interruptToRpiPin, HIGH);
  delayMicroseconds(2);
  digitalWrite(interruptToRpiPin, LOW);
}