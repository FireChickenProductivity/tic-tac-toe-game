HELP_MESSAGES = {
    "": "Help topics include:\nregister\nlogin\ncreate-game\njoin-game\nmove\nquit\n\nType 'help' followed by the command you would like more information about.",
    "register": "Upon successfully connecting to the server, you must register an account. To do this, type 'register' followed by your chosen username and password into the terminal, seperated by spaces.",
    "login": "After you have created an account, you will need to login. Type 'login' followed by your registered username and password into the terminal, seperated by spaces.",
    "create-game": "To create a new game, type 'create' into the terminal followed by the username of your opponent.",
    "join-game": "To join someone else's game, type 'join' followed by your opponent's username.",
    "move": "To make a move, choose a space on the board and find it's corresponding coordinate. The columns are designated by 'a', 'b', or 'c'. The rows are '1', '2', or '3'. An example coordinate would be 'b3'. Type 'move' followed by the chosen coordinate into the terminal to make your move. You can only make a move on empty spaces.",
    "quit": "To quit a game, enter 'quit' into the terminal."
}

def create_help_message(label):
    if label in HELP_MESSAGES:
        text = HELP_MESSAGES[label]
    else:
        text = f"Did not recognize help topic {label}!\n{HELP_MESSAGES['']}"
    return text