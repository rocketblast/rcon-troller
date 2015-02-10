import re
from collections import OrderedDict


class CommandValidator():
    _commands = list()
    _command_pattern = None

    def __init__(self, commands=None):
        if commands:
            CommandValidator.register_commands(commands, True)
        else:
            raise Exception('Must specify at least 1 command')

    @classmethod
    def register_commands(cls, commands, replace=False):
        if commands not in cls._commands:
            cls._commands += commands
            cls._command_pattern = re.compile(r'(^[ ]*(?P<token>[!/])[ ]*(?P<command>{0})([ ]|$))|(([\'"]+)?(?P<argument>(?(6)[^\'"]|[^ ])+)(?(6)[\'"]+)?)'.format('|'.join(cls._commands)))

    @classmethod
    def validate(cls, message):
        command_match = CommandValidator._command_pattern.match(message)

        if command_match and command_match.group('command'):
            argument_match = re.finditer(CommandValidator._command_pattern, message)
            arguments = OrderedDict()
            for i, m in enumerate(argument_match):
                if m.group('argument'):
                    arguments.update({'argument{0}'.format(i): m.group('argument')})

            return CommandMatch(True, command_match.group('command'), 'public' if command_match.group('token') == '!' else 'private', arguments)

        return CommandMatch()


class CommandMatch():
    def __init__(self, is_command=False, command=None, visibility='public', arguments=OrderedDict()):
        self.is_command = is_command
        self.command = command
        self.visibility = visibility
        self.arguments = arguments
