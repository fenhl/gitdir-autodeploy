#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gitdir autodeploy
"""

import bottle
import datetime
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

@application.route('/')
def show_index():
    return bottle.static_file('static/index.html', root=config.get('documentRoot', os.path.dirname(os.path.abspath(__file__))))

@application.route('/deploy')
def get_deploy():
    request_time = datetime.datetime.utcnow()
    for host, host_data in config.get('repos', {}).items():
        if host == 'github.com':
            for user, repo_data in host_data.items():
                for repo, branches in repo_data.items():
                    for branch in branches:
                        try:
                            if branch == 'master' or branch is None:
                                cwd = os.path.join('/opt/git/github.com', user, repo, 'master')
                            else:
                                cwd = os.path.join('/opt/git/github.com', user, repo, 'branch', branch)
                            try_subprocess(['git', 'fetch', 'readonly'], cwd=cwd, request_time=request_time)
                            try_subprocess(['git', 'reset', '--hard', 'readonly/master'], cwd=cwd, request_time=request_time) #TODO don't reset gitignored files (or try merging and reset only if that fails)
                        except Exception as e:
                            if 'logPath' in config and os.path.exists(config['logPath']):
                                with open(os.path.join(config['logPath'], request_time.strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
                                    print('Error while deploying from github.com:', file=log_file)
                                    print('username: ' + user, file=log_file)
                                    print('repo: ' + repo, file=log_file)
                                    print('branch: ' + (branch or 'master'), file=log_file)
                                    traceback.print_exc(file=log_file)
                            raise
        elif host == 'gitlab.com':
            for user, repo_data in host_data.items():
                for repo, branches in repo_data.items():
                    for branch in branches:
                        try:
                            if branch == 'master' or branch is None:
                                cwd = os.path.join('/opt/git/gitlab.com', user, repo, 'master')
                            else:
                                cwd = os.path.join('/opt/git/gitlab.com', user, repo, 'branch', branch)
                            try_subprocess(['git', 'fetch', 'readonly'], cwd=cwd, request_time=request_time)
                            try_subprocess(['git', 'reset', '--hard', 'readonly/master'], cwd=cwd, request_time=request_time) #TODO don't reset gitignored files (or try merging and reset only if that fails)
                        except Exception as e:
                            if 'logPath' in config and os.path.exists(config['logPath']):
                                with open(os.path.join(config['logPath'], request_time.strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
                                    print('Error while deploying from gitlab.com:', file=log_file)
                                    print('username: ' + user, file=log_file)
                                    print('repo: ' + repo, file=log_file)
                                    print('branch: ' + (branch or 'master'), file=log_file)
                                    traceback.print_exc(file=log_file)
                            raise
        else:
            raise LookupError('host not currently supported: {!r}'.format(host))

@application.route('/deploy', method='POST')
def post_deploy():
    if 'logPath' in config and os.path.exists(config['logPath']):
        with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f.json')), 'w') as log_file:
            json.dump(bottle.request.json, log_file, sort_keys=True, indent=4, separators=(',', ': '))
    return get_deploy() #TODO read the payload to see what to deploy

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
