#Provide functionality for the server to manage games and associate them with the appropriate players

import game_utilities

class Game:
    def __init__(self, creator_username, invited_username):
        """Used to manage a single game"""
        self.creator_username = creator_username
        self.invited_username = invited_username
        self.players = [creator_username, invited_username]
        self.board = [' ' for _ in range(9)]
        self.current_turn = creator_username

        if self.current_turn not in self.players:
            raise ValueError("Invalid current turn")

    def compute_player_piece(self, username: str):
        """Compute the game piece for the specified player"""
        return 'X' if username == self.creator_username else 'O'

    def compute_player_outcome(self, victory_condition: str, username: str):
        if victory_condition == self.compute_player_piece(username):
            return game_utilities.VICTORY
        elif victory_condition == game_utilities.TIE:
            return game_utilities.TIE
        else:
            return game_utilities.LOSS

    def make_move(self, username, move):
        if username != self.current_turn:
            return False
        move_index = int(move) - 1
        if self.board[move_index] != ' ':
            return False
        self.board[move_index] = 'X' if username == self.creator_username else 'O'
        self.switch_turns()
        return True
    
    def get_current_turn(self):
        return self.current_turn
    
    def switch_turns(self):
        self.current_turn = self.players[0] if self.current_turn == self.players[1] else self.players[1]

    def check_winner(self):
        return game_utilities.determine_outcome(self.board)

    def is_over(self):
        return self.check_winner() is not None

    def compute_text(self):
        return "".join(self.board)

    def compute_other_player(self, username):
        if username == self.creator_username:
            return self.invited_username
        return self.creator_username

class GameHandler:
    """Used to associate games with the corresponding players"""
    def __init__(self):
        self.games = {}

    def _should_create_game_with_id(self, game_id):
        return game_id not in self.games or self.games[game_id].is_over()

    def create_game(self, creator_username, invited_username):
        game_id = self.sorted_game_id(creator_username, invited_username)
        if self._should_create_game_with_id(game_id):
            self.games[game_id] = Game(creator_username, invited_username)
            return game_id
        return False

    def get_game(self, username1, username2):
        game_id = self.sorted_game_id(username1, username2)
        return self.games.get(game_id)

    def game_exists(self, username1, username2):
        game_id = self.sorted_game_id(username1, username2)
        return game_id in self.games
    
    def sorted_game_id(self, username1, username2):
        """Make sure the game is accessible using a single string regardless of which player is the first in the calculation by using the result of sorting the usernames"""
        return ' '.join(sorted([username1, username2]))
