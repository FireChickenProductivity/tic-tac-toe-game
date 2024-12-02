# Provide utility constants and functions for dealing with the tictactoe game

VICTORY = "W"
LOSS = "L"
TIE = "T"
X_PIECE = "X"
O_PIECE = "O"
EMPTY_POSITION = " "

def is_valid_move_text(text: str):
    return len(text) == 2 and text[0].lower() in 'abc' and text[1] in '123'

def convert_move_text_to_move_number(text: str):
    letter = text[0].lower()
    number = int(text[1])
    if letter == 'b':
        number += 3
    elif letter == 'c':
        number += 6
    return number

def compute_current_player(game_state: str) -> str:
    """Determines the current player based on game state."""
    x_moves = game_state.count(X_PIECE)
    o_moves = game_state.count(O_PIECE)
    return X_PIECE if x_moves == o_moves else O_PIECE

def compute_other_piece(piece: str):
    return X_PIECE if piece == O_PIECE else O_PIECE

def determine_outcome(board):
    """If the game is still going, return None. Otherwise, return the outcome as a value representing ties on a tie or the piece of the winner if someone won"""
    winning_combos = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for combo in winning_combos:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] != EMPTY_POSITION:
            return board[combo[0]]
    if EMPTY_POSITION not in board:
        return TIE
    return None