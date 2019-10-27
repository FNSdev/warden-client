import json
import logging
from datetime import datetime

import psutil
import requests

from .exceptions import WardenException

logger = logging.getLogger(__name__)


class Warden:
    def __init__(self):
        try:
            with open('settings.json', 'r') as file:
                config = json.load(file)
                self.instance_uuid = config['instance_uuid']
                self.token = config['token']
                self.delta_interval = config['delta_interval'] if config['delta_interval'] >= 30 else 30

                self.initial_state = self._get_initial_state()
                self.previous_state = self.initial_state
                self.base_url = config['server_address']
                self.request_headers = {
                    'Authorization': f'Token {config["token"]}'
                }

                # Initial caching of running processes
                for _ in psutil.process_iter(attrs=['pid', 'name', 'cpu_percent']):
                    pass
        except FileNotFoundError as e:
            raise WardenException(f'Config file was not found')
        except KeyError as e:
            raise WardenException(f'Config parameter {e} is missing')

    def update_instance_info(self):
        self._update_instance_info(payload={
            'cpu_count': self.initial_state['cpu_count'],
            'total_ram': self.initial_state['total_ram'],
            'total_swap': self.initial_state['total_swap'],
            'is_connected': True,
            'is_running': True,
        })

    def send_report(self):
        url = f'{self.base_url}/api/states/'
        current_state = self._get_current_state()
        current_state['instance'] = self.instance_uuid
        current_state['timestamp'] = int(datetime.now().timestamp())

        response = requests.post(url, json=current_state, headers=self.request_headers)
        if not response.ok:
            logger.warning('Could not send report, response = %s', response.json())
        else:
            logger.info('Report was successfully sent')

    def teardown(self):
        self._update_instance_info(payload={
            'is_running': False,
        })

    def _update_instance_info(self, payload):
        url = f'{self.base_url}/api/instances/{self.instance_uuid}/'

        response = requests.patch(url, json=payload, headers=self.request_headers)
        if not response.ok:
            logger.warning('Could not update instance info, response = %s', response.json())
        else:
            logger.info('Instance info was successfully updated')

    def _get_initial_state(self):
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        return {
            'cpu_count': psutil.cpu_count(),
            'total_ram': psutil.virtual_memory().total,
            'total_swap': psutil.swap_memory().total,
            'read_bytes': disk_io.read_bytes,
            'write_bytes': disk_io.write_bytes,
            'bytes_recv': net_io.bytes_recv,
            'bytes_sent': net_io.bytes_sent,
        }

    def _get_current_state(self):
        cpu_load = psutil.cpu_percent(interval=0.5)
        virtual_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        running_processes = []
        for proc in psutil.process_iter(attrs=['pid', 'name', 'cpu_percent']):
            if proc.info['cpu_percent'] != 0:
                running_processes.append(proc.info)

        current_state = {
            'cpu_load': cpu_load,
            'used_ram': virtual_memory.used,
            'used_swap': swap_memory.used,
            'read_bytes': disk_io.read_bytes - self.previous_state['read_bytes'],
            'write_bytes': disk_io.write_bytes - self.previous_state['write_bytes'],
            'bytes_recv': net_io.bytes_recv - self.previous_state['bytes_recv'],
            'bytes_sent': net_io.bytes_sent - self.previous_state['bytes_sent'],
            'running_processes': running_processes
        }

        self.previous_state = current_state
        return current_state
