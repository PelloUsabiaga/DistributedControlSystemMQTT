import json
import socket
import sys
import time
from typing import Callable, Union

from base_class_python.MqttConnection import MqttConnection
from base_class_python.MqttMonitorThread import MqttMonitorThread
from base_class_python.MqttHardwareVariable import MqttHardwareVariable
from base_class_python.MqttParser import MqttParser
from base_class_python.MonitorType import MonitorType
from base_class_python.MqttLogger import MqttLogger, MqttLogPriority

import base_class_python.DateUtility as DateUtility

class MqttHardwareServer:
    """
    Main class of a program that handles MqttHardwareVariables.
    """

    def __init__(self, name: str, hardware_variable_list: list[MqttHardwareVariable], mqtt_broker_ip: str, 
                 mqtt_broker_port: int=1883, topic_origin: str="", function_at_close: Callable=lambda:None, username: str | None=None, password: str | None=None):
        
        self._init_class_defaults()
        
        self._run_main_thread = True

        self._name = name

        self._function_at_close = function_at_close

        self._topic_origin = topic_origin
        self._reconections = -1

        self._parser = MqttParser(topic_origin=self._topic_origin)

        self._logger = MqttLogger()

        self._connection = MqttConnection(self._mqtt_message_handler, 
                                            self._mqtt_on_connect_handler,
                                            terminate_program_function=self.close_program,
                                            mqtt_broker_ip=mqtt_broker_ip,
                                            mqtt_broker_port=mqtt_broker_port,
                                            username=username,
                                            password=password,
                                            logger = self._logger,
                                            name_for_connection = self._name)
        
        self._logger.load_connection(connection=self._connection)
        

        self._hardware_variable_list: list[MqttHardwareVariable] = []
        self._monitor_thread_list: list[MqttMonitorThread] = []

        for variable in hardware_variable_list:
            self.add_hardware_variable(variable)


    def run_forever(self):
        """
        The server works without calling this, but fun_forever enshures that the program will end up correctly, closeing all the threads.
        """
        try:
            while self._run_main_thread:
                time.sleep(0.1)
            
            sys.exit(1)
        except KeyboardInterrupt:
            self.close_program(0)
            sys.exit(0)
            


    def add_hardware_variable(self, hardware_variable: MqttHardwareVariable):

        self._hardware_variable_list.append(hardware_variable)

        command_topic = self._topic_origin + "commands/{}".format(hardware_variable.get_variable_name())
        self._connection.subscribe(command_topic)

        monitor_thread = MqttMonitorThread(monitored_variable=hardware_variable,
                                            connection=self._connection,
                                            topic_origin=self._topic_origin,
                                            logger=self._logger)

        self._monitor_thread_list.append(monitor_thread)
        monitor_thread.start()


    def get_server_name(self):
        return self._name
    
    def get_logger(self) -> MqttLogger:
        return self._logger
        

    def _mqtt_on_connect_handler(self, client, userdata, flags, rc):
        while self._logger == None:
            pass
        self._logger.log("Connected with result code "+str(rc), sender_name=self.get_server_name(), priority=MqttLogPriority.INFO)
        self._reconections = self._reconections + 1
        
    
    def _mqtt_message_handler(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        response_topic = topic.replace('commands', 'responses')
        self._logger.log("Message recived in topic: {}, payload: {}".format(topic, payload), sender_name=self.get_server_name(), priority=MqttLogPriority.INFO)
        
        try:
            (command_name, command_type, command_id, parameters) = self._parser.parse_mqtt_command(topic, payload)
        except ValueError as error:
            self._connection.send_response(response_topic, 'NACK', 'no_id', [str(error)], topic, payload)
            return
        
        (response_code, response_list) = self._handle_command(command_name, command_type, parameters)
        self._connection.send_response(response_topic, response_code, command_id, response_list, topic, payload)


    def close_program(self, exit_code=1):
        """
        Make shure that this method is called at program ending, if not, some threads will be alive.
        """
        self._logger.log("Program ending...", self._name, MqttLogPriority.INFO)
        self._connection.close_connection()
        for monitor_thread in self._monitor_thread_list:
            monitor_thread.stop_thread()
        
        for variable in self._hardware_variable_list:
            variable.stop_variable()
        
        self._function_at_close()
        self._run_main_thread = False
        sys.exit(exit_code)

    
    def _handle_command(self, variable_name: str, command_type: str, parameters: list) -> tuple[str, list[Union[int, float, str]]]:
        """
        Method to handle incomming commands to the server. The integrity checking is made, 
        the command is parsed, and if everithing is correct, the command is passed to the variable to be processed.
        """
        target_variable = next((variable for variable in self._hardware_variable_list if variable.get_variable_name() == variable_name), None)
        if target_variable == None:
            return ('ERROR', ["Variable {} not found.".format(variable_name)])

        if command_type == 'GET':
            return target_variable.handle_get_command()
        
        elif command_type == 'PUT':
            argument_number = target_variable.get_put_argument_number()
            if argument_number == [-1]:
                return ('ERROR', ["{} variable does not support PUT commands.".format(target_variable.get_variable_name())])
            
            if len(parameters) not in argument_number:
                return ('ERROR', ["Incorrect argument number {} for variable {}. Argument number should be in {}.".format(len(parameters), variable_name, target_variable.get_put_argument_number())])
            return target_variable.handle_put_command(parameters)
        
        elif command_type == 'INFO':
            user_configured_dict = target_variable.handle_info_command()

            default_dict = {"HostIp" : self._get_ip(),
                            "VariableName" : target_variable.get_variable_name(),
                            "AppName" : sys.argv[0]}
            
            default_dict.update(user_configured_dict)

            return ("DONE", [json.dumps(default_dict)])
        

        elif command_type == 'MONITOR':
            target_thread = next((thread for thread in self._monitor_thread_list if thread.get_monitored_variable_name() == variable_name), None)
            if target_thread == None:
                return ('ERROR', ["Variable {} have not monitor thread.".format(variable_name)])
            if len(parameters) not in (1, 2, 3):
                return ('ERROR', ["Monitor command only acepts 1, 2 or 3 parameters."])
            
            if parameters[0] == 1:
                if len(parameters) == 3:
                    try:
                        mode = MonitorType.from_string(parameters[1])
                    except ValueError as e:
                        return ('ERROR', [str(e)])
                    period = float(parameters[2])

                elif len(parameters) == 2:
                    try:
                        mode = MonitorType.from_string(parameters[1])
                    except ValueError as e:
                        return ('ERROR', [str(e)])
                    period = self._default_monitor_period
                else:
                    mode = self._default_monitor_mode
                    period = self._default_monitor_period

                if mode == MonitorType.inactive:
                    return ('ERROR', ["Setting inactive monitoring isn't possible. Just turn of the monitor."])
                
                if target_variable.handle_start_monitor_request_command(mode, period):
                    try:
                        target_thread.start_monitor(mode, period)
                    except ValueError as e:
                        return ('ERROR', [str(e)])
                    return ('DONE', ["Monitor started in variable {} with mode {} and period {}.".format(variable_name, mode, period)])
                else:
                    return ('ERROR', ["Target variable {} refused to start monitoring with mode {} and period {}. Check if MONITOR is supported for this variable.".format(variable_name, mode, period)])
                
            elif parameters[0] == 0:
                target_thread.stop_monitor()
                return ('DONE', [])
            else:
                return ('ERROR', ["Monitor commands first argument should be 1 or 0."])
            

        else:
            return ('ERROR', ['Command type {} not supported.'.format(command_type)])
        


    def _init_class_defaults(self):
        self._default_monitor_mode = MonitorType.periodic
        self._default_monitor_period = 0.1

    
    def _get_ip(self):
        try:
            hostname = socket.getfqdn()
            return socket.gethostbyname_ex(hostname)[2][0]
        except:
            self._logger.log("IP can't be resolved", sender_name=self.get_server_name(), priority=MqttLogPriority.ERROR)
            return "Not resolved, hostname = {}".format(socket.getfqdn())
        
        
            
        


        
