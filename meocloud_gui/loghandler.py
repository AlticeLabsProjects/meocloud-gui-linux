import logging
from meocloud_gui.exceptions import ListenerConnectionFailedException
from meocloud_gui.protocol.daemon_core.ttypes import NotificationLevel


class LogHandler(logging.Handler):
    def __init__(self, core_client=None):
        logging.Handler.__init__(self)
        self.core_client = core_client

    def emit(self, record):
        if self.core_client is not None and not self.core_client.ignore_logs:
            try:
                if (record.levelname != "DEBUG" and
                        record.levelname != "INFO" and
                        record.levelname != "WARNING"):
                    self.core_client.log(
                        NotificationLevel.ERROR, record.message)
            except ListenerConnectionFailedException:
                pass
