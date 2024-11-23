class CommandResult:
    def __init__(self, feedback: str, message=None):
        self.feedback = feedback
        self.message = message
    
    def has_message(self):
        return self.message is not None
    
    def get_message(self):
        return self.message

    def has_feedback(self):
        return self.feedback is not None

    def get_feedback(self):
        return self.feedback

class Command:
    def __init__(self, client, name: str, help_message: str, pre_command_validate, action):
        self.client = client
        self.name = name
        self.help_message = help_message
        self.pre_command_validate = pre_command_validate
        self.action = action
    
    def _handle_result(self, result):
        if result.has_feedback():
            self.client.output_text(result.get_feedback() + "\n" + self.get_help_message())
        if result.has_message():
            self.client.send_message(result.get_message())

    def perform_command(self, values):
        parsed_values = self.pre_command_validate(values)
        result = self.action(parsed_values)
        self._handle_result(result)
    
    def get_name(self):
        return self.name
    
    def get_help_message(self):
        return self.help_message