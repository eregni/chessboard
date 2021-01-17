#include "SPI.h"

///////////////////
// COMMUNICATION //
///////////////////
const long SERIAL_BAUDRATE = 115200;
const SPISettings settings(4000000, MSBFIRST, SPI_MODE0);
const byte START_CHAR = '<';
const byte STOP_CHAR = '>';

/////////////////
// REED MATRIX //
/////////////////

const byte INTERRUPT_TO_RPI_PIN = 17; //Interrupt to rpi zero
//Reed matrix wiring
// //output ic 74hc595
// //a595dataPin          // Connects MOSI 11 to the DS/SER, serial in,  pin of the 595
// // a595clockPin        // Connects sck pin 13 to the SH_CP/SRCLK shiftregister clock,  of the 595
const byte a595slaveSelectPin  = 15;  // Connects to the ST_CP/RCLK, storage register clock, of the 595
// //input ic 74hc165
const byte b165ploadPin        = 14;  // Connects to PL/SH-LD Parallel load pin the 165
const byte b165clockEnablePin  = 10;  // Connects to CE/CLK INH Clock Enable pin the 165
// // b165dataPin         // Connects MISO 12 pin to the Q7 pin of the 165
// // b165clockPin        // Connects sck pin 13 to the CP/CLK Clock pin of the 165

//Variables
volatile bool buttonChangedFlag = false; //Set true for the first time

byte currentBoard[] = {0, 0, 0, 0, 0, 0, 0, 0};  //Representation of the board stored in memory. Board is represented by 8 bytes --> 8 x 8 bits for the 64 squares
byte incomingBoard[] = {0, 0, 0, 0, 0, 0, 0, 0}; //New board reading from reed switches
byte  new_move = 100;  // This value indicates thre's no move (situation when the python program just triggers the reed interrupt)
bool reedActive = true;  


///////////
// SETUP //
///////////
  int testpin = 10;
void setup(){
// *** Turn on rpi relais and led grid relais ***//
  //pinMode(RPI_RELAIS, OUTPUT);
  //digitalWrite(RPI_RELAIS, HIGH);

// *** Communication ***//
  Serial.begin(SERIAL_BAUDRATE);
  SPI.begin();

// *** Reed matrix ***//
  //initialize pins
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
  display_pin_values();
  Serial.write("Start");
  }



///////////
// LOOP  //
///////////
void loop() 
{
  // check reed matrix
  if (reedActive){
    readReedSwitchMatrix();
    checkBoard();
    // reed change detected
    if (buttonChangedFlag){
      display_pin_values();
      reedInterrupt();
    }
  }

  delayMicroseconds(2000);  // Delay is necessary for the serial
  // check serial
  if (Serial.available() > 0)
  {
    checkSerial();
  }
}


/////////////
//FUNCTIONS//
/////////////
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
void checkBoard(){
  for (int i = 0; i < 8; i++)
    {
      byte mask = 0b00000001;
      for (int j = 0; j < 8; j++)
      {
        if ((incomingBoard[i] & mask) != (currentBoard[i] & mask))
        {
          new_move = (i * 8) + j;
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
    // I --> send interrupt signal to rpi (for debugging)
    // L --> execute led matrix instruction
    if (in == 'H'){
      Serial.write(START_CHAR);
      Serial.write("hello");
      Serial.write(STOP_CHAR);
    }
    // Send complete board to Rpi_zero.
    else if (in == 'B'){
    byte incomingBoard = 0;
    digitalWrite(b165ploadPin, LOW);
    digitalWrite(b165ploadPin,HIGH);
    
    SPI.beginTransaction(settings);
    digitalWrite(b165clockEnablePin, LOW);
    incomingBoard = SPI.transfer(0);
    Serial.println(incomingBoard);
    digitalWrite(b165clockEnablePin, HIGH);
    SPI.endTransaction();
    }
    else if (in == 'E'){
        SPI.beginTransaction(settings);
        digitalWrite(a595slaveSelectPin,LOW);
        SPI.transfer(255);
        digitalWrite(a595slaveSelectPin, HIGH);
        SPI.endTransaction();
    }
    //Send detected move to Rpi_zero.
    else if (in == 'M'){
      Serial.write(START_CHAR);
      Serial.write(new_move);
      Serial.write(STOP_CHAR);
      new_move = 100;
    }
    //Activate reed detection
    else if (in == 'R'){
      reedActive = true;
      Serial.write(START_CHAR);
      Serial.write("on");
      Serial.write(STOP_CHAR);
    }
    //Deactivate reed detection
    else if (in == 'O'){
      reedActive = false;
      Serial.write(START_CHAR);
      Serial.write("off");
      Serial.write(STOP_CHAR);
    }
    else if(in == 'I'){

      digitalWrite(INTERRUPT_TO_RPI_PIN, HIGH); //Send interrupt to Rpi
      delay(2);
      digitalWrite(INTERRUPT_TO_RPI_PIN, LOW);
    }
    else{
      Serial.write('x');
    }

    // Clear buffer
    Serial.flush();
    in = 0;
  }
  else {
    Serial.write("Not a start char");
  }
}