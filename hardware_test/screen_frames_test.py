#!/usr/bin/env python3
"""
# ############################################### #
# SCRIPT TO SHOW FRAMES ON THE EPAPER FOR TESTING #
# ############################################### #
"""

from functools import partial
from main import *

OFF = False
ON = True

game = Game()


def stop(sig=None, frame=None):
    # epaper_screen.sleep()
    # gpio.GPIO.cleanup()
    raise SystemExit(0)


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

State.set(States.MAIN)


# ###########
# TEST HERE #
# ###########
def test_frame_main_info():
    epaper_screen.update_frame(button_panel, epaper.main_info(button_panel), important=True)
    epaper_screen.update_frame(button_panel, epaper.main_info(button_panel, game.setup, partial_frame=True), important=True)


def test_frame_main_color():
    epaper_screen.update_frame(button_panel, epaper.main_color(button_panel, game.setup, partial_frame=False), important=True)
    epaper_screen.update_frame(button_panel, epaper.main_color(button_panel, game.setup, partial_frame=True), important=True)


def test_frame_main_engine():
    epaper_screen.update_frame(button_panel, epaper.main_engine(button_panel, setup=game.setup, partial_frame=False))
    for engine in config.ENGINES:
        game.setup.engine = engine
        epaper_screen.update_frame(button_panel, epaper.main_engine(button_panel, game.setup, partial_frame=True), important=True)
        sleep(2)


def test_frame_main_markers():
    epaper_screen.update_frame(button_panel, epaper.main_markers(button_panel, game.setup, partial_frame=False))
    epaper_screen.update_frame(button_panel, epaper.main_markers(button_panel, game.setup, partial_frame=True), important=False)


def test_frame_main_mark_last_move():
    epaper_screen.update_frame(button_panel, epaper.main_mark_last_move(button_panel, game.setup, partial_frame=False))
    epaper_screen.update_frame(button_panel, epaper.main_mark_last_move(button_panel, game.setup, partial_frame=True), important=False)


def test_frame_main_wait_for_confirm():
    epaper_screen.update_frame(button_panel, epaper.main_wait_for_confirm(button_panel, game.setup, partial_frame=False))
    epaper_screen.update_frame(button_panel, epaper.main_wait_for_confirm(button_panel, game.setup, partial_frame=True), important=False)


def test_frame_main_defaults():
    epaper_screen.update_frame(button_panel, epaper.main_defaults(button_panel))


def test_frame_player_turn():
    """Simulate player actions during his turn"""
    board = chess.Board()
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel))
    epaper_screen.update_frame(button_panel, epaper.game_engine_info(player_turn=True, engine=game.setup.engine))
    # waiting for move
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel, content=epaper.PLAYER_WAIT, partial_frame=True))
    sleep(3)
    # pseudo move + pseudo list with legal moves
    from_square = 12
    to_square = 28
    validate_player_move(game, from_square, set(board.legal_moves))
    sleep(3)
    # finished move
    validate_player_move(game, to_square, set(board.legal_moves))
    epaper_screen.update_frame(button_panel, epaper.PLAYER_CONFIRM)
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel, content=epaper.PLAYER_MOVE_CONFIRMED, partial_frame=True))


def test_frame_computer_turn():
    epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel))
    epaper_screen.update_frame(button_panel, epaper.game_engine_info(player_turn=False, engine=game.setup.engine))
    epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel, move_text=epaper.game_computer_thinking(game.setup), partial_frame=True))
    sleep(3)
    board = chess.Board()
    board.push(chess.Move.from_uci('e2e4'))
    example_move = chess.Move.from_uci('e7e5')
    epaper_screen.update_frame(button_panel, epaper.game_computer_turn(button_panel, move_text=epaper.get_move_text(example_move, board), partial_frame=True))
    epaper_screen.update_frame(button_panel, epaper.COMPUTER_CONFIRM)


def test_give_hint():
    # Make example ponder move
    game.board = chess.Board()
    game.setup = config.DEFAULT_SETUP
    game.engine = chess.engine.SimpleEngine.popen_uci(game.setup.engine.path)
    game.computer_move = game.engine.play(game.board, chess.engine.Limit(time=1), ponder=True)
    game.board.push(game.computer_move.move)
    epaper_screen.update_frame(button_panel, epaper.game_player_turn(button_panel))
    give_hint(game)


def test_validate_board():
    game.board = chess.Board(fen='3qk3/8/8/8/8/8/7P/4KB2 b KQkq e3 0 1')
    current_board = get_board_square_set(game.board)
    incoming_board = get_board_square_set(chess.Board(fen='3q4/8/8/8/8/8/7P/4K3 b KQkq e3 0 1'))
    epaper_screen.update_frame(button_panel, epaper.game_validate_board(button_panel, 'Board invalid!', current_board, incoming_board, game.board))


def test_frame_end_game():
    game.board = chess.Board()
    game.board.push(chess.Move.from_uci('e2e4'))
    test_result_draw = '*'
    epaper_screen.update_frame(button_panel, epaper.end_game(button_panel, result=test_result_draw, setup=game.setup, board=game.board))
    sleep(3)
    test_result_draw = '1/2-1/2'
    epaper_screen.update_frame(button_panel, epaper.end_game(button_panel, result=test_result_draw, setup=game.setup, board=game.board))
    sleep(3)
    test_result_black = '0-1'
    epaper_screen.update_frame(button_panel, epaper.end_game(button_panel, result=test_result_black, setup=game.setup, board=game.board))
    sleep(3)
    test_result_white = '1-0'
    epaper_screen.update_frame(button_panel, epaper.end_game(button_panel, result=test_result_white, setup=game.setup, board=game.board))
    sleep(3)


def test_frame_question():
    epaper_screen.update_frame(button_panel, epaper.question(button_panel, line='[Insert question here]'))


def test_show_board():
    game.board = chess.Board(fen='2Nqk3/8/2N5/8/8/8/5PPP/4KB2 b KQkq e3 0 1')
    epaper_screen.update_frame(button_panel, epaper.game_show_board(button_panel, game.board))


def test_frame_main_engine_options():
    game.setup = config.DEFAULT_SETUP
    for _, item in game.setup.engine.options.items():
        epaper_screen.update_frame(button_panel, epaper.main_engine_options(button_panel, item, partial_frame=False))
        epaper_screen.update_frame(button_panel, epaper.main_engine_options(button_panel, item, partial_frame=True))
        sleep(3)


def test_rodent_personality(full=False):
    if not full:
        option = config.RODENT.options['level']
        epaper_screen.update_frame(epaper.main_engine_options(button_panel, option, partial_frame=False))
    else:
        for conf in config.RODENT_PERSONALIIES:
            if conf.active == '1':
                option = config.Option('PersonalityFile', value=conf)
                epaper_screen.update_frame(button_panel, epaper.main_engine_options(button_panel, option, partial_frame=False))
            sleep(2)


def test_game_led_options():
    game.setup = config.DEFAULT_SETUP
    epaper_screen.update_frame(button_panel, epaper.game_led_options(button_panel, game.setup, partial_frame=False))
    epaper_screen.update_frame(button_panel, epaper.game_led_options(button_panel, game.setup, partial_frame=True))


tests = (
    test_frame_main_engine,
    test_frame_main_engine_options,
    test_frame_main_info,
    test_frame_main_color,
    test_frame_main_markers,
    test_frame_main_mark_last_move,
    test_frame_main_wait_for_confirm,
    test_frame_main_defaults,
    test_frame_player_turn,
    test_frame_computer_turn,
    test_show_board,
    test_give_hint,
    test_frame_end_game,
    test_validate_board,
    test_frame_question,
    partial(test_rodent_personality, full=True),
    test_game_led_options,
)
# ADD TESTS HERE ###############
# ##############################

epaper_screen.clear_screen(full_refresh=True)
for test in tests:
    test()
    sleep(3)
print(gpio.mcp23s17_read_register(gpio.GPIOB))
# button_panel.clear_butons()
# epaper_screen.clear_screen(message='The End')
print('DONE!')
stop()
