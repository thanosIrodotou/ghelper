#!/usr/bin/python
# encoding: utf-8

"""gh[options]

Usage:
    gh list
    gh repos <query>
    gh users <query>
    gh pulls <query>
    gh refreshcache
    gh [-n]
    gh -h|--help
    gh --version

Options:
    -n, --nothing   Dry run. Don't actually change any workflow.
    -h, --help      Show this message and exit.
    --version       Show version number and exit.

"""

import functools
import json
import os
import sys

from HTMLParser import HTMLParser

import docopt
# from workflow import Workflow, web
from workflow import (
    Workflow3,
    web,
    MATCH_STARTSWITH,
    MATCH_CAPITALS,
    MATCH_ATOM,
    MATCH_INITIALS_STARTSWITH,
    MATCH_SUBSTRING)
from workflow.update import Version

log = None

# version of AW in this workflow
VERSION_FILE = os.path.join(os.path.dirname(__file__), 'workflow/version')
MIN_VERSION = Version(open(VERSION_FILE).read())

h = HTMLParser()

BASE_URL = "https://api.github.com"
ACCESS_TOKEN = os.getenv('token')
ORG = os.getenv('org')
MATCH = (MATCH_STARTSWITH |
         MATCH_CAPITALS |
         MATCH_ATOM |
         MATCH_INITIALS_STARTSWITH |
         MATCH_SUBSTRING)


def list_actions():
    """Show available workflow actions."""
    items = [
        dict(title='View Log File',
             subtitle='Open the log file in Console.app',
             arg='log',
             uid='log',
             valid=True),
        dict(title='View source code',
             subtitle='View the code for this workflow on github.com',
             arg='gogithub',
             uid='gogithub',
             valid=True),
        dict(title='CLEAR REPOSITORY+USER CACHE',
             subtitle='Clears any cached repositories (next lookup will rebuild the cache)',
             arg='refreshcache',
             uid='refreshcache',
             valid=True)
    ]

    for d in items:
        wf.add_item(**d)


def search_repos(query):
    items = wf.filter(query, get_items(),  key=lambda d: d['name'], match_on=MATCH, min_score=50)
    for item in items:
        wf.add_item(item['name'], item['url'], arg=item['name'], valid=True)


def get_items():
    return wf.cached_data('private', functools.partial(iterate_repos), max_age=0)


def iterate_repos():
    data = [{'id': val['id'], 'name': val['name'], 'url': val['html_url']}
            for page in range(1, 8)
            for val in get_repos(page)]

    return data


def get_repos(page=None):
    list_request = web.get(
        'https://api.github.com/orgs/{}/repos?page={}&per_page=100&type=private'.format(ORG, page),
        headers={'Authorization': 'token ' + ACCESS_TOKEN}
    )
    return list_request.json()


def search_members(query):
    items = wf.filter(query, get_member_items(),  key=lambda d: d['login'], match_on=MATCH, min_score=50)
    for item in items:
        wf.add_item(item['login'], item['url'], arg=item['login'], valid=True)


def get_member_items():
    return wf.cached_data('private-users', functools.partial(iterate_members), max_age=0)


def iterate_members():
    data = [{'id': val['id'], 'login': val['login'], 'url': val['html_url']}
            for page in range(1, 7)
            for val in get_members(page)]

    return data


def get_members(page=None):
    log.warn('calling')
    list_request = web.get(
        'https://api.github.com/orgs/{}/members?page={}'.format(ORG,page),
        headers={'Authorization': 'token ' + ACCESS_TOKEN}
    )
    return list_request.json()


def get_open_prs(repo):
    response = web.get(
        'https://api.github.com/repos/{}/{}/pulls?state=open'.format(ORG, repo),
        headers={'Authorization': 'token ' + ACCESS_TOKEN}
    )

    json_response = response.json()
    if len(json_response) is 0:
        wf.add_item('Could not find any open PRs for {}'.format(repo), valid=True)
    for d in json_response:
        wf.add_item('{} (PR-{})'.format(d['title'], d['number']), 'Opened by: {}, on: {}'.format(d['user']['login'],d['created_at']), arg=d['html_url'], valid=True)


def refresh_cache():
    wf.add_item(wf.cached_data_age('private'), 'seconds remaining until cache expiry')
    wf.add_item('removing cache file')
    wf.clear_cache()



def main(wf):
    if wf.update_available:
        log.info('UPDATE AVAILABLE')
        wf.add_item('New version available',
                'Action this item to install the update',
                autocomplete='workflow:update',
                icon=ICON_INFO)

    opts = docopt.docopt(__doc__, argv=wf.args, version=wf.version)
    query = opts['<query>']

    if opts['list']:
        list_actions()

    if opts['repos']:
        search_repos(query)

    if opts['users']:
        search_members(query)

    if opts['pulls']:
        get_open_prs(query)

    if opts['refreshcache']:
        refresh_cache()
        wf.add_item('caches removed', 'next repo search will trigger a rebuild')

    wf.send_feedback()


if __name__ == '__main__':
    wf = Workflow3(
        update_settings = {'github_slug': 'thanosIrodotou/ghelper'},
        help_url='https://github.com/thanosIrodotou/ghelper/issues'
    )
    log = wf.logger
    sys.exit(wf.run(main, text_errors=True))
