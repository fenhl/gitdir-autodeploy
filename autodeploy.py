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
                            subprocess.check_call(['git', 'fetch', 'readonly'], cwd=cwd)
                            subprocess.check_call(['git', 'reset', '--hard', 'readonly/master'], cwd=cwd) #TODO don't reset gitignored files (or try merging and reset only if that fails)
                        except Exception as e:
                            if 'logPath' in config and os.path.exists(config['logPath']):
                                with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f-error.log')), 'w') as log_file:
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
                            subprocess.check_call(['git', 'fetch', 'readonly'], cwd=cwd)
                            subprocess.check_call(['git', 'reset', '--hard', 'readonly/master'], cwd=cwd) #TODO don't reset gitignored files (or try merging and reset only if that fails)
                        except Exception as e:
                            if 'logPath' in config and os.path.exists(config['logPath']):
                                with open(os.path.join(config['logPath'], datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f-error.log')), 'w') as log_file:
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
