# -*- coding: utf-8 -*-
"""
Created on Fri Mar 24 11:52:56 2023

@author: pello usabiaga
"""
import sys
import traceback
import threading
import time
from typing import Callable, Union
import paho.mqtt.client as client_mqtt
import socket

from base_class_python.MqttLogger import MqttLogger, MqttLogPriority

class MqttConnection:
    """
    A class to handle the connection with the MQTT brocker. It uses paho mqtt library.
    """
    
    def __init__(self, mqtt_message_handler: Callable, mqtt_on_connect_handler: Callable,
                 terminate_program_function: Callable,
                 logger: MqttLogger, name_for_connection: str,
                 mqtt_broker_ip: str, mqtt_broker_port: int=1883,
                 username: str | None=None, password: str | None=None) -> None:
        """
        It can receive only one broker, or a list of brokers, in which case the ports option turns 
        mandatory to be a list with the same length.

        The message handler and the on connect handler have to be defined outside this class. 
        They should be in paho mqtt-compatible format.
        """

        self._logger = logger
        self._name = name_for_connection

        self._mqtt_broker_ip = mqtt_broker_ip
        self._mqtt_broker_port = mqtt_broker_port
       
        
        self.mqtt_message_handler = mqtt_message_handler
        self.mqtt_on_connect_handler = mqtt_on_connect_handler
        self.terminate_program_function = terminate_program_function

        self._username = username 
        self._password = password
        
        self._run_in_background = True

        self._topics_to_subscribe: list[str] = []

        self._init_mqtt_client()


    def subscribe(self, topic: str):
        self._topics_to_subscribe.append(topic)
        self._client.subscribe(topic)


    def try_connection(self):
        if self._run_in_background:
            try:
                self._client.connect(self._mqtt_broker_ip, self._mqtt_broker_port)
            except TimeoutError as e:
                if self._logger != None:
                    self._logger.log("Connection failed with error: {}".format(e), self._name, MqttLogPriority.ERROR)
                self.on_connect_fail(None, None)

    
    def on_disconnect(self, client, userdata,  rc):
        if self._logger != None:
            self._logger.log("Disconnected from broker.", self._name, MqttLogPriority.ERROR)
        
        self.try_connection()

    
    def on_connect_fail(self, client, userdata):
        if self._logger != None:
            self._logger.log("Connection failed with broker.", self._name, MqttLogPriority.ERROR)
        self.try_connection()


    def on_connect(self, client, userdata, flags, rc):
        if self._logger != None:
            self._logger.log("Connected to broker broker.", self._name, MqttLogPriority.INFO)
        for topic in self._topics_to_subscribe:
            self._client.subscribe(topic)
        self.mqtt_on_connect_handler(client, userdata, flags, rc)
   
    
    def _init_mqtt_client(self):
        self._client = client_mqtt.Client()
        if (self._username != None and self._password != None):
            self._client.username_pw_set(self._username, self._password)
        self._client.on_connect = self.on_connect
        self._client.on_message = self.mqtt_message_handler

        self._client.on_connect_fail
        self._client.on_disconnect = self.on_disconnect
        
        self.try_connection()

        self.background_loop_thread = threading.Thread(target=self.background_loop, name=self._name, daemon=True)
        self.background_loop_thread.start()


    
    def background_loop(self):
        while self._run_in_background:
            try:
                self._client.loop_forever()
            except Exception as e:
                self._logger.log("Mqtt loop failed with error: {}. Sys info = {}. Ending.".format(e, traceback.format_exc()), self._name, MqttLogPriority.CRITICAL)
                self.terminate_program_function()
        
        
    def send_single_mqtt_message(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> None:
        """
        To send a single message, its use is only recommended for monitor data.
        """
        try:
            self._client.publish(topic, payload, qos, retain)
        except Exception as e:
            if self._logger != None:
                self._logger.log("Send single message failed: {}; {}:{}.".format(e, topic, payload), self._name, MqttLogPriority.ERROR)

    
    def send_response(self, topic_of_response: str, response_code: str, command_id: str, response_list: list[Union[int, float, str]], topic_of_request: str, payload_of_request: str) -> None:
        """
        To send a response to the brocker. There are defined the formats of the response messages.
        """
        if response_code == 'DONE':
            if response_list == []:
                self.send_single_mqtt_message(topic_of_response, 'DONE;{}'.format(command_id))
            else:
                self.send_single_mqtt_message(topic_of_response, 'DONE;{};{}'.format(command_id, str(response_list)))
        
        elif response_code == 'ERROR':
            self.send_single_mqtt_message(topic_of_response, 'ERROR;{};{}'.format(command_id, str(response_list)))
        
        else:
            self.send_single_mqtt_message(topic_of_response,'NACK_{}_{}_{}'.format(topic_of_request, payload_of_request, 'Not acquired in {}, error message: {}'.format(self._get_host_ip(), str(response_list))))
        
    def close_connection(self):
        self._run_in_background = False # important that this goes before loop_stop

        self._client.loop_stop()


    def _get_host_ip(self):
        try:
            hostname = socket.getfqdn()
            return socket.gethostbyname_ex(hostname)[2][0]
        except:
            return "Could not get host"
        
        
