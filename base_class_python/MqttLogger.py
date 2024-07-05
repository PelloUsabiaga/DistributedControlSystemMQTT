import base_class_python.DateUtility as DateUtility
from enum import Enum

class MqttLogPriority(Enum):
    CRITICAL=0
    ERROR=10
    WARN=30
    INFO=40
    DEBUG=50
    NOTSET=100


class MqttLogger:

    def __init__(self) -> None:
        self._connection_loaded = False

    def load_connection(self, connection):
        self._connection = connection
        self._connection_loaded = True


    def log(self, message: str, sender_name: str, priority: int=MqttLogPriority.NOTSET):
        """
        There the logging mechanism can be changed. Priority is higher for smaller numbers. Priority 0 is the bigger priority.
        """
        print("[{}][{}][{}]: {}".format(sender_name, priority, DateUtility.get_date_string(), message))
        if self._connection_loaded:
            self._connection.send_single_mqtt_message("log/{}".format(sender_name), "{};{};{}".format(priority, DateUtility.get_date_string(), message))