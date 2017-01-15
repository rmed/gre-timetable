# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Rafael Medina García <rafamedgar@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Script to obtain ical file containing the personal University of Greenwich
timetable.
"""

from ics import Calendar, Event
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
import datetime
import getpass
import os
import pytz
import six
import sys


PHANTOM = os.getenv('PHANTOMJS', './phantomjs')

URLS = {
    'login': 'https://portal.gre.ac.uk/cp/home/displaylogin',
    # 'timetable': 'https://portal.gre.ac.uk/cp/redirect/new_timetable'
    'timetable': 'https://portal.gre.ac.uk/delegate/redirect/timetable'
}

# Timetable columns
COL_ACTI = 0
COL_DESC = 1
COL_TYPE = 2
COL_START = 3
COL_END = 4
COL_WEEK = 5
COL_ROOM = 6
COL_STAFF = 7

# Day deltas (M, T, W, Th, S, Su)
DAYS = [
    datetime.timedelta(days=0),
    datetime.timedelta(days=1),
    datetime.timedelta(days=2),
    datetime.timedelta(days=3),
    datetime.timedelta(days=4),
    datetime.timedelta(days=5),
    datetime.timedelta(days=6)
]

# Week starting dates
TZONE = pytz.timezone('GMT')
START_DATE = TZONE.localize(datetime.datetime(year=2016, month=9, day=19))
WEEKS = ['dummy']

for w in range(52):
    WEEKS.append(START_DATE + datetime.timedelta(days=(7 * w)))

# Term bounds
TERMS = [(2, 13), (18, 29), (34, 52)]


class Scrapper(object):

    def __init__(self, username, password, term):
        self.username = username
        self.password = password
        self.term = int(term)

        self.ical = Calendar()

        self.driver = webdriver.PhantomJS(executable_path=PHANTOM)
        self.driver.set_window_size(1120, 550)


    def login(self):
        """Login to the portal."""
        six.print_('Logging in...')

        self.driver.get(URLS['login'])

        user_input = self.driver.find_element_by_id('username')
        pass_input = self.driver.find_element_by_id('password')
        # login_btn = self.driver.find_element_by_id('loginbutton')
        login_btn = self.driver.find_element_by_tag_name('button')

        user_input.clear()
        pass_input.clear()

        user_input.send_keys(self.username)
        pass_input.send_keys(self.password)

        login_btn.click()

    def access_timetable(self):
        """Access the timetable."""
        six.print_('Accessing timetable...')

        self.driver.get(URLS['timetable'])

        # Select 2016/2017
        # select_year = Select(self.driver.find_element_by_name('navOption'))
        # select_year.select_by_visible_text('2016/17')

        # Select 'My Timetable'
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, 'LinkBtn_mytimetablestudentset')
            )
        )

        own_table = self.driver.find_element_by_id('LinkBtn_mytimetablestudentset')
        own_table.click()

        # Select Term
        select_term = Select(self.driver.find_element_by_name('lbWeeks'))
        select_term.select_by_index(self.term - 1)

        # Select days
        select_days = Select(self.driver.find_element_by_name('lbDays'))
        select_days.select_by_visible_text('All Week')

        # Select list timetable
        select_list = Select(self.driver.find_element_by_name('dlType'))
        select_list.select_by_visible_text('List Timetable')

        view_btn = self.driver.find_element_by_id('bGetTimetable')
        view_btn.click()

    def parse_timetable(self):
        """Convert timetable to ical."""
        six.print_('Parsing timetable...')

        tables = self.driver.find_elements_by_class_name('spreadsheet')

        for tindex, table in enumerate(tables):
            rows = table.find_elements_by_tag_name('tr')

            for rindex, row in enumerate(rows):
                if rindex == 0:
                    # First row is only the description of the columns
                    continue

                cols = row.find_elements_by_tag_name('td')

                # Find out weeks
                weeks = []

                if cols[COL_WEEK].text.startswith('Term'):
                    # Whole term
                    term = TERMS[self.term - 1]
                    weeks = WEEKS[term[0]:term[1]+1]

                else:
                    # Individual weeks
                    nums = cols[COL_WEEK].text.split(',')

                    for n in [a.strip() for a in nums]:
                        ran = n.split('-')

                        if len(ran) > 1:
                            # Range of weeks
                            weeks += WEEKS[int(ran[0]):int(ran[1])+1]

                        else:
                            # Regular number
                            weeks.append(WEEKS[int(ran[0])])

                # Create events
                for w in weeks:
                    start_time = TZONE.localize(
                        datetime.datetime.strptime(
                            cols[COL_START].text, '%H:%M'
                        )
                    )
                    start = w + DAYS[tindex]
                    start = start.replace(
                        hour=start_time.hour,
                        minute=start_time.minute
                    )

                    end_time = TZONE.localize(
                        datetime.datetime.strptime(
                            cols[COL_END].text, '%H:%M'
                        )
                    )
                    end = w + DAYS[tindex]
                    end = end.replace(
                        hour=end_time.hour,
                        minute=end_time.minute
                    )

                    event = Event(
                        name=cols[COL_DESC].text,
                        description='%s; %s' % (
                            cols[COL_TYPE].text,
                            cols[COL_STAFF].text
                        ),
                        location=cols[COL_ROOM].text,
                        begin=start,
                        end=end
                    )

                    self.ical.events.append(event)

    def start(self):
        """Start process."""
        self.login()
        self.access_timetable()
        self.parse_timetable()

        self.driver.close()

        # Write ics to file
        with open('out.ics', 'w') as ics:
            ics.writelines(self.ical)

def prepare():
    """Prepare a spider.

    This asks for username and password used to login to the portal at
    <https://portal.gre.ac.uk/>

    Returns:
        Spider instance.
    """
    # Ask for username
    username = six.moves.input('Portal username: ')

    # Ask for password
    password = getpass.getpass('Portal password (typed text does not appear): ')

    # Ask for term
    term = six.moves.input('Term to obtain calendar for [1-3]: ')

    if term not in ['1', '2', '3']:
        sys.exit('Term must be a value in the range [1-3]')

    # spider = Scrapper()
    spider = Scrapper(username=username, password=password, term=term)

    return spider


if __name__ == '__main__':
    spider = prepare()

    spider.start()
