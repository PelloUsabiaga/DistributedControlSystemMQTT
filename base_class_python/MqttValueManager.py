import time
import paho.mqtt.client as client_mqtt

from base_class_python import DateUtility


class MqttValueManager:
    """
    A class to easily get and set values into variables over MQTT. It is usefull for any
    program that needs to access a variable value sporadically. 

    To use this class, a MqttValueManager object must be created, and then the methods
    get_variable_value and set_variable_value can be used.
    """
    def __init__(self, mqtt_broker_ip: str, 
                 mqtt_broker_port: int=1883, topic_origin: str='',
                 timeout: float=10) -> None:
        self._mqtt_broker_ip = mqtt_broker_ip
        self._mqtt_broker_port = mqtt_broker_port
        self._topic_origin = topic_origin
        self._timeout = timeout

        self.last_get_id = None
        self._received = False
        self._create_client()
        self._last_response = None

    def _on_connect(self, client, userdata, flags, rc):
        self._connected = True
    

    def _mqtt_message_handler(self, client, userdata, message):
        try:
            payload : str = message.payload.decode()
            if payload.startswith("NACK"):
                raise ValueError("The message to get the variable have not been adquired: {}".format(payload))

            elif payload.startswith("ERROR"):
                raise ValueError("The variable to get have returned error: {}".format(payload))

            elif payload.startswith("DONE"):
                splited_payload = payload.split(";")
                if splited_payload[1] != self.last_get_id:
                    pass
                else:
                    if len(splited_payload) != 3:
                        raise ValueError("The response have the incorrect number of arguments: {}".format(payload))

                    self._last_response = (splited_payload[0], splited_payload[2][1:-1].split(","))
                    self._received = True
        except ValueError as e:
            print(e)


    def _create_client(self):
        self._client = client_mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._mqtt_message_handler

        self._connected = False
        self._client.connect(self._mqtt_broker_ip, self._mqtt_broker_port, 60)
        self._client.loop_start()
        t0 = time.time()
        while not self._connected:
            if ((time.time() - t0) < self._timeout):
                pass
            else:
                raise TimeoutError("To much time connecting to broker")


    def get_variable_value(self, variable_name: str, timeout: float=1) -> tuple[str, list[str]]:
        """
        Get the value of a MQTT variable. Return a tuple with the response code, and argument list.

        Internally, the value manager creates a subscription to the response topic of the variable, sends
        a GET command, and waits for it to be ansered. Then, breaks the subscription.

        Raises TimeuotError and others.
        """
        t_start = time.time()
        topic_to_subscribe = self._topic_origin + "responses/{}".format(variable_name)
        self._received = False
        self._client.subscribe(topic=topic_to_subscribe)
        
        topic = self._topic_origin + "commands/{}".format(variable_name)
        self.last_get_id = DateUtility.get_date_string()
        payload = "GET;{}".format(self.last_get_id)
        self._client.publish(topic, payload)

        t0 = time.time()
        while ((time.time() - t0) < timeout):
            if self._received:
                self._client.unsubscribe(topic_to_subscribe)
                return self._last_response
            else:
                pass
        self._client.unsubscribe(topic_to_subscribe)
        raise TimeoutError("Timeout at getting variable {}, more than {} seconds elapsed".format(variable_name, timeout))
    

    def set_variable_value(self, variable_name: str, new_value: str) -> bool:
        """
        Set the value of a MQTT variable. Return true if message is sended, false if not, but 
        does not check if the message is correctly acknowledge and executed.

        Internaly it simply publishes a PUT command.
        """
        topic = self._topic_origin + "commands/{}".format(variable_name)
        payload = "PUT;{};[{}]".format(DateUtility.get_date_string(), new_value)
        try:
            info = self._client.publish(topic=topic, payload=payload)
            info.wait_for_publish()
            return info.is_published()
        except RuntimeError as e:
            return False
