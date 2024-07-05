# -*- coding: utf-8 -*-
"""

@author: Pello Usabiaga
"""


from collections.abc import Callable, Iterable, Mapping
import time
from threading import Thread
from typing import Any
from typing import Union


import base_class_python.DateUtility as DateUtility

from base_class_python.MqttHardwareVariable import MqttHardwareVariable
from base_class_python.MqttConnection import MqttConnection
from base_class_python.MonitorType import MonitorType
from base_class_python.MqttLogger import MqttLogger, MqttLogPriority


class MqttMonitorThread(Thread):
    """
    Class that inerits from Thread. It communicates with a MqttHardwareVariable, 
    to monitor its value in the way it have been configured trought commands.
    """

    def __init__(self, monitored_variable: MqttHardwareVariable, connection: MqttConnection, logger: MqttLogger, topic_origin: str="",
                 group: None = None, target: Union[Callable[..., object], None] = None, 
                 name: Union[str, None] = None, args: Iterable[Any] = ..., kwargs: Union[Mapping[str, Any], None] = None, *, 
                 daemon: Union[bool, None] = None) -> None:
        super().__init__(group, target, name, args, kwargs, daemon=daemon)

        self.daemon = True

        self._should_run = True

        self._connection = connection
        self._logger = logger

        self._monitored_variable = monitored_variable
        self._monitor_topic = topic_origin + "data/{}".format(self.get_monitored_variable_name())

        self._last_measurement = None
        self._previous_measurement = None
        self._last_measurement_time = time.time()

        self._mode = MonitorType.inactive
        self._period = None
        self._send_monitor_data = False

        self.name = "{} thread".format(self.get_monitored_variable_name())
  
  
    def run(self):
        """
        The method that is runned when the thread is alive. It periodically checks for data to be send to MQTT.
        """
        current_iteration_start_time = time.time()
        while self._should_run:
            if self._send_monitor_data:
                if self._mode == MonitorType.periodic:
                    self._connection.send_single_mqtt_message(self._monitor_topic, '{};{}'.format(str(self._get_measurement()), DateUtility.get_date_string()), retain=True)

                elif self._mode == MonitorType.change:
                    self._get_measurement()
                    if self._previous_measurement != self._last_measurement:
                        self._connection.send_single_mqtt_message(self._monitor_topic, '{};{}'.format(str(self._last_measurement), DateUtility.get_date_string()), retain=True)
                else:
                    raise ValueError("_mode should never be {}, it can only be 'periodic' or 'change'.".format(self._mode))
                
                currently_erased_time = time.time() - current_iteration_start_time
                try:
                    time_to_sleep = self._period - currently_erased_time
                except TypeError:
                    # this means that _period is None, because the monitor have been stoped inside the loop.
                    time_to_sleep = 0

                if time_to_sleep < 0:
                    self._logger.log("Overrun in monitor thread handling variable {}".format(self.get_monitored_variable_name()), sender_name=self.get_monitored_variable_name(), priority=MqttLogPriority.INFO)
                    current_iteration_start_time = time.time()
                    continue

                time.sleep(time_to_sleep)
                try:
                    current_iteration_start_time += self._period
                except TypeError:
                    # this means that _period is None, because the monitor have been stoped inside the loop.
                    current_iteration_start_time = time.time()
            else:
                time.sleep(0.1)
                current_iteration_start_time = time.time()



    def start_monitor(self, mode: Union[MonitorType, str], period: float) -> None:
        """
        Start monitoring the threads variable with the specified mode and period.

        Raises ValueError.
        """

        if type(mode) == str:
            mode = MonitorType.from_string(mode)

        if period != None and period <= 0:
            raise ValueError("Period should be None or a positive float.")
        
        if mode == MonitorType.periodic:
            self._mode = MonitorType.periodic
            self._period = period
        elif mode == MonitorType.change:
            self._mode = MonitorType.change
            self._period = period
        else:
            raise ValueError("Monitor mode {} not supported. Use 'periodic' or 'change' only.".format(mode))

        self._send_monitor_data = True

    def stop_monitor(self) -> None:
        self._mode = MonitorType.inactive
        self._period = None
        self._send_monitor_data = False

    def _get_measurement(self) -> Union[int, float, str]:
        self._previous_measurement = self._last_measurement

        now = time.time()
        delta_time = now - self._last_measurement_time
        self._last_measurement_time = now

        self._last_measurement = self._monitored_variable.get_measurement_for_monitor(delta_time)
        return self._last_measurement
    
    def get_monitored_variable_name(self) -> str:
        return self._monitored_variable.get_variable_name()

    
    def stop_thread(self):
        """
        To be called at program ending.
        """
        self._should_run = False