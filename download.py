import sys
import requests
import re

default_bar_len = 60
number_of_retries = 3
default_timeout = 30
chunk_size = 1024


class ProgressBar():
    """Basic text progress bar"""

    def __init__(self, total):
        """Initializes with total"""
        self.total = total
        self.bar_len = default_bar_len
        self.progress = 0
        
    def update(self, step = 1):
        """Increments progress by step and displays the percent as a bar"""
        self.progress += step
        if self.total == 0:
            sys.stdout.write(_('Progress: %.1fK') % (self.progress / 1024.0) + '\r')
        else:
            if self.progress > self.total: self.progress = self.total
            self.percent = round(100.0 * self.progress / float(self.total), 1)
            filled_len = int(round(self.percent) * self.bar_len / 100.0)
            bar = '#' * filled_len + '-' * (self.bar_len - filled_len)
            sys.stdout.write('[%s] %s%%\r' % (bar, self.percent))
        sys.stdout.flush()

def get_response(url, stream=False):
    """Try many times to get a http response or raise exception"""
    for i in range(number_of_retries):
        response = requests.get(url, stream=stream, timeout=default_timeout)
        if response.status_code == requests.codes.ok:
            return response
    response.raise_for_status()

def wget(url, filename):
    """Download url to filename"""
    response = get_response(url, stream=True)
    total = 0
    if 'Content-Length' in response.headers:
        total = int(response.headers['Content-Length'])
    progress = ProgressBar(total)
    with open(filename, "wb") as f:
        for chunk in response.iter_content(chunk_size):
            progress.update(chunk_size)
            f.write(chunk)
