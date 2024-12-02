from game_utilities import *

import unittest

def compute_flipped_board(board):
    flip = ""
    for character in board:
        flipped_character = ' '
        if character == 'X':
            flipped_character = 'O'
        elif character == 'O':
            flipped_character = 'X'
        flip += flipped_character
    return flip



class EndingTestCase(unittest.TestCase):
    def _assert_victory(self, board):
        self.assertEqual(determine_outcome(board), 'X')
        flipped_board = compute_flipped_board(board)
        self.assertEqual(determine_outcome(flipped_board), 'O')

    def _assert_conditions_match(self, board, condition):
        self.assertEqual(determine_outcome(board), condition)
        flipped_board = compute_flipped_board(board)
        self.assertEqual(determine_outcome(flipped_board), condition)

    def _assert_tie(self, board):
        self._assert_conditions_match(board, 'T')

    def _assert_unfinished(self, board):
        self._assert_conditions_match(board, None)

    def test_empty_board(self):
        expected = None
        actual = determine_outcome(' '*9)
        self.assertEqual(expected, actual)

    def test_first_row(self):
        board = 'X'*3 + 'OO' + ' '*4
        self._assert_victory(board)

    def test_second_row(self):
        board = 'OO ' + 'X'*3 + ' '*3
        self._assert_victory(board)

    def test_last_row(self):
        board = 'OO ' + ' '*3 + 'X'*3
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