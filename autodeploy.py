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

@application.route('/')
def show_index():
    return bottle.static_file('static/index.html', root=config.get('documentRoot', os.path.dirname(os.path.abspath(__file__))))

@application.route('/deploy')
def get_deploy():
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
                            fetch_popen = subprocess.Popen(['git', 'fetch', 'readonly'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
                            if fetch_popen.wait() != 0:
                                if 'logPath' in config and os.path.exists(config['logPath']):
                                    with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
                                        print('Error while fetching repo. Subprocess output:', file=log_file)
                                        print(fetch_popen.stdout.read().decode('utf-8'))
                                raise subprocess.CalledProcessError('Error while fetching repo.')
                            merge_popen = subprocess.Popen(['git', 'reset', '--hard', 'readonly/master'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd) #TODO don't reset gitignored files (or try merging and reset only if that fails)
                            if merge_popen.wait() != 0:
                                if 'logPath' in config and os.path.exists(config['logPath']):
                                    with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
                                        print('Error while merging repo. Subprocess output:', file=log_file)
                                        print(merge_popen.stdout.read().decode('utf-8'))
                                raise subprocess.CalledProcessError('Error while merging repo.')
                        except Exception as e:
                            if 'logPath' in config and os.path.exists(config['logPath']):
                                with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
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
                            fetch_popen = subprocess.Popen(['git', 'fetch', 'readonly'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
                            if fetch_popen.wait() != 0:
                                if 'logPath' in config and os.path.exists(config['logPath']):
                                    with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
                                        print('Error while fetching repo. Subprocess output:', file=log_file)
                                        print(fetch_popen.stdout.read().decode('utf-8'))
                                raise subprocess.CalledProcessError('Error while fetching repo.')
                            merge_popen = subprocess.Popen(['git', 'reset', '--hard', 'readonly/master'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd) #TODO don't reset gitignored files (or try merging and reset only if that fails)
                            if merge_popen.wait() != 0:
                                if 'logPath' in config and os.path.exists(config['logPath']):
                                    with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
                                        print('Error while merging repo. Subprocess output:', file=log_file)
                                        print(merge_popen.stdout.read().decode('utf-8'))
                                raise subprocess.CalledProcessError('Error while merging repo.')
                        except Exception as e:
                            if 'logPath' in config and os.path.exists(config['logPath']):
                                with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f-error.log')), 'a') as log_file:
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
