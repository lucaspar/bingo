# Author: Jin Huang
# Initial version date: 10/08/2019

"""
Useful proxy list websites
    https://www.sslproxies.org/ (100 IPs all Https, tested)
    http://spys.one/en/https-ssl-proxy/ (90 IPs which are https, NOT TESTED YET)
    https://hidemy.name/en/proxy-list/?type=hs#list (Over 2000 https, NOT TESTED YET)
    https://www.proxy-list.download/HTTPS (1500 https, NOT TESTED YET)

"""

import os
import time
import random
import urllib3
import requests
import threading
from bs4 import BeautifulSoup
from time import time as timer
from fake_useragent import UserAgent
from multiprocessing.pool import ThreadPool
import os

urllib3.disable_warnings()

class BingoProxy(object):

    def __init__(self, concurrency=4, timeout=8):

        # set parameters
        self._PROXY_WEBSITES = ['https://www.sslproxies.org/']  # websites with proxy lists
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
        self._NB_THREAD = concurrency
        self._CALL_TIMEOUT = timeout
        self.proxy_list = []
        self._real_ip = None

        # define self._real_ip ip by making a request without proxy
        self.test_and_remove()

        # fetch proxy ips
        self._update_proxy_list()


    def request(self, url_list):

        # create a list if it is a single url
        if not isinstance(url_list, list):
            url_list = [url_list]

        # randomly select proxies from list
        proxy_selection = random.choices(self.proxy_list, k=len(url_list))
        req_list = list(zip(url_list, proxy_selection))

        # ============================================================
        #       The code for Heisenberg's uncertainty principle
        #
        #   Please don't remove the print statements below, otherwise
        #   the code will fail. In this case the variables must be
        #   observed to have their state defined, as the quantum
        #   physics states.
        # ============================================================
        for r in req_list:
            for n in r:
                print(n, end='\t\t')
            print()
        # ============================================================
        #   wrapping the zip() call above into list() solves it, but
        #   leaving the Heisemberg's uncertainty code is more fun
        # ============================================================

        # make concurrent requests
        pool = ThreadPool(self._NB_THREAD)
        results = pool.imap_unordered(self.make_proxy_request, req_list)

        return results


    def _update_proxy_list(self):
        """
        Updates local list of proxies from multiple public proxy services.

        :return:
            list: a list of available proxies
        """

        for proxy_website in self._PROXY_WEBSITES:

            # set it up
            proxies_no_filter = []
            user_agent = UserAgent()
            headers = {
                'User-Agent': user_agent.random,
            }

            # make requests
            try:
                response = requests.get(proxy_website, headers=headers, timeout=self._CALL_TIMEOUT, verify=False)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                proxies_table = soup.find(id='proxylisttable')

            except:
                print("Failed to get proxies from", proxy_website)
                continue

            if (proxy_website == 'https://www.sslproxies.org/'):
                # Find the proxies and feature in this website
                for row in proxies_table.tbody.find_all('tr'):
                    proxies_no_filter.append(
                        {
                            'ip': row.find_all('td')[0].string,
                            'port': row.find_all('td')[1].string,
                            'country': row.find_all('td')[3].string,
                            'https': row.find_all('td')[6].string == 'yes',
                        }
                    )

            #TODO: Add other proxy websites as well as the conditions for them


        # filter proxies that do not satisfy the conditions
        for proxy_ip in proxies_no_filter:
            if  proxy_ip['country'] in self._COUNTRY_LIST   and \
                proxy_ip['https']:

                self.proxy_list.append(proxy_ip)

            else:
                continue

        # cap proxy list to 5 IPs for local testing
        if os.getenv("ENVIRONMENT") == 'local':
            self.proxy_list = random.choices(self.proxy_list, k=5)

        print("Total %d proxies found" % len(self.proxy_list))
        return self.proxy_list


    def random_proxy(self):
        """
        :return: Random index for a proxy
        """
        return random.choice(range(len(self.proxy_list)))


    def make_proxy_request(self, url, proxy=None, enforce_proxy=False):
        """
        Makes an HTTP request using a proxy.

        :param
            url:            The document to be requested.
            proxy:          The proxy to intermediate the request. On error, a random proxy is selected.
            enforce_proxy:  If False (default), it will retry using another proxy.
        :return:
            response object, including content and HTTP status code.
        """

        # unpack first argument if necessary
        if isinstance(url, tuple):
            url, proxy = url

        # define proxy
        def proxy_protocols(proxy):
            return {
                'http': 'http://' + proxy['ip'] + ':' + proxy['port'],
                'https': 'https://' + proxy['ip'] + ':' + proxy['port'],
            } if proxy else {}

        response = None
        # make the request using the proxy
        try:
            response = requests.get(url, proxies=proxy_protocols(proxy), timeout=self._CALL_TIMEOUT, verify=False)
        except requests.exceptions.ProxyError as e:
            # retry with another proxy
            if not enforce_proxy:
                rp = random.choice(self.proxy_list)
                response = requests.get(url, proxies=proxy_protocols(rp), timeout=self._CALL_TIMEOUT, verify=False)
            else:
                raise e
        # or let parent function handle it
        except Exception as e:
            raise e

        return response


    def test_and_remove(self, proxy=None, test_only=False):
        """
        Tests a specific proxy and updates proxy list on failure.

        :param
            proxy:      The proxy dict to be tested with its IP and PORT
            test_only:  If True, does not remove on proxy failure
        :return:
            result: True if the proxy works, False if it does not work
        """
        proxy_works = False

        # removes from object list
        def remove_proxy(reason=""):
            try:
                print("\tRemoving", proxy['ip'], "Reason:", reason)
                self.proxy_list.remove(proxy)
            except ValueError:
                pass

        try:

            # try to fetch test url and read result
            ip_test_url = random.choice(self._IP_TEST_URLS)
            response = self.make_proxy_request(ip_test_url, proxy, enforce_proxy=True)
            response.raise_for_status()
            my_ip = response.text.replace('\n','')

            # proxy used
            if proxy is not None:

                # if proxy was really used, these must be different:
                proxy_works = my_ip != self._real_ip
                print("\tREAL_IP:", self._real_ip, 'EXTERNAL_IP:',  my_ip)

                # remove proxy
                if not test_only and not proxy_works:
                    remove_proxy(reason="Exposed real IP")

            # no proxy used: reset real ip
            else:
                self._real_ip = my_ip

        # if request failed for any reason, proxy will be removed from list
        except (requests.exceptions.HTTPError, Exception):
            if not test_only:
                remove_proxy(reason="HTTP Error")
            proxy_works = False

        return proxy_works


# ========================
#   USAGE EXAMPLE
# ========================
if __name__ == '__main__':

    # load environment variables
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='../.env')
    concurrency = int(os.getenv("CR_REQUESTS_CONCURRENCY", default=1))
    timeout     = int(os.getenv("CR_REQUESTS_TIMEOUT", default=20))
    print("Concurrency", concurrency, "Timeout", timeout)

    # other variables
    url_list    = ['https://en.wikipedia.org/wiki/Main_Page', 'https://www.yahoo.com/', 'https://cnn.com']

    # basic usage:
    bp = BingoProxy(concurrency=concurrency, timeout=timeout)
    responses = bp.request(url_list)
    for res in responses:
        print("\t" + str(res.status_code), res.url, res.elapsed, sep='\t\t')

    # testing proxies
    works = []
    print()
    print(len(bp.proxy_list), "proxies before testing")

    pl_copy = list(bp.proxy_list)
    for idx, proxy in enumerate(pl_copy):
        works.append(bp.test_and_remove(proxy))

    print(len(bp.proxy_list), "proxies after testing\n\n----\n")
    for p in bp.proxy_list:
        print(p['ip'])
