#!/usr/bin/env python
import os
import time
import random
import logging
import urllib3
import requests
import threading
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from time import time as timer
from fake_useragent import UserAgent
from colorlog import ColoredFormatter
from multiprocessing.pool import ThreadPool

urllib3.disable_warnings()

class BingoProxy(object):

    def __init__(self, concurrency=4, timeout=8, test=True):
        """
        Initialize proxy module.

        Args:
            concurrency:    number of maximum parallel requests
            timeout:        timeout for requests
            test:           if True, tests proxy list on initialization
        """

        # set parameters
        self._PROXY_SOURCES = [                 # websites with proxy lists
            'https://www.sslproxies.org/',
            # 'http://spys.one/en/https-ssl-proxy/',
            # 'https://hidemy.name/en/proxy-list/?type=hs',
            # 'https://www.proxy-list.download/HTTPS',
        ]
        self._IP_TEST_URLS = [                                  # urls to probe ip addresses
            'https://ident.me/',
            'http://icanhazip.com',
            'https://ip.seeip.org/',
            'https://ifconfig.co/ip',
            'https://api.ipify.org/',
            'https://ipecho.net/plain',
            'http://plain-text-ip.com/',
            'https://wtfismyip.com/text',
            'https://myexternalip.com/raw',
        ]
        self._COUNTRY_LIST = [
            'United States', 'USA', 'US', 'Canada', 'Mexico', 'Brazil',
            'United Kingdom', 'UK', 'Belarus', 'Germany', 'Czech Republic',
            'Spain', 'France', 'Iceland', 'Poland', 'Ukraine',
            'France', 'Hungary', 'Russia',
        ]
        self.proxy_list = []            # list of valid proxies
        self._MIN_PROXY_THRESHOLD = 10  # min number of proxies to maintain
        self._LOCAL_PROXY_CAP = 20      # cap for local executions (> _MIN_PROXY_THRESHOLD)
        self._NB_THREAD = concurrency   # number of concurrent connections
        self._CALL_TIMEOUT = timeout    # timeout for each request
        self._real_ip = None            # public IP address of this machine

        # setup logging
        self._config_logging()

        # define self._real_ip ip by making a request without proxy
        if test:
            self._test_and_remove()

        # fetch proxy ips
        self._update_plist()


    def request(self, url_list):

        # create a list if it is a single url
        if not isinstance(url_list, list):
            url_list = [url_list]

        # randomly select proxies from list
        proxy_selection = random.choices(self.proxy_list, k=len(url_list))
        req_list = list(zip(url_list, proxy_selection))

        # make concurrent requests
        pool = ThreadPool(self._NB_THREAD)
        results = pool.imap_unordered(self._proxy_request, req_list)

        return results


    def _remove_proxy(self, proxy, reason=""):
        """
        Removes a proxy from list.

        Args:
            proxy:  Proxy element to be removed
            reason: Reason of removal (for logging)
        """
        try:
            self.proxy_list.remove(proxy)
            self.logger.info("{} proxy was removed: {}".format(proxy['ip'], reason))
        except ValueError:
            pass


    def _test_and_remove(self, proxy=None, test_only=False):
        """
        Tests a specific proxy and updates proxy list on failure.

        Args:
            proxy:      The proxy dict to be tested with its IP and PORT
            test_only:  If True, does not remove on proxy failure
        Returns:
            result:     True if the proxy works, False if it does not work
        """
        proxy_works = False

        try:

            # try to fetch test url and read result
            ip_test_url = random.choice(self._IP_TEST_URLS)
            response = self._proxy_request(ip_test_url,
                                                proxy,
                                                enforce_proxy=True)
            response.raise_for_status()
            my_ip = response.text.replace('\n', '')

            # proxy used
            if proxy is not None:

                # if proxy was really used, these must be different:
                proxy_works = my_ip != self._real_ip

                # remove proxy
                if not test_only and not proxy_works:
                    self.logger.info("REAL_IP: {} : EXTERNAL_IP: {}".format(
                        self._real_ip, my_ip))
                    self._remove_proxy(proxy, reason="Exposed real IP")

            # no proxy used: reset real ip
            else:
                self._real_ip = my_ip

        # if request failed for any reason, proxy will be removed from list
        except (requests.exceptions.HTTPError, Exception):
            if not test_only:
                self._remove_proxy(proxy, reason="HTTP Error")
            proxy_works = False

        return proxy_works


    def _update_plist(self):
        """
        Updates local list of proxies from public proxy sources.

        Returns:
            list: a list of available proxies
        """

        for proxy_source in self._PROXY_SOURCES:

            # set up user agent
            proxies_no_filter = []
            user_agent = UserAgent()
            headers = {
                'User-Agent': user_agent.random,
            }

            # make requests
            try:
                response = requests.get(proxy_source, headers=headers, timeout=self._CALL_TIMEOUT, verify=False)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                proxies_table = soup.find(id='proxylisttable')

            except:
                self.logger.warn("Failed to get proxies from {}".format(proxy_source))
                continue

            if (proxy_source == 'https://www.sslproxies.org/'):
                # get public servers from this source
                for row in proxies_table.tbody.find_all('tr'):
                    proxies_no_filter.append(
                        {
                            'ip': row.find_all('td')[0].string,
                            'port': row.find_all('td')[1].string,
                            'country': row.find_all('td')[3].string,
                            'https': row.find_all('td')[6].string == 'yes',
                        }
                    )

        # filter out proxies that do not satisfy the conditions
        for proxy_ip in proxies_no_filter:
            if  proxy_ip['country'] in self._COUNTRY_LIST   and \
                proxy_ip['https']:

                self.proxy_list.append(proxy_ip)
            else:
                continue

        # cap proxy list to 15 IPs for local testing
        if os.getenv("ENVIRONMENT") == 'local':
            self.logger.info("Local env: using only {} proxies.".format(self._LOCAL_PROXY_CAP))
            self.proxy_list = random.choices(self.proxy_list, k=self._LOCAL_PROXY_CAP)

        self.logger.info("Updated proxy list: {} proxies available".format(len(self.proxy_list)))
        return self.proxy_list


    def _proxy_request(self, url, proxy=None, enforce_proxy=False):
        """
        Makes an HTTP request using a proxy.

        Args:
            url:            The document to be requested.
            proxy:          The proxy to intermediate the request. On error, a random proxy is selected.
            enforce_proxy:  If False (default), it will retry using another proxy.
        Returns:
            response object, including content and HTTP status code, or None if unsuccessful.
        """

        # unpack first argument if necessary
        if isinstance(url, tuple):
            if len(url) == 2:
                url, proxy = url
            elif len(url) == 3:
                url, proxy, enforce_proxy = url

        # define proxy
        def proxy_protocols(proxy):
            return {
                'http': 'http://' + proxy['ip'] + ':' + proxy['port'],
                'https': 'https://' + proxy['ip'] + ':' + proxy['port'],
            } if proxy else {}

        response = None
        # try different proxies until it works
        while True:

            try:
                TEMP_DISABLED = False
                if TEMP_DISABLED:
                    response = requests.get(url, timeout=self._CALL_TIMEOUT, verify=False)
                else:
                    response = requests.get(url, proxies=proxy_protocols(proxy), timeout=self._CALL_TIMEOUT, verify=False)
                if response:
                    self.logger.debug("Request succeeded: {}".format(url))
                    break

            except requests.exceptions.ProxyError as e:

                # proxy failed, remove from list
                self._remove_proxy(proxy, reason="Proxy has failed")

                # fetch more proxy servers if below threshold
                if len(self.proxy_list) < self._MIN_PROXY_THRESHOLD:
                    self._update_plist()

                # if proxy is enforced, log and return None response
                if enforce_proxy:
                    self.logger.error("Proxy error: {}".format(str(e)))
                    break
                # else, retry with another random proxy
                else:
                    self.logger.info("{} proxy failed, retrying request...".format(proxy['ip']))
                    proxy = random.choice(self.proxy_list)

            except requests.exceptions.ConnectTimeout as e:
                self.logger.warn("Request timeout. Retrying another proxy... \n{}".format(str(e)))

            except Exception as e:
                self.logger.warn("Unknown error: {}".format(str(e)))

        return response


    def _config_logging(self, demo=False):
        """
        Configure logging format and handler.

        Args:
            demo: if True, logging demonstration is executed.
        """

        # get formatting string
        FORMAT = os.environ.get(
            "LOGGING_FORMAT",
            '%(log_color)s[%(asctime)s] %(module)-12s %(funcName)s(): %(message)s %(reset)s'
        )

        # set
        LOG_LEVEL = logging.DEBUG
        stream = logging.StreamHandler()
        stream.setLevel(LOG_LEVEL)
        stream.setFormatter(ColoredFormatter(FORMAT))

        self.logger = logging.getLogger('main')
        self.logger.setLevel(LOG_LEVEL)
        self.logger.addHandler(stream)


# ===============
#  USAGE EXAMPLE
# ===============
if __name__ == '__main__':

    # load environment variables
    load_dotenv(dotenv_path='../.env')
    concurrency = int(os.getenv("CR_REQUESTS_CONCURRENCY", default=1))
    timeout     = int(os.getenv("CR_REQUESTS_TIMEOUT", default=20))
    print("Concurrency", concurrency, "Timeout", timeout)

    # other variables
    url_list = [
        'https://en.wikipedia.org/wiki/Main_Page',
        'https://www.youtube.com/',
        'https://www.foxnews.com/',
        'https://www.reddit.com/',
        'https://www.github.com/',
        'https://www.yahoo.com/',
        'https://www.quora.com/',
        'https://www.nd.edu/',
        'https://cnn.com/',
    ]

    # basic usage:
    bp = BingoProxy(concurrency=concurrency, timeout=timeout, test=False)
    responses = bp.request(url_list)
    for res in responses:
        print("\t" + str(res.status_code), res.url, res.elapsed, sep='\t')

    TESTING = False
    if TESTING:

        # testing proxies
        works = []
        print()
        print(len(bp.proxy_list), "proxies before testing")

        pl_copy = list(bp.proxy_list)
        for idx, proxy in enumerate(pl_copy):
            works.append(bp._test_and_remove(proxy))

        print(len(bp.proxy_list), "proxies after testing\n\n----\n")
        for p in bp.proxy_list:
            print(p['ip'])
