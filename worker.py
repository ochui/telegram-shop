import multiprocessing
import telegram
import strings
import configloader
import sys

# Load the configuration
config = configloader.load_config()

class StopSignal:
    """A data class that should be sent to the worker when the conversation has to be stopped abnormally."""

    def __init__(self, reason: str=""):
        self.reason = reason


class ChatWorker:
    """A worker for a single conversation. A new one should be created every time the /start command is sent."""

    def __init__(self, bot: telegram.Bot, chat: telegram.Chat):
        # A pipe connecting the main process to the chat process is created
        out_pipe, in_pipe = multiprocessing.Pipe(duplex=False)
        # The sending pipe is stored in the ChatWorker class, allowing the forwarding of messages to the chat process
        self.pipe = in_pipe
        # A new process running the conversation handler is created, and the receiving pipe is passed to its arguments to enable the receiving of messages
        self.process = multiprocessing.Process(target=conversation_handler, args=(bot, chat, out_pipe))

    def start(self):
        """Start the worker process."""
        self.process.start()

    def stop(self, reason: str=""):
        """Gracefully stop the worker process"""
        # Send a stop message to the process
        self.pipe.send(StopSignal(reason))
        # Wait for the process to stop
        self.process.join()

# TODO: maybe move these functions to a class

def graceful_stop(bot: telegram.Bot, chat: telegram.Chat, pipe):
    """Handle the graceful stop of the process."""
    # Notify the user that the session has expired
    bot.send_message(chat.id, strings.conversation_expired)
    # End the process
    sys.exit(0)

def receive_next_update(bot: telegram.Bot, chat: telegram.Chat, pipe) -> telegram.Update:
    """Get the next update from a pipe.
    If no update is found, block the process until one is received.
    If a stop signal is sent, try to gracefully stop the process."""
    # Wait until some data is present in the pipe or the wait time runs out
    if not pipe.poll(int(config["Telegram"]["conversation_timeout"])):
        # If the conversation times out, gracefully stop the process
        graceful_stop(bot, chat, pipe)
    # Receive data from the pipe
    data = pipe.recv()
    # Check if the data is a stop signal instance
    if isinstance(data, StopSignal):
        # Gracefully stop the process
        graceful_stop(bot, chat, pipe)
    # Return the received update
    return data


def conversation_handler(bot: telegram.Bot, chat: telegram.Chat, pipe):
    """This function is ran once for every conversation (/start command) by a separate process."""
    # TODO: catch all the possible exceptions
    # Welcome the user to the bot
    bot.send_message(chat.id, strings.conversation_after_start)
    # TODO: Send a command list or something
    while True:
        # For now, echo the sent message
        update = receive_next_update(bot, chat, pipe)
        bot.send_message(chat.id, f"{multiprocessing.current_process().name} {update.message.text}")