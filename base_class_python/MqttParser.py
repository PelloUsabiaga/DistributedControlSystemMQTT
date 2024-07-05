# -*- coding: utf-8 -*-
"""
Created on Wed Mar 29 11:48:21 2023

@author: gaudee
"""

import ast
import base_class_python.DateUtility as DateUtility

class MqttParser:
    """
    This class parses incoming commands, and makes shure that they are correctly formated.
    """
    
    def __init__(self, topic_origin=""):
        self._topic_origin = topic_origin
    
    def parse_mqtt_command(self, topic, payload) -> tuple[str, str, str, list]:
        """
        It returns a tuple with (command_name, command_type, command_id, parameters).

        Raises ValueError.
        """

        if topic.startswith(self._topic_origin + "commands"):
            
            topic_structure = topic.split('/')
            command_name = topic_structure[-1]
            if command_name == "commands":
                raise ValueError("No command specified. Use a subtopic of commands")
            
            payload_array = payload.split(';')
            if len(payload_array) not in (2, 3):
                raise ValueError("The command format isn't correct, to much or to few arguments")
            
            command_type = payload_array[0]
            command_id = payload_array[1]

            if not DateUtility.check_date_string(command_id):
                raise ValueError("The id format isn't correct, it should be ISO-8601 with microseconds")
                
            if len(payload_array) == 3:
                try:
                    parameters = ast.literal_eval(payload_array[2])
                except (ValueError, NameError, SyntaxError):
                    raise ValueError("The parameters format should be in python array format.")
                if type(parameters) != list:
                    raise ValueError("Parameters should be in list format")
            else:
                parameters = []
            
            return (command_name, command_type, command_id, parameters)

    
        else:
            raise ValueError("The topic {} is not a command topic".format(topic))