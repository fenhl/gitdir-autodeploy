#!/usr/bin/env python3

import sys

sys.path.append('/opt/py')

import bottle
import datetime
import gitdir.host
import json
import os.path
import pathlib
import subprocess
import traceback

try:
    import uwsgi
    CONFIG_PATH = pathlib.Path(uwsgi.opt['config_path'])
except:
    CONFIG_PATH = pathlib.Path('/etc/xdg/gitdir/autodeploy.json')

bottle.debug()

application = bottle.Bottle()

try:
    with CONFIG_PATH.open() as config_file:
        CONFIG = json.load(config_file)
except:
    CONFIG = {}

try:
    LOG_PATH = pathlib.Path(CONFIG['logPath'])
    if not LOG_PATH.exists():
        LOG_PATH = None
except:
    LOG_PATH = None

class DeployError(Exception):
    pass

def try_subprocess(args, cwd=None, request_time=None):
    if request_time is None:
        request_time = datetime.datetime.utcnow()
    popen = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(cwd)) #TODO (Python 3.6) remove str wrapping
    if popen.wait() != 0:
        if LOG_PATH:
            with (LOG_PATH / request_time.strftime('%Y%m%d-%H%M%S-%f-error.log')).open('a') as log_file:
                print('subprocess output:', file=log_file)
                print(popen.stdout.read().decode('utf-8'), file=log_file)
        raise subprocess.CalledProcessError(popen.returncode, args)

@application.route('/deploy/<hostname>/<repo_spec:path>/<branch>')
def deploy(hostname, repo_spec, branch='master', request_time=None):
    try:
        gitdir.host.by_name(hostname).deploy(repo_spec, branch=branch)
    except Exception as e:
        if LOG_PATH and request_time is not None:
            with (LOG_PATH / request_time.strftime('%Y%m%d-%H%M%S-%f-error.log')).open('a') as log_file:
                print('Error while deploying from {}:'.format(hostname), file=log_file)
                print('repo: ' + repo_spec, file=log_file)
                print('branch: ' + (branch or 'master'), file=log_file)
                traceback.print_exc(file=log_file)
        raise DeployError('{} while deploying. host: {!r}, repo: {!r}, branch: {!r}'.format(e.__class__.__name__, hostname, repo_spec, branch)) from e

@application.route('/')
def show_index():
    return bottle.static_file('static/index.html', root=CONFIG.get('documentRoot', os.path.dirname(os.path.abspath(__file__))))

@application.route('/deploy')
def get_deploy():
    request_time = datetime.datetime.utcnow()
    for host, host_data in CONFIG.get('repos', {}).items():
        for repo_spec, repo_info in host_data.items():
            for branch in repo_info.get('branches', ['master']):
                deploy(host, repo_spec, branch=branch, request_time=request_time)

@application.route('/deploy', method='POST')
def post_deploy():
    if LOG_PATH:
        with (LOG_PATH / datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f.json')).open('w') as log_file:
            json.dump(bottle.request.json, log_file, sort_keys=True, indent=4)
            print(file=log_file)
    return deploy('github.com', bottle.request.json['repository']['full_name'], branch=bottle.request.json['ref'][11:]) #TODO add support for hosts other than github.com

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
