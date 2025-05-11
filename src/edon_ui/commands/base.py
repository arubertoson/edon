from typing import Any, Protocol

class Command(Protocol):
    def execute(self, context: Any = None) -> bool:
        ...

class ContextProvider(Protocol):
    def get_command_context(self, command_name: str) -> Any:
        ...

class CommandRegistry:
    def __init__(self):
        self.commands: dict[str, Command] = {}

    def register(self, name: str, command: Command) -> None:
        self.commands[name] = command

    def execute(self, name: str, context: Any = None) -> bool:
        if name in self.commands:
            return self.commands[name].execute(context)
        import loguru
        loguru.logger.warning(f"Attempted to execute unknown command: {name}")
        return False 