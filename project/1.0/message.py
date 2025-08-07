from enum import Enum

class MessageType(Enum):
    REGISTER = 0
    GROUP_SELECTION = 1
    ERROR = 2
    CHALLENGE = 3
    AUTH_REQUEST = 4
    AUTH_RESPONSE = 5
    ACCEPTED = 6
    REJECTED = 7
    REGISTERED = 8
    ASSOCIATE_REQUEST = 0
    # More...


class ErrorType(Enum):
    USERNAMEALEARYEXISTS = 0
    USERNAMENOTFOUND = 1
    UNKNOWNERROR = 2

    @staticmethod
    def message(val): 
        messages = {
            ErrorType.USERNAMEALEARYEXISTS.value: "Username already exists.",
            ErrorType.UNKNOWNERROR.value: "An unknown error occurred."
        }
        return messages.get(val, "Unknown error type.")

