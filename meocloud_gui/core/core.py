import os
import sys
import signal
from time import sleep
from subprocess import Popen, check_output

from meocloud_gui.constants import (CORE_LISTENER_SOCKET_ADDRESS,
                                    DAEMON_LISTENER_SOCKET_ADDRESS,
                                    SHELL_LISTENER_SOCKET_ADDRESS,
                                    LOGGER_NAME, CORE_BINARY_FILENAME,
                                    CORE_PID_PATH, BRAND)
from meocloud_gui.utils import test_already_running, get_own_dir

import logging
log = logging.getLogger(LOGGER_NAME)


class Core(object):
    def __init__(self, core_client):
        log.debug('Core: Initializing...')
        super(Core, self).__init__()
        self.core_client = core_client
        self.process = None
        # assumes core binary is in same dir as daemon
        self.core_binary_path = "/opt/{0}/core/".format(BRAND) + CORE_BINARY_FILENAME
        self.core_env = os.environ.copy()
        self.core_env['CLD_CORE_SOCKET_PATH'] = DAEMON_LISTENER_SOCKET_ADDRESS
        self.core_env['CLD_UI_SOCKET_PATH'] = CORE_LISTENER_SOCKET_ADDRESS
        self.core_env['CLD_SHELL_SOCKET_PATH'] = SHELL_LISTENER_SOCKET_ADDRESS
        self.thread = None

        try:
            if sys.getfilesystemencoding().lower() != 'utf-8':
                if 'C.UTF-8' in check_output(['locale', '-a']).splitlines():
                    log.info('Forcing locale to C.UTF-8')
                    self.core_env['LC_ALL'] = 'C.UTF-8'
                else:
                    log.info('Forcing locale to en_US.utf8')
                    self.core_env['LC_ALL'] = 'en_US.utf8'
        except Exception:
            log.exception('Something went wrong while trying to fix set the '
                          'LC_ALL env variable')

    def run(self):
        """
        Runs core without verifying if it is already running
        """
        log.info('Core: Starting core')
        self.process = Popen([self.core_binary_path], env=self.core_env,
                             preexec_fn=lambda: os.setpgrp())

    def stop_by_pid(self):
        pid = test_already_running(CORE_PID_PATH, CORE_BINARY_FILENAME)
        if pid:
            os.kill(pid, signal.SIGTERM)
            log.debug('Core: Killed core running with pid {0}'.format(pid))

    def stop(self):
        if self.process is not None:
            pid = self.process.pid
            failed = 0

            try:
                self.process.terminate()
            except OSError:
                failed += 1

            try:
                os.kill(pid, 0)
                self.process.kill()
                log.debug('Core: Killed core running with pid {0}'.format(pid))
            except OSError:
                failed += 1

            if failed > 1:
                os.system("killall meocloudd")

            self.process = None
        else:
            self.stop_by_pid()

    def watchdog(self):
        # Watchdog wait for event core_start_ready before starting
        log.debug('Core: watchdog will now start')
        count = 0

        while not self.thread.stopped():
            if count > 10:
                log.error(
                    'Core: Watchdog giving up after 10 retries')
                return

            if not test_already_running(CORE_PID_PATH, CORE_BINARY_FILENAME):
                count += 1

                try:
                    self.run()
                except OSError:
                    self.process = None
                    self.core_client.ignore_logs = True
                    log.error(
                        'Core: watchdog error while starting core')

                if self.process is not None:
                    self.process.wait()

                self.core_client.ignore_logs = True
