#!/usr/bin/env python

import collectd
import requests


# PULP host. Override in config by specifying 'Host'
PULP_HOST = 'localhost'
# PULP user. Override in config by specifying 'User'
PULP_USER = 'monitoring-user'
# PULP user password. Override in config by specifying 'Password'
PULP_PASSWORD = 'msecret'
# Verbose logging on/off. Override in config by specifying 'Verbose'.
VERBOSE_LOGGING = False


class PulpConn(object):
    """ Pulp connector class """

    def __init__(self, host, username, password):
        self.username = username
        self.password = password
        self.host = host

    def get_tasks(self):
        """ Retrieves the PULP tasks """

        url = "https://%s/%s" % (self.host, '/pulp/api/v2/tasks/')
        r = requests.get(url, auth=(self.username, self.password), verify=False)

        return r.json()


def configure_callback(conf):
    """ Receive configuration block """

    global PULP_HOST, PULP_USER, PULP_PASSWORD, VERBOSE_LOGGING

    for node in conf.children:
        if node.key == 'Host':
            PULP_HOST = node.values[0]
        elif node.key == 'User':
            PULP_USER = node.values[0]
        elif node.key == 'Password':
            PULP_PASSWORD = node.values[0]
        elif node.key == 'Verbose':
            VERBOSE_LOGGING = bool(node.values[0])
        else:
            collectd.warning('pulp-tasks plugin: Unknown config key: %s.' % node.key)
    log_verbose('Configured with host=%s, user=%s' % (PULP_HOST, PULP_USER))


def dispatch_value(info, key, type, type_instance=None):
    """ Read a key from info response data and dispatch a value """

    if key not in info:
        collectd.warning('pulp-tasks plugin: Info key not found: %s' % key)
        return

    if not type_instance:
        type_instance = key

    value = int(info[key])
    log_verbose('Sending value: %s=%s' % (type_instance, value))

    val = collectd.Values(plugin='pulp-tasks')
    val.type = type
    val.type_instance = type_instance
    val.values = [value]
    val.dispatch()


def read_callback():
    log_verbose('Read callback called')

    # get tasks from the server
    pulp_conn = PulpConn(PULP_HOST, PULP_USER, PULP_PASSWORD)
    tasks = pulp_conn.get_tasks()
    if not tasks:
        collectd.error('pulp-tasks plugin: No info received')
        return

    # get running and waiting tasks
    info = {}
    info['running_tasks'] = info['waiting_tasks'] = 0
    for task in tasks:
        state = task.get('state', '')
        if state == 'running':
            info['running_tasks'] += 1
        elif state == 'waiting':
            info['waiting_tasks'] += 1

    # send high-level values
    dispatch_value(info, 'running_tasks', 'gauge')
    dispatch_value(info, 'waiting_tasks', 'gauge')


def log_verbose(msg):
    if not VERBOSE_LOGGING:
        return
    collectd.info('pulp-tasks plugin [verbose]: %s' % msg)


# register callbacks
collectd.register_config(configure_callback)
collectd.register_read(read_callback)
