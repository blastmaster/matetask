#! /usr/bin/env python3

''' matetask.py

    Scrapes your current balance from matemat and creates a taskwarrior task if
    your balance is critical low. To remindes you to pay your Drinks!

'''

import sys
import os
import re

from bs4 import BeautifulSoup
import requests

from taskw import TaskWarrior


MATEMAT_URL = 'http://matemat.hq.c3d2.de'
# username and password required if you want to access outside of GCHQ.
AUTH_USER, AUTH_PW = '', ''
# matemat username
USERNAME = os.getenv('USER')
# file where user-id would be cached
CACHE_FILE = os.path.join(os.getenv('HOME'), '.cache/matetask/user_cache')
# minimum balance, notify if we fall below
MIN_BALANCE = 5.0
# critical balance, set priority to high if we fall below
CRITIC_BALANCE = 0.0
# taskwarrior tags to use for matetask
TASK_TAGS = ['mate', 'c3d2', 'todo']
# taskwarrior description to use for matetask
TASK_DESC = 'matemat bezahlen!'


if not os.path.exists(CACHE_FILE):
    os.makedirs(CACHE_FILE)


def cache_user(user_name, user_url):
    ''' appending the line 'user_name : user_url' to CACHE_FILE '''

    with open(CACHE_FILE, 'a') as cache_f:
        cache_f.write(' : '.join([user_name, user_url]))


def get_cached(username):
    ''' Reads the CACHE_FILE and returns a tuple(user, url) if username exists
        in the cached entries. '''

    with open(CACHE_FILE) as cache_f:
        for user, url in [e.split(' : ') for e in cache_f.readlines()]:
            if user == username:
                return user, url


def scrape_user(soup, username):
    ''' Searches for a given username returns a tuple
        containing the name and the user url. '''

    user_entries = soup.select('.article > a')
    for entry in user_entries:
        entry_name = entry.getText().rstrip()
        if entry_name == username:
            return entry_name, entry['href']


def scrape_balance(user_url):
    ''' Scrape the current balance of the user_url.
        Returns the balance as a float. '''

    resp = requests.get(user_url, auth=(AUTH_USER, AUTH_PW))
    soup = BeautifulSoup(resp.text, 'html.parser')
    balance_tag = soup.select('.header > ul > li')[0]
    balance = re.sub(r'[^\d,]+', '', balance_tag.text)
    return float(balance)


def add_taskwarrior_task(current_balance, tags, priority='M'):
    ''' Add or update the taskwarrior task. If a task with the description given
        in TASK_DESC and the given tags already exists. The task description will be
        updated to the value of the current_balance if changed. Otherwise a new
        task will be added.
    '''

    task_filter = {'tags': tags,
                   'description': TASK_DESC}
    desc = " ".join([TASK_DESC, str(current_balance)])
    tw = TaskWarrior()

    task = tw.filter_tasks(task_filter)
    if task:
        old_desc = task['description']
        old_balance = float(old_desc.split()[-1])
        if current_balance < old_balance:
            task.update({'description': desc,
                         'priority': priority})
            tw.task_update(task)
    else:
        tw.task_add(desc, tags=tags, priority=priority)


def main(*args):
    # TODO: add argument handling

    user, user_url = get_cached(USERNAME)
    if not user and not user_url:
        response = requests.get(MATEMAT_URL, auth=(AUTH_USER, AUTH_PW))
        soup = BeautifulSoup(response.text, 'html.parser')
        user, user_url = scrape_user(soup, USERNAME)
        cache_user(user, user_url)

    current_balance = scrape_balance(user_url)

    if current_balance < MIN_BALANCE:
        if current_balance < CRITIC_BALANCE:
            add_taskwarrior_task(current_balance, TASK_TAGS, priority='H')
        else:
            add_taskwarrior_task(current_balance, TASK_TAGS)


if __name__ == '__main__':
    main(sys.argv)
