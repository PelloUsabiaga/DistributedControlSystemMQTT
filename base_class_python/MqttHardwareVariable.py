from abc import ABCMeta, abstractmethod
from typing import Union
from base_class_python.MonitorType import MonitorType

class MqttHardwareVariable(metaclass = ABCMeta):
    """
    This is the abstract base class from which any hardware variable should inherit. It have some abstract
    methods, which will be called during program execution, and where all the user programmable logic should
    be.

    Response tuples are tuples with the response code, DONE, ERROR or NACK, and the list of the response 
    parameters. For example, ("DONE",[3.14,"pi"]) or 
    ("ERROR",["The value -100 is outside the alowed values for the variable Temperature."])
    """

    @abstractmethod
    def get_put_argument_number(self) -> list[int]:
        """
        It should return a list with all the suported PUT arguments. For example, if both 1 or 2 arguments
        are suported for the PUT command, it should return [1, 2].
        If the PUT command is not supported for this variable, it should return [-1].
        """
        pass

    @abstractmethod
    def handle_put_command(self, argument_list: list) -> tuple[str, list[Union[str, int, float]]]:
        """
        Write there the logic to handle PUT commands. It should return a response tuple.
        """
        pass

    @abstractmethod
    def handle_get_command(self) -> tuple[str, list[str]]:
        """
        Write there the logic to handle GET commands. It should return a response tuple.
        """
        pass

    @abstractmethod
    def handle_start_monitor_request_command(self, mode: MonitorType, period: float) -> bool:
        """
        This method is called anytime that a new MONITOR command is received. Any restrictions to MONITOR commands can be implemented
        here.
        """
        pass

    @abstractmethod
    def handle_info_command(self) -> dict[str, str]:
        """
        Write there the logic to handle INFO commands. It should return a dict of string to string pairs, for each info field you want.
        If any of the default fields is overrided, the user programmed one have priority.
        The default fields are the following:
            -HostIp
            -VariableName
            -AppName
        Some suggested fields for standarization are the following:
            -Unit
            -SuportedCommands
            -Info
        """
        pass

    @abstractmethod
    def get_measurement_for_monitor(self, delta_time: float) -> Union[int, float, str]:
        """
        Each time a new measurement is needed from a monitor thread, this method will be called. 
        """
        pass

    @abstractmethod
    def get_variable_name(self) -> str:
        """
        The variable name will define which MQTT topic will be used for commands, responses and data of this variable.
        """
        pass

    @abstractmethod
    def stop_variable(self) -> None:
        """
        Make shure to call any closeup logic for your hardware here.
        """
        pass