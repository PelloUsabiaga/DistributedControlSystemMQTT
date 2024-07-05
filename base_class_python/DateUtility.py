import datetime

import dateutil.parser

def get_date_string():
    """
    If date format have to be changed, it can be done here. This affects both the monitor messages, and the ID-s of the messages sent by 
    MqttValueManager.
    """
    return datetime.datetime.utcnow().isoformat()

def check_date_string(date_string: str) -> bool:
    """
    To check the integrity of date strings, for example message ID-s.
    """
    try:
        dateutil.parser.parse(date_string, fuzzy=False)
        return True
    except ValueError:
        return False