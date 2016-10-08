#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gitdir autodeploy
"""

import sys

sys.path.append('/opt/py')

import bottle
import datetime
import gitdir.host
import json
import os.path
import subprocess
import traceback

try:
    import uwsgi
    CONFIG_PATH = uwsgi.opt['config_path']
except:
    CONFIG_PATH = '/etc/xdg/gitdir/autodeploy.json'

bottle.debug()

application = bottle.Bottle()

try:
    with open(CONFIG_PATH) as config_file:
        config = json.load(config_file)
except:
    config = {}

class DeployError(Exception):
    pass

def try_subprocess(args, cwd=None, request_time=None):
    if request_time is None:
        request_time = datetime.datetime.utcnow()
    popen = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
    if popen.wait() != 0:
        if 'logPath' in config and os.path.exists(config['logPath']):
            with open(os.path.join(config['logPath'], request_time.strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
                print('subprocess output:', file=log_file)
                print(popen.stdout.read().decode('utf-8'), file=log_file)
        raise subprocess.CalledProcessError(popen.returncode, args)

@application.route('/deploy/<hostname>/<repo_spec:path>/<branch>')
def deploy(hostname, repo_spec, branch='master', request_time=None):
    try:
        gitdir.host.by_name(hostname).deploy(repo_spec, branch=branch)
    except Exception as e:
        if 'logPath' in config and os.path.exists(config['logPath']) and request_time is not None:
            with open(os.path.join(config['logPath'], request_time.strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
                print('Error while deploying from {}:'.format(hostname), file=log_file)
                print('repo: ' + repo_spec, file=log_file)
                print('branch: ' + (branch or 'master'), file=log_file)
                traceback.print_exc(file=log_file)
        raise DeployError('{} while deploying. host: {!r}, user: {!r}, repo: {!r}, branch: {!r}'.format(e.__class__.__name__, hostname, repo_spec, branch)) from e

@application.route('/')
def show_index():
    return bottle.static_file('static/index.html', root=config.get('documentRoot', os.path.dirname(os.path.abspath(__file__))))

@application.route('/deploy')
def get_deploy():
    request_time = datetime.datetime.utcnow()
    for host, host_data in config.get('repos', {}).items():
        for repo_spec, repo_info in host_data.items():
            for branch in repo_info.get('branches', ['master']):
                deploy(host, repo_spec, branch=branch, request_time=request_time)

@application.route('/deploy', method='POST')
def post_deploy():
    if 'logPath' in config and os.path.exists(config['logPath']):
        with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f.json')), 'w') as log_file:
            json.dump(bottle.request.json, log_file, sort_keys=True, indent=4, separators=(',', ': '))
    return get_deploy() #TODO read the payload to see what to deploy

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
