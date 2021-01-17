#!/usr/bin/env python3
"""Chess board with a raspberry pi zero, an arduino nano and and electronic paper display.
You can choose different chess engines to play against and configure them where possible.
The board uses reed contacts + chess pieces with magnets to scan for moves and positions.
The squares on the board are animated with 9x9 RGB led matrix."""

from time import sleep, strftime, localtime
import logging.handlers
import signal
from subprocess import run
from enum import Enum
from dataclasses import dataclass
from typing import Set, Dict, Callable
import chess
import chess.pgn
import chess.engine

import config
import gpio
import files
import serial_arduino
import epaper
import button

# import lights  DISABLED FOR NOW

# Todo: 2 new options:
#     - move score (-> python-chess module)
#     - naming opening

# #############
# ## Logging ##
# #############
LEVEL = logging.DEBUG
LOG_FORMATTER = logging.Formatter(
    fmt='[%(asctime)s.%(msecs)03d] [%(module)s] [%(threadName)s] %(levelname)s: %(message)s',
    datefmt='%D %H:%M:%S',
)
LOG_FORMATTER.default_msec_format = '%s.%03d'
LOG_HANDLER = logging.handlers.RotatingFileHandler(
    filename=config.LOG_FILE,
    maxBytes=500000,
    backupCount=5,
)
LOG_HANDLER.setFormatter(LOG_FORMATTER)
LOG_HANDLER.setLevel(LEVEL)
LOG = logging.getLogger()
LOG.addHandler(LOG_HANDLER)
LOG.setLevel(LEVEL)
LOG_HANDLER.doRollover()
# alter loglevel for some mudules to reduce 'noise' in the log file
logging.getLogger('Image').setLevel(logging.WARNING)
logging.getLogger('PngImagePlugin').setLevel(logging.WARNING)


# End log settings
# -------------------------------------------------------------------------------------------------


# ###########
# ## Class ##
# ###########
@dataclass
class Game:
    """The game variables"""
    move_stack_copy: list = None
    engine: chess.engine.SimpleEngine = None
    board: chess.Board = chess.Board()
    pgn_notes: chess.pgn = chess.pgn.Game()
    pgn_headers: chess.pgn.Headers = chess.pgn.Headers()
    setup: config.Setup = config.DEFAULT_SETUP
    computer_move: chess.engine.PlayResult = None
    piece_up: int = -1
    # confirm: bool = False
    hint: bool = False


class States(Enum):
    """Program states"""
    BOOT = 0
    MAIN = 1
    GAME = 2
    BOARD_INVALID = 3
    PLAYER_TURN = 4
    COMPUTER_TURN = 5
    END_GAME = 6


class State:
    """Program states"""
    _program_state = States.BOOT

    @classmethod
    def is_set(cls, _state) -> bool:
        return cls._program_state == _state

    @classmethod
    def set(cls, _state) -> None:
        if _state not in States:
            raise ValueError('Need a state from States class')

        cls._program_state = _state


# End class
# -------------------------------------------------------------------------------------------------
# ###############
# ## FUNCTIONS ##
# ###############
# -----------------------
# -- General functions --
# -----------------------
def signal_exit_program(game, signr, *args) -> None:
    """
    handler for SIGINT, SIGTERM
    :param game: Game
    :param signr: int
    """
    LOG.debug('%s: exit_program triggered', signr)
    exit_program(game, shutdown=False)


def arduido_interrupt(self, gpio_pin: int, level: int, tick: int):
    """Callback function for interrupt coming from arduino"""
    incoming = serial_arduino.get_interrupt_reason()
    if incoming == serial_arduino.ReasonInterrupt.NONE:
        LOG.warning("Got an arduino interrupt but recieved code NONE")
    elif incoming == serial_arduino.ReasonInterrupt.BUTTONPRESS:
        LOG.debug("Arduino interrupt: BUTTONPRESS")
        button_panel.handler_callbacks()
    elif incoming == serial_arduino.ReasonInterrupt.SHUTDOWN:
        LOG.debug("Arduino interrupt: SHUTDOWN")
        shutdown_interrupt()
    elif incoming == serial_arduino.ReasonInterrupt.MOVE:
        LOG.debug("Arduino interrupt: MOVE")
        button_panel.move_event.set()
    else:
        LOG.warning("Arduino interrupt: Got invalid interrupt flag!")


def exit_program(game: Game, shutdown: bool = True) -> None:
    """
    :param game: Game
    :param shutdown: bool, Exit program and shutdown the raspberry pi as well
    """
    LOG.info("Exit program")
    button_panel.update_buttons([])  # turn off btn led
    # Save if necessary
    try:
        game.board.peek()
        if not game.engine.ping():
            game.engine.close()
            game.engine.quit()
            save_pgn(game)
    except IndexError:
        LOG.debug("Board.moves_stack is empty")
    except NameError:
        LOG.debug("No active game so no need to save anything")

    # frame goodbye
    frame = epaper.Frame(name='exit', items=[epaper.FrameImage('images/calvin/sleeping.png')])
    epaper_screen.update_frame(button_panel, frame)
    # Wait for possible screen thread to finish
    while epaper_screen.busy():
        sleep(0.05)
    epaper_screen.sleep()
    gpio.cleanup()
    LOG.debug('GPIO cleaned')
    if shutdown:
        LOG.info('exit_program: shutdown pi')
        run(['sudo', 'poweroff'], check=True)
    else:
        LOG.debug('exit program')

    raise SystemExit(0)


def question(line: str) -> bool:
    """
    Ask question on epaper
    param question: str: The question shown on epaper
    return: bool: user pressed 'confirm' or 'cancel'
    """
    frame = epaper.question(button_panel, line=line)
    epaper_screen.update_frame(button_panel, frame, important=True)
    return button_panel.execute_task(timeout=30)
    

def shutdown_interrupt(*args) -> None:
    """
    Arduino send shutdown intterupt for three possible reasons:
        - User pressed power button
        - Coulomb counter reached minimum --> warning on epaper and power led
        - Low voltage --> info on epaper and start shutdown
    """
    epaper_screen.enabled = True
    if question("Shutdown chessboard?"):
        exit_program(main_game, shutdown=True)

    else:
        epaper_screen.enabled = True
        back_to_game(main_game) if state.is_set(States.GAME) else epaper_screen.get_menu_item(first=True)


# ----------
# -- Game --
# ----------
def play_game(game: Game, saved_game: chess.pgn.Game = None) -> None:
    """
    start and end new/saved
    :param game: Game
    :param saved_game: chess.pgn
    :return:
    """
    LOG.info('play!')
    new_game(game) if saved_game is None else load_game(game, saved_game)

    LOG.info('start engine')
    game.engine = chess.engine.SimpleEngine.popen_uci(game.setup.engine.path)

    engine_setup = game.setup.engine.options
    # todo assemble engine options to an engine.ConfigMapping (+ extra options)

    game.engine.configure(engine_setup)
    LOG.debug('start loop')

    # Game loop
    State.set(States.GAME)
    while state.is_set(States.GAME):
        if not state.is_set(States.GAME):
            break

        validate_board(game)

        if game.board.turn == game.setup.color.value:
            player_move(game)
            game.computer_move = chess.engine.PlayResult(move=None, ponder=None)

        else:
            computer_move(game)

        update_pgn_notes(game)
        save_pgn(game, )

    end_game(game)


def new_game(game: Game) -> None:
    """A new starts with filling in values for the pgn notes"""
    LOG.info('new GAME')
    engine = game.setup.engine
    game.board = chess.Board()
    game.pgn_headers['Event'] = 'Player vs {0} {1}'.format(engine.name, engine.version)
    game.pgn_headers['Date'] = strftime('%A %d %B %Y - %H:%M', localtime())
    setup_text = ['{0} = {1}{2}'.format(item.name, item.value, item.unit) for _, item in engine.options.items()]
    engine_text = '{0} {1}'.format(engine.name, setup_text)
    game.pgn_headers['White'] = 'Player' if game.setup.color.value is config.WHITE else engine_text
    game.pgn_headers['Black'] = 'Player' if game.setup.color.value is config.BLACK else engine_text
    game.pgn_headers['Site'] = '-'
    game.pgn_headers['Round'] = '-'
    game.pgn_headers['Result'] = str(game.board.result())
    try:
        run(['rm', config.COMPUTER_MOVE])
    except FileNotFoundError:
        LOG.debug('no saved computer_move present')


def load_game(game: Game, saved_game: chess.pgn.Game) -> None:
    """
    :param game: Game
    :param saved_game: chess.pgn.Game, saved game
    1:  Set up the chess.Board based on the given pgn notes from saved file
    2:  If present (usually is), get the last calculated computer move + ponder
    :param saved_game: pgn string
    :return:
    """
    LOG.info('load GAME')
    try:
        moves_string = files.open_move(config.COMPUTER_MOVE)
        move0 = chess.Move.from_uci(moves_string[:4])
        # There is not always a ponder move
        move1 = chess.Move.from_uci(moves_string[4:]) if len(moves_string) > 4 else None
        game.computer_move = chess.engine.PlayResult(move=move0, ponder=move1)
    except (TypeError, ValueError):
        LOG.debug('no saved computer_move present')

    try:
        game.board = saved_game.board()
        for move in saved_game.mainline_moves():
            game.board.push(move)
        # load pgn
        game.pgn_headers = saved_game.headers
        update_pgn_notes(game)
        LOG.info('GAME loaded')
    except (TypeError, ValueError):
        LOG.error('save GAME corrupted!')
        run(['mv', config.SAVEGAME, config.SAVEGAME + 'error'])
        new_game(game)


def end_game(game: Game) -> None:
    """
    Actions at end GAME
    'Confirm' or 'Save pgn file'
    :param: result, GAME.board.result()
    :return:
    """
    LOG.info('GAME finished!')
    result = game.board.result()
    game.pgn_notes.headers['Result'] = result
    epaper_screen.enabled = True
    epaper_screen.update_frame(button_panel, epaper.end_game(button_panel, result, game.setup, game.board))
    button_panel.execute_task(timeout=60)
    game.confirm = False
    run(['rm', config.SAVEGAME])


def update_pgn_notes(game: Game) -> None:
    """update pgn text in GAME.pgn_notes plus optional comments"""
    # TODO: add comment tag to nodes. --> openings...
    game.pgn_notes = chess.pgn.Game.from_board(game.board)
    game.pgn_notes.headers = game.pgn_headers.copy()
    LOG.debug('pgn notes updated')


def validate_board(game: Game, message: str = 'Board invalid!') -> None:
    """
    holds the Game in case the fysical board doesn't matches the GAME.board.
    Indicates pieces who are missing and pieces on a wrong square.
    The GAME is released as soon as the psysical board matches with the chess.Board.
    On release the frame on the screen is refreshed based on chess.Board.turn -> computer or player.
     """
    LOG.debug('validate_board')
    current_board = get_board_square_set(game.board)
    LOG.info('current board:\n%s', game.board.__str__())
    old_incoming_board = current_board.copy()
    loop_count = 0
    state.set(States.BOARD_INVALID)
    while state.is_set(States.BOARD_INVALID):
        incoming_board = chess.SquareSet(squares=serial_arduino.ask_board())
        if incoming_board.symmetric_difference(
                current_board) == 0:
            state.set(States.GAME)
            LOG.debug('pieces are ok')
            game.piece_up = -1
            break
        else:
            # Do not update epaper when wait_for_reed_switch_interrupt() was
            # triggered by a timeout
            if old_incoming_board.symmetric_difference(incoming_board) != 0:
                LOG.info('board incorrect!')
                old_incoming_board = incoming_board.copy()
                frame = epaper.game_validate_board(
                    button_panel, message, current_board, incoming_board, game.board)
                if loop_count == 3:
                    # Also skip some frames if there are too many frames in
                    # line
                    epaper_screen.update_frame(button_panel, frame, important=True)
                    loop_count = 0
                else:
                    epaper_screen.update_frame(button_panel, frame, important=False)
                    loop_count += 1

            LOG.debug(validate_board_debug(current_board, incoming_board))
            # TODO LED: mark according squares with leds
            incoming_board.clear()
            button_panel.wait_for_move(timeout=3)


def validate_board_debug(current_board: chess.SquareSet, incoming_board: chess.SquareSet) -> None:
    """Print missing and wrong moves. Only used for debugging"""
    missing = [square for square in current_board if square not in incoming_board]
    wrong_place = [
        square for square in incoming_board if square not in current_board]
    wrong = [' . '] * 64
    for key_missing in missing:
        wrong[key_missing] = ' ! '
    for key_wrong_place in wrong_place:
        wrong[key_wrong_place] = ' X '

    print('Nr of incorrect squares: {0} pieces missing, {1} wrong position'.format(len(missing), len(wrong_place)))

    for i in range(7, -1, -1):
        print('\n')
        for j in range(8):
            print(wrong[i * 8 + j], end='')  # DEBUG
    print('\n')


def get_board_square_set(board: chess.Board) -> chess.SquareSet:
    """
    Returns current board represented in list with 64 bits
    :returns chess.SquareSet
    """
    square_set = chess.SquareSet()  # Empty square set
    for key in board.piece_map().keys():
        square_set.add(key)

    return square_set


def push_move(game: Game, move: chess.Move) -> None:
    """
    Push move to board.move_stack
    :param game: Game
    :param move: chess.Move
    :return:
    """
    if game.setup.color.value == game.board.turn:
        epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=epaper.PLAYER_MOVE_CONFIRMED, partial_frame=True))

    game.board.push(move)
    game.piece_up = -1
    LOG.info('move pushed')


# ---------------------
# -- Move validation --
# ---------------------
def player_move(game: Game) -> None:
    """
    loop to wait for move from player = eventdetected from reed switch matrix. The loop is finished when a valid move has been made.
    """
    State.set(States.PLAYER_TURN)
    LOG.info('player turn')
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel))
    epaper_screen.update_frame(button_panel, epaper.game_engine_info(player_turn=True, engine=game.setup.engine), important=False)
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=epaper.PLAYER_WAIT, partial_frame=True), important=False)

    legal_moves = game.board.legal_moves
    legal_move_from = {move.from_square for move in game.board.legal_moves}
    while State.is_set(States.PLAYER_TURN):
        if game.piece_up is None:
            legal_squares = legal_move_from
        else:
            legal_squares = {move.to_square for move in legal_moves if move.from_square == game.piece_up}

        LOG.debug('waiting for move...')
        button_panel.wait_for_move()
        if state.is_set(States.MAIN):
            return

        incoming = serial_arduino.new_detected_move()
        if game.hint:
            erase_hint = epaper.PartialFrame(name='erase_hint', width=200, height=40, pos=(200, 165), important=False)
            epaper_screen.update_frame(button_panel, erase_hint)
            game.hint = False

        new_move = validate_player_move(game, incoming, legal_squares)
        if isinstance(new_move, chess.Move):
            break

        if game.setup.wait_to_confirm:
            epaper_screen.update_frame(button_panel, epaper.PLAYER_CONFIRM)
            while not confirm_move(game):
                pass

        new_move = chess.Move(game.piece_up, incoming)
        push_move(game, new_move)
        State.set(States.GAME)


def validate_player_move(game: Game, move: int, legal_moves: Set[chess.Move]) -> chess.Move:
    """
    validations:    - can the piece make any move (black and white)?
                    - did the piece made a valid move?
                    - is the move a capture?
                    - detects special moves: castling, promotion, en passant
                    - did the player put a piece back on it"s original square (Which is against some chess rule...)?
    if any kind of move appears to be invalid the program will get stuck in a loop from the "indicate_missing_pieces"
    function until all pieces are putted back to the original position (at the beginning of the turn)
    :returns the valid chess.Move or None in case of a wrong move
    """
    result = None
    LOG.debug('validate new player move')

    legal_squares_up = set(move.from_square for move in legal_moves)
    legal_squares_down = set(move.to_square for move in legal_moves)

    # INVALID MOVE
    if move not in legal_squares_up.union(legal_squares_down):
        LOG.info('invalid move!')
        invalid_move(game)

    # VALID MOVE
    elif move in legal_squares_up:
        # 1: Put piece back
        # 2: Piece up
        # put piece back on same square (not always valid by the chess rules :-)
        if move == game.piece_up:
            LOG.info('piece putted back')
            game.piece_up = None
            epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=epaper.PLAYER_WAIT, partial_frame=True), important=False)
        # Piece up
        else:
            game.piece_up = move
            LOG.info('piece up: %s square_nr:%s', chess.square_name(move), move)
            epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=epaper.get_half_move_text(move, game.board), partial_frame=True))

    else:
        new_move = chess.Move(game.piece_up, move)
        LOG.info('new move: %s', new_move.uci())

        # 1: En passant?
        # 2: Castling?
        # 3: Promotion?
        # 4: normal move

        # en passant, capture or castling
        if validate_en_passant(game, new_move) or validate_caputure(game, new_move) or validate_castling(game, new_move):
            text = epaper.get_move_text(new_move, game.board)

        # promotion
        elif game.board.piece_type_at(game.piece_up) == chess.PAWN and chess.square_rank(move) in [0, 7] and validate_promotion(new_move):
            text = epaper.get_move_text(new_move, game.board)
            LOG.info('promotion succesfull!')

        # normal move
        else:
            LOG.info('move is valid')
            text = epaper.get_move_text(new_move, game.board)

        epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=text, partial_frame=True))
        result = new_move

    return result


def confirm_move(game: Game) -> bool:
    """
    a move is confirmed by leaving the moved piece on the board a few seconds (as set in the config file)
    Confirmation is positive --> move gets pushed to board
    Confirmation is negative --> call indicate_missing_pieces
    """
    if button_panel.wait_for_move(timeout=config.TIME_CONFIRM_MOVE):
        LOG.info('not confirmed')
        validate_board(game)
        return False

    LOG.info('move is confirmed')
    return True


def invalid_move(game: Game) -> None:
    """Handle invalid moves"""
    if game.piece_up is None:
        message = 'This piece cannot be moved'
    else:
        message = 'Invalid move'

    validate_board(game, message=message)
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel))
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=epaper.PLAYER_WAIT, partial_frame=True), important=False)


def computer_move(game: Game) -> None:
    """chess program calculates move + wait for player to move the piece"""
    State.set(States.COMPUTER_TURN)
    LOG.info('computer turn')
    button_panel.toggle_alarm()
    epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel=button_panel))
    epaper_screen.update_frame(button_panel, (epaper.game_engine_info(player_turn=False, engine=game.setup.engine)))
    epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel=button_panel, move_text=epaper.game_computer_thinking(game.setup), partial_frame=True), important=False)

    button_panel.toggle_alarm(active=False)

    # get a new move or load from savegame
    if state.is_set(States.MAIN):
        return
    if game.computer_move.move is not None:
        new_move = game.computer_move.move
    else:
        calculate_move(game)
        new_move = game.computer_move.move

    # Show the computer move
    LOG.info('new move: %s', new_move)
    LOG.info('wait for confirmation from board')
    while state.is_set(States.COMPUTER_TURN):
        epaper_screen.update_frame(button_panel, epaper.COMPUTER_CONFIRM)
        epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel=button_panel, move_text=epaper.get_move_text(new_move, game.board), partial_frame=True))
        # Led --> mark from and to_square
        button_panel.wait_for_move()
        if state.is_set(States.MAIN):
            break

        if validate_computer_move(game, new_move) is True:
            push_move(game, new_move)
            State.set(States.GAME)
        elif new_move == 100:
            LOG.debug('computer_move: dummy new_move')
        else:
            validate_board(game, message='Wrong move!')
            epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel=button_panel))
            epaper_screen.update_frame(button_panel, epaper.game_engine_info(player_turn=False, engine=game.setup.engine))


def calculate_move(game: Game) -> None:
    """Update GAME.computer move with new calculation. Save the move to file as well"""
    LOG.info('thinking...')
    movetime = game.setup.engine.options['movetime'].value
    game.computer_move = game.engine.play(game.board, chess.engine.Limit(time=movetime), ponder=game.setup.engine.ponder)
    files.save_move(config.COMPUTER_MOVE, "".format(game.computer_move.move, game.computer_move.ponder))


def validate_computer_move(game: Game, new_move: chess.Move) -> bool:
    """
    Shows the computer move on the screen
    validate if the computer piece is moved as instructed
    :returns True/False"""
    incoming_move = serial_arduino.new_detected_move()
    # TODO: finish promotion
    # 1: Capture
    # 2: Castling
    # 3: En passant?
    # 4: Piece up?
    # 5: Piece back
    # 6: Move Done
    # 7: Invalid
    # 8: promotion
    if incoming_move == new_move.from_square:
        if game.board.is_en_passant(new_move):
            LOG.debug('en passant')
            result = validate_en_passant(game, new_move, player=False)
        elif game.board.is_capture(new_move):
            LOG.debug('capture')
            result = validate_caputure(game, new_move, player=False)
        elif game.board.is_castling(new_move):
            LOG.debug('castling')
            result = validate_castling(game, new_move, player=False)
        elif chess.square_rank(new_move.to_square) in [0, 7] and game.board.piece_type_at(new_move.from_square) is chess.PAWN:
            LOG.debug('promotion')
            result = validate_promotion(new_move)
        else:
            LOG.debug('normal move')
            result = validate_normal_computer_move(new_move)
    else:
        result = False  # invalid move

    return result


def validate_normal_computer_move(move: chess.Move) -> bool:
    """
    Player picked up the right piece. Now place it on thye right square...
    :param move: chess.Move: move given by the chess engine
    :return:
    """
    button_panel.wait_for_move()
    if state.is_set(States.MAIN):
        return False

    incoming = serial_arduino.new_detected_move()
    if incoming == move.to_square:
        return True

    return False


def validate_caputure(game: Game, new_move: chess.Move, player: bool = True) -> bool:
    """
    validate a new_move detected as a "capture"
    :returns True/False
    """
    if game.board.is_capture(new_move):
        LOG.debug('capture!')
        step = 1 if player else 0
        while True:
            button_panel.wait_for_move()
            if state.is_set(States.MAIN):
                result = False
                break
            incoming_move = serial_arduino.new_detected_move()
            if incoming_move == new_move.to_square and step == 0:
                step += 1
                LOG.debug('removed captured piece')
            elif incoming_move == new_move.to_square and step == 1:
                LOG.debug('capture done!')
                result = True
                break
            else:
                LOG.debug('wrong piece or square')
                LOG.debug('try the move again!')
                result = False
                break
    else:
        result = False

    return result


def get_castling_type(game: Game, move: chess.Move) -> chess.Move:
    """
    returns the correct tower move from a castling move
    :param game: Game
    :param move: chess.Move
    :return:
    """
    if game.board.turn is chess.WHITE:
        tower_move = chess.Move(7, 5) if game.board.is_kingside_castling(move) else chess.Move(0, 3)
    else:
        tower_move = chess.Move(63, 61) if game.board.is_kingside_castling(move) else chess.Move(56, 59)
    LOG.info('castling move: %s', tower_move.uci())
    return tower_move


def validate_castling(game: Game, new_move: chess.Move, player: bool = True):
    """
     validate a new_move detected as"castling
    :param game: Game
    :param new_move: int, square nr of king's move TO square.
    :param player: Set this True if the move is made by the player
    :return: True if move is correct castling else False
    """
    if game.board.is_castling(new_move):
        LOG.info('castling!')
        tower_move = get_castling_type(game, new_move)
        step = 1 if player else 0
        while True:
            button_panel.wait_for_move()
            if state.is_set(States.MAIN):
                result = False
                break

            incoming_move = serial_arduino.new_detected_move()
            if step == 0 and incoming_move == new_move.to_square:
                step += 1
                LOG.info('king ok')
            elif step == 1 and incoming_move == tower_move.from_square:
                step += 1
                LOG.info('tower up')
            elif step == 2 and incoming_move == tower_move.to_square:
                LOG.info('castling done!')
                result = True
                break
            else:
                result = False
                break
    else:
        result = False

    return result


def validate_promotion(new_move: chess.Move, player: bool = True) -> bool:
    """validate a new_move detected as a "promotion"""
    LOG.debug('promotion: ')
    step = 1 if player else 0
    while True:
        button_panel.wait_for_move()
        if state.is_set(States.MAIN):
            result = False
            break

        incoming_move = serial_arduino.new_detected_move()
        if incoming_move == new_move.to_square and step == 0:
            step += 1
            LOG.debug('piece down')
        if incoming_move == new_move.to_square and step == 1:
            step += 1
            LOG.debug('replace pawn with queen')

        elif incoming_move == new_move.to_square and step == 2:
            LOG.debug('replaced with new queen')
            result = True
            break
        else:
            result = False
            break

    return result


def validate_en_passant(game: Game, new_move: chess.Move, player: bool = True) -> bool:
    """validate a new_move detected as a "en passant"""
    if game.board.is_en_passant(new_move):
        LOG.info('en passant!')
        step = 2 if player else 0
        captured_piece = new_move.to_square - 8 if game.board.turn is chess.WHITE else new_move.to_square + 8
        while True:
            button_panel.wait_for_move()
            if state.is_set(States.MAIN):
                result = False
                break

            incoming_move = serial_arduino.new_detected_move()
            if incoming_move is new_move.from_square and step == 0:
                step += 1
                LOG.debug('piece up')
            elif incoming_move is new_move.to_square and step == 1:
                step += 1
                LOG.info('piece down')
            elif incoming_move is captured_piece and step == 2:
                LOG.debug('removed captured pawn')
                result = True
                break

    else:
        result = False

    return result


# ###############################
# ## Button callback functions ##
# ###############################
def get_dict_callbacks() -> Dict[str, Callable]:
    """Make dict containing all callback functions """
    callbacks = (
        start_game,
        stop_game,
        confirm,
        cancel,
        undo,
        redo,
        give_hint,
        show_board,
        # show_attackers,
        save_pgn,
        engine_stop,
        back_to_game,
        show_next_menu_item,
        show_next_engine,
        change_option,
        toggle_option,
        restore_defaults,
        led_options,
    )

    return {item.__name__: item for item in callbacks}


# -------------
# -- In GAME --
# -------------
def start_game(game: Game) -> None:
    """play new GAME"""
    LOG.debug('BUTTON_EVENT start_game')
    epaper_screen.update_frame(button_panel, epaper.game_new())
    play_game(game)


def stop_game(game: Game) -> None:
    """abort the GAME and return to MAIN screen"""
    LOG.debug('BUTTON_EVENT stop GAME')
    epaper_screen.update_frame(button_panel, epaper.question(button_panel, 'Stop GAME?'))
    epaper_screen.enabled = False
    button_panel.execute_task(timeout=30)
    if game.confirm is True:
        game.confirm = False
        if not game.engine.ping():
            game.engine.close()
            game.engine.quit()

        state.set(States.MAIN)
        serial_arduino.trigger_arduino_int()

    else:
        epaper_screen.enabled = True
        back_to_game(game)


def confirm() -> bool:
    LOG.debug('BUTTON_EVENT confirm')
    return True


def cancel() -> bool:
    LOG.debug('BUTTON_EVENT cancel')
    return False


def undo(game: Game) -> None:
    """
    wait for correct reversed move.
    show player 2 reversed moves (1 computer, 1 player)
    remove moves from GAME.board.movestack but keep a copy in the GAME.move_stack_copy
    keep the old movestack until a new move/confirmation computer move has been made (in case of "redo" call)
    :return:
    """
    LOG.debug('BUTTON_EVENT undo')
    # (led indicators) make frame show computer move in reverse
    move1 = game.board.pop()  # pop function from chess.Board
    move2 = game.board.pop()
    # copy the move stack fir when the redo function is called
    game.move_stack_copy.append(move1)
    game.move_stack_copy.append(move2)

    # reverse moves
    move1 = chess.Move(move1.to_square, move1.from_square)
    move2 = chess.Move(move2.to_square, move2.from_square)

    text0 = epaper.FrameText(pos=(214, 15), content='Undo move:', fill=config.WHITE)
    text1 = epaper.FrameText(pos=(30, 40), content=''.join([str(move2), str(move1)]), font=config.FONT_BIG)
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=(text0, text1), partial_frame=True), important=False)
    # Interrupt active on buttons  'undo' 'redo'
    # Undo 1 computer move
    while True:
        button_panel.wait_for_move()
        if validate_computer_move(game, move1):
            break

    # Undo 1 player move
    while True:
        button_panel.wait_for_move()
        if validate_computer_move(game, move2):
            break

    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel))
    epaper_screen.update_frame(button_panel,
                               epaper.game_player_turn(button_panel=button_panel, content=epaper.PLAYER_WAIT, partial_frame=True),
                               important=False)


def redo(game: Game) -> None:
    """
    redo undone move(s).
    Show player 2 moves. (1 computer, 1 player).
    Remove moves from GAME.move_stack_copy and push them on the GAME.board
    :return:
    """
    LOG.debug('BUTTON_EVENT redo')
    if game.move_stack_copy == 0:
        message = epaper.FrameText(content='This is the last move', pos=(15, 6))
        epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=message, partial_frame=True))
        return

    # led indicators
    # Get 2 moves from the movestack copy
    move1 = game.move_stack_copy.pop()
    move2 = game.move_stack_copy.pop()

    text = epaper.FrameText(pos=(15, 6), content=''.join([str(move2), str(move1)]), fill=config.WHITE, font=config.FONT_BIG)
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=text, partial_frame=True))

    while True:
        button_panel.wait_for_move()
        if validate_computer_move(game, move1):
            game.board.push(move1)
            break

    while True:
        button_panel.wait_for_move()
        if validate_computer_move(game, move2):
            game.board.push(move2)
            break


def give_hint(game: Game) -> None:
    """Write ponder move on the frame --> frame_player_turn"""
    LOG.debug('BUTTON_EVENT give hint')
    epaper_screen.update_frame(button_panel, epaper.PLAYER_HINT)
    if game.computer_move.ponder is not None:
        text = epaper.get_move_text(game.computer_move.ponder, game.board)
    else:
        text = epaper.FrameText(content='No hint available', pos=(75, 25), fill=config.WHITE, font=config.FONT_BIGGER, align=config.CENTER)

    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=text, partial_frame=True))
    game.hint = True


def show_board(game: Game) -> None:
    """Show complete board on epaper"""
    epaper_screen.update_frame(button_panel, epaper.game_show_board(button_panel, game.board))
    button_panel.execute_task(timeout=60)


# def show_attackers(game: Game) -> None:
#     """
#     Show attackers as a partial display in commander.game_player_turn
#     :param game: Game
#     """
#     LOG.debug('BUTTON_EVENT show attackers')
#     text0 = epaper.FrameText(content='Lift or place a piece...', pos=(15, 6), fill=config.WHITE)
#     epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=text0, partial_frame=True))
#     button_panel.wait_for_reed()
#     square = serial_arduino.new_detected_move()
#     LOG.debug('attackers on square %s', chess.square_name(square))
#     attackers = game.board.attackers(not game.setup.color.value, square)
#     LOG.debug([chess.square_name(item) for item in attackers])
#     text1 = epaper.FrameText(content=''.join(['Square ', chess.square_name(square), ' is attacked by:']), pos=(15, 6), fill=config.WHITE)
#     if attackers:
#         attackers_string = ''.join([chess.square_name(item) + ' ' for item in attackers])
#     else:
#         attackers_string = 'Nobody'
#     text2 = epaper.FrameText(content=textwrap.fill(attackers_string, width=24), pos=(20, 28), fill=config.WHITE)
#     text3 = epaper.FrameText(content='Remove or put piece back', pos=(15, 60), fill=config.WHITE)
#     epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=(text1, text2, text3), partial_frame=True))
#     while True:
#         button_panel.wait_for_reed()
#         incoming_move = serial_arduino.new_detected_move()
#         LOG.debug('not the same square!')
#         if incoming_move != square:
#             validate_board(game)
#         else:
#             epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel=button_panel, content=(text1, text2), partial_frame=True))
#             break


def save_pgn(game: Game, backup=False) -> None:
    """
    Write the pgn notes to file.
    :param game: Game
    :param backup: If set True the file will be placed in a seperate folder
    :return:
    """
    board = game.board
    try:
        board.peek()
    except IndexError:
        return

    if backup:
        path = 'history/{0}_{1}.pgn'.format(
            game.pgn_notes.headers['Event'].strip(), strftime(
                '%d-%m-%Y_%Hh%M', localtime()))
        epaper_screen.update_frame(button_panel, epaper.PGN_SAVED)
    else:
        path = config.SAVEGAME

    files.save_game(path, game.pgn_notes)
    LOG.debug('pgn notes saved')


def engine_stop(game: Game) -> None:
    """make engine stop calculating"""
    LOG.debug('BUTTON_EVENT engine stop')
    if not game.engine.ping():
        game.engine.close()  # TODO check in real-time if this could be use as the equivalent of the UCI 'stop' command and the bestmove is present
        part_frame = epaper.game_computer_turn(button_panel=button_panel, move_text=epaper.get_move_text(game.computer_move.move, game.board),
                                               partial_frame=True)
        epaper_screen.update_frame(button_panel, part_frame)
    else:
        LOG.debug('engine has already stopped')


def back_to_game(game: Game) -> None:
    """
    go back to previous GAME menu:
    - Validate board    OR
    - player turn       OR
    - Computer turn
    """
    LOG.debug('BUTTON_EVENT back to GAME')
    if state.is_set(States.BOARD_INVALID):  # redraw the 'validate board' frame
        current_board = get_board_square_set(game.board)
        incoming_board = chess.SquareSet(squares=serial_arduino.ask_board())
        frame = epaper.game_validate_board(button_panel, "board invalid", current_board, incoming_board, game.board)
        epaper_screen.update_frame(button_panel, frame, important=True)
        serial_arduino.trigger_arduino_int()  # wait again for a reed interrupt

    elif state.is_set(States.PLAYER_TURN):
        engine_info = epaper.game_engine_info(player_turn=True, engine=game.setup.engine)
        epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel))
        epaper_screen.update_frame(button_panel, engine_info, important=False)

    elif state.is_set(States.COMPUTER_TURN):
        engine_info = epaper.game_engine_info(player_turn=False, engine=game.setup.engine)
        epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel=button_panel))
        epaper_screen.update_frame(button_panel, engine_info, important=False)
        if game.computer_move.move:
            new_move = game.computer_move.move
            epaper_screen.update_frame(button_panel, epaper.COMPUTER_CONFIRM)
            epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel=button_panel, move_text=epaper.get_move_text(new_move, game.board), partial_frame=True))

        else:
            epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel=button_panel, move_text=epaper.game_computer_thinking(game.setup), partial_frame=True), important=False)
            # Waiting for player to make computer move
            button_panel.toggle_alarm(active=False)


# ---------------
# -- Main menu --
# ---------------
def show_next_menu_item(game: Game, first=False) -> None:
    """
    Show next option on epaper. Sends a full frame and and a partial_frame
    :param game: Game
    :param first: bool, Set True to start at first menu item
    :return:
    """
    LOG.debug('BUTTON_EVENT Next screen')
    frame = epaper_screen.get_menu_item(first)
    LOG.debug('new MAIN menu frame: %s', frame)
    epaper_screen.update_frame(button_panel, frame(button_panel), important=False)
    epaper_screen.update_frame(button_panel, frame(button_panel, game.setup, partial_frame=True), important=False)


def show_next_engine(game: Game) -> None:
    """Show next engine on epaper"""
    LOG.debug('BUTTON_EVENT Next engine')
    selected_engine = iter(config.ENGINES)
    try:
        game.engine = next(selected_engine)
    except StopIteration:
        selected_engine = iter(config.ENGINES)
        game.engine = next(selected_engine)

    epaper_screen.update_engine_options(game.setup.engine)
    epaper_screen.update_frame(button_panel, epaper.engine_logo(game.setup), important=False)
    epaper_screen.update_frame(button_panel, epaper.main_engine(button_panel, game.setup, partial_frame=True), important=False)
    files.save_setup(game.setup)


def change_option(game: Game, option, adjust, engine_option=False) -> None:
    """
    Adjust option
    :param game: Game
    :param option: config.Option/config.EngineOption from GAME.setup
    :param adjust: 1 or -1
    :param engine_option. Set True is frame is an engine_option
    :return:
    """
    # so far only engine_options use this function...
    LOG.debug('BUTTON_EVENT change option')
    index = option['options'].index(option['value'])
    if index + adjust >= len(option['options']):
        option['value'] = option['options'][0]
    elif index + adjust < 0:
        option['value'] = option['options'][-1]
    else:
        option['value'] = option['options'][index + adjust]

    files.save_setup(game.setup)

    if engine_option:
        part_frame = epaper.main_engine_options(button_panel, option, partial_frame=True)
        epaper_screen.update_frame(button_panel, part_frame, important=False)
    else:
        raise NotImplementedError('change_option: engine_option=False')


def toggle_option(game: Game, option, engine_option=False) -> None:
    """
    Toggle bool value from file. (use change_value for non bool values)
    :param game: Game
    :param option: config.Option/config.EngineOption
    :param engine_option: Set True if the given option is an engine_option
    :return:
    """
    LOG.debug('BUTTON_EVENT toggle file')
    LOG.debug(option)

    option['value'] = not option['value']

    if engine_option:
        part_frame = epaper.main_engine_options(
            button_panel, option, partial_frame=True)

    else:
        if option['id_name'] == 'color':
            part_frame = epaper.main_color(button_panel, game.setup, partial_frame=True)
        elif option['id_name'] == 'markers':
            part_frame = epaper.main_markers(button_panel, game.setup, partial_frame=True)
        elif option['id_name'] == 'mark_last_move':
            part_frame = epaper.main_mark_last_move(button_panel, game.setup, partial_frame=True)
        elif option['id_name'] == 'wait_to_confirm':
            part_frame = epaper.main_wait_for_confirm(button_panel, game.setup, partial_frame=True)
        else:
            LOG.error('toggle option: Unknown option')
            raise ValueError('toggle_option: unknown option')

    files.save_setup(game.setup)
    epaper_screen.update_frame(button_panel, part_frame, important=False)


def restore_defaults(game: Game) -> None:
    """Set all setup to their default value"""
    LOG.debug('BUTTON_EVENT restore default options')
    game.setup = config.DEFAULT_SETUP
    frame = epaper_screen.get_menu_item(first=True)
    epaper_screen.update_frame(button_panel, frame())
    files.save_setup(game.setup)


def led_options(game: Game) -> None:
    """"Menu to change led options during a GAME"""
    LOG.debug('BUTTON_EVENT ingame led options')
    epaper_screen.update_frame(button_panel, epaper.game_led_options(button_panel, game.setup, partial_frame=False))
    epaper_screen.update_frame(button_panel, epaper.game_led_options(button_panel, game.setup, partial_frame=True))


# End functions
# -------------------------------------------------------------------------------------------------
gpio.init()

signal.signal(signal.SIGINT, signal_exit_program)
signal.signal(signal.SIGTERM, signal_exit_program)
signal.signal(signal.SIGALRM, signal_exit_program)

button_panel = button.Panel(callbacks=get_dict_callbacks())
gpio.set_callback(config.ARDUINO_INT_PIN, arduido_interrupt)

epaper_screen = epaper.Screen(
    menu_items=[
        epaper.main_info,
        epaper.main_color,
        epaper.main_engine,
        epaper.main_markers,
        epaper.main_mark_last_move,
        epaper.main_wait_for_confirm,
        epaper.main_defaults
    ])

LOG.debug('waiting for arduino...')
if serial_arduino.say_hello() is True:
    LOG.debug('Arduino found!')
else:
    LOG.critical('Cannot find arduino')
    epaper_screen.clear_screen(message='Critical: cannot find arduino')
    sleep(config.AUTOSHUTDOWN)
    epaper_screen.clear_screen(button_panel, full_refresh=True)
    raise SystemExit(1)

state = State()

if __name__ == '__main__':
    LOG.info('Start program')
    epaper_screen.clear_screen(button_panel, full_refresh=True)
    main_game = Game()
    epaper_screen.update_engine_options(main_game.setup.engine)
    save_file = files.open_saved_game(config.SAVEGAME)
    state.set(States.MAIN)
    if save_file is not None:
        play_game(main_game, saved_game=save_file)

    show_next_menu_item(main_game, first=True)

    while True:
        button_panel.execute_task(timeout=config.AUTOSHUTDOWN)
