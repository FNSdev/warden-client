import logging
import os
import signal
import time

from warden import Warden

logger = logging.getLogger(__name__)
STOP = False


def on_stop(sig, frame):
    global STOP
    STOP = True


signal.signal(signal.SIGTERM, on_stop)


def main():
    pid = os.getpid()
    with open('warden.pid', 'w') as pid_file:
        pid_file.write(str(pid))

    warden = Warden()
    warden.update_instance_info()

    while True:
        if STOP:
            warden.teardown()
            break

        warden.send_report()

        logger.info(f'Sleeping for {warden.delta_interval} seconds ...')
        time.sleep(warden.delta_interval)


if __name__ == '__main__':
    main()
