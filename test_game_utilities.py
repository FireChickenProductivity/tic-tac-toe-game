#Automated tests for the game utilities file

from game_utilities import *

import unittest

def compute_flipped_board(board):
    """Computes the board with pieces swapped between the player"""
    flip = ""
    for character in board:
        flipped_character = EMPTY_POSITION
        if character == X_PIECE:
            flipped_character = O_PIECE
        elif character == O_PIECE:
            flipped_character = X_PIECE
        flip += flipped_character
    return flip



class EndingTestCase(unittest.TestCase):
    #Utility methods
    def _assert_victory(self, board):
        """Assert that player X wins on the board and player O wins on the flipped board"""
        self.assertEqual(determine_outcome(board), X_PIECE)
        flipped_board = compute_flipped_board(board)
        self.assertEqual(determine_outcome(flipped_board), O_PIECE)

    def _assert_conditions_match(self, board, condition):
        """Assert that the same condition happens on the board and the flipped board"""
        self.assertEqual(determine_outcome(board), condition)
        flipped_board = compute_flipped_board(board)
        self.assertEqual(determine_outcome(flipped_board), condition)

    def _assert_tie(self, board):
        self._assert_conditions_match(board, 'T')

    def _assert_unfinished(self, board):
        self._assert_conditions_match(board, None)

    def test_empty_board(self):
        expected = None
        actual = determine_outcome(EMPTY_POSITION*9)
        self.assertEqual(expected, actual)

    def test_first_row(self):
        board = X_PIECE*3 + 'OO' + EMPTY_POSITION*4
        self._assert_victory(board)

    def test_second_row(self):
        board = 'OO ' + X_PIECE*3 + EMPTY_POSITION*3
        self._assert_victory(board)

    def test_last_row(self):
        board = 'OO ' + EMPTY_POSITION*3 + X_PIECE*3
        self._assert_victory(board)

    def test_first_column(self):
        board = 'XO XO X  '
        self._assert_victory(board)

    def test_second_column(self):
        board = ' XO XO X  '
        self._assert_victory(board)

    def test_last_column(self):
        board = ' OX OX  X'
        self._assert_victory(board)

    def test_top_left_to_bottom_right_diagonal(self):
        board = 'XOO X   X'
        self._assert_victory(board)

    def test_bottom_left_to_top_right_diagonal(self):
        board = 'OOX X X  '
        self._assert_victory(board)

    def test_simple_tie(self):
        board = 'XOXOOXXXO'
        self._assert_tie(board)

    def test_unfinished(self):
        first_turn = 'X        '
        self._assert_unfinished(first_turn)
        second_turn = 'XO       '
        self._assert_unfinished(second_turn)
        third_turn = 'XOX      '
        self._assert_unfinished(third_turn)
        fourth_turn = 'XOXO     '
        self._assert_unfinished(fourth_turn)
        fifth_turn = 'XOXOX    '
        self._assert_unfinished(fifth_turn)
        sixth_turn = 'XOXOXO   '
        self._assert_unfinished(sixth_turn)

if __name__ == '__main__':
    unittest.main()