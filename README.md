# chessboard
This program is used on a raspberrypi zero to run an electronic chessboard, a hobby project. 
It is used to play chess with various (opensource) chess engines like stockfish and rodent.
The board detects chess pieces with reed switches and magnets to keep track of the game.
Squares are lit up with leds to indicate computer moves, illigal moves, hints etc...
The board is powered by 18650 li-ion batteries or a 5V DC adapter.

The raspberypi communicates with the user with an electronic paper display from waveshare. 
It is interresting because is doesn't consume much power, but it takes much time to change a frame.