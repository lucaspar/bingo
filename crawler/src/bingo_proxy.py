# Wrap the methods in "proxy_rotation.py" into a class

# Author: Jin Huang
# Initial version date: 10/08/2019

"""
Useful proxy list websites
    https://www.sslproxies.org/ (100 IPs all Https, tested)
    http://spys.one/en/https-ssl-proxy/ (90 IPs which are https, NOT TESTED YET)
    https://hidemy.name/en/proxy-list/?type=hs#list (Over 2000 https, NOT TESTED YET)
    https://www.proxy-list.download/HTTPS (1500 https, NOT TESTED YET)

"""

import time
import random
import threading
from bs4 import BeautifulSoup
from time import time as timer
from fake_useragent import UserAgent
from urllib.request import Request, urlopen
from multiprocessing.pool import ThreadPool

###############################################
# Define some parameters
###############################################
# Proxies from these countries will be allowed
COUNTRY_LIST = ['United States', 'United Kingdom', 'Belarus',
                'Czech Republic', 'Spain', 'Brazil', 'France',
                'Canada', 'Poland', 'Armenia', 'Ukraine', 'France',
                'Mexico', 'Georgia', 'Hungary']
PROXY_WEBSITES = ['https://www.sslproxies.org/']
TARGET_URL = 'http://icanhazip.com'
STEP_RANDOM_PROXY = 2
NB_REQUESTS = 4
NB_THREAD = 14
CALL_TIMEOUT = 8
test_single = False

###############################################
# Define the class
###############################################
class  bingo_proxy(object):
    def retrieve_proxy_ips(self, proxy_website_list):
        """
        Retrieve the proxy lists from multiple websites.

        :param
            proxy_website: the list for the proxy websites
        :return:
            list: a list of available proxies
        """

        for proxy_website in proxy_website_list:
            user_agent = UserAgent()
            proxies_no_filter = []
            proxies = []

            proxies_req = Request(proxy_website)
            proxies_req.add_header('User-Agent', user_agent.random)
            proxies_doc = urlopen(proxies_req, timeout=CALL_TIMEOUT).read().decode('utf8')

            soup = BeautifulSoup(proxies_doc, 'html.parser')
            proxies_table = soup.find(id='proxylisttable')

            if (proxy_website == 'https://www.sslproxies.org/'):
                # Find the proxies and feature in this website
                for row in proxies_table.tbody.find_all('tr'):
                    proxies_no_filter.append({
                        'ip': row.find_all('td')[0].string,
                        'port': row.find_all('td')[1].string,
                        'country': row.find_all('td')[3].string,
                        'https': row.find_all('td')[6].string})

            #TODO: Add other proxy websites as well as the conditions for them


        # Filter the whole list and only get those satisfy our conditions
        for proxy_ip in proxies_no_filter:
            if (proxy_ip['country'] in COUNTRY_LIST) and (proxy_ip['https'] == 'yes'):
                proxies.append(proxy_ip)
            else:
                pass

        # Print the number of proxies we have and return
        print("Total %d proxies found" % len(proxies))

        return proxies

    def random_proxy(self, proxies):
        """
        :param proxies: A proxy list
        :return: Random index for a proxy
        """
        return random.choice(range(len(proxies)))


    def test_single_process_proxy(self, proxies,
                                nb_request=NB_REQUESTS,
                                test_url=TARGET_URL ,
                                step_for_random_proxy=STEP_RANDOM_PROXY):
        """
        Testing the proxies in the filtered list
        based on a random choice using a single process.

        :param
            proxy: The list of filtered proxies
            nb_request: Number of total requests we want each process to make
            test_url: The target URL to which we send the request
            step_for_random_proxy: Number of steps for changing to next proxy

        :return:
            result: True if the proxy works, False if it does not work
        """
        print(proxies)

        proxy_index = self.random_proxy(proxies)
        proxy = proxies[proxy_index]

        # Proxy rotation
        for n in range(1, nb_request + 1):
            req = Request(test_url)
            req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')

            # Every certain number of requests, generate a new proxy
            if n % step_for_random_proxy == 0:
                proxy_index = self.random_proxy(proxies)
                proxy = proxies[self.random_proxy(proxies)]
                req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
            else:
                pass

            # Intercept broken proxies and delete them from the list and notice the user
            try:
                my_ip = urlopen(req, timeout=CALL_TIMEOUT).read().decode('utf8')
                print('#' + str(n) + ': ' + my_ip)
                # result.append(True)

            except:  # If error, delete this proxy and find another one
                del proxies[proxy_index]
                print('Proxy ' + proxy['ip'] + ':' + proxy['port'] + ' is deleted.')
                proxy = proxies[self.random_proxy(proxies)]
                # req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
                # result.append(False)

        # return result

    def test_multi_process_proxy(self, proxy,
                                nb_request=NB_REQUESTS,
                                test_url=TARGET_URL ,
                                step_for_random_proxy=STEP_RANDOM_PROXY):
        """
        Testing the proxies in the filtered list
        based on a random choice using multi-process.

        :param
            proxy: The list of filtered proxies
            nb_request: Number of total requests we want each process to make
            test_url: The target URL to which we send the request
            step_for_random_proxy: Number of steps for changing to next proxy

        :return:
            result: True if the proxy works, False if it does not work
        """
        # print(threading.get_ident(), id(proxies))
        result = []

        # Proxy rotation
        for n in range(1, nb_request + 1):
            req = Request(test_url)
            req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')

            # # Every certain number of requests, generate a new proxy
            # if n % step_for_random_proxy == 0:
            #     proxy_index = random_proxy(proxies)
            #     proxy = proxies[proxy_index]
            #     req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
            # else:
            #     pass

            # Intercept broken proxies and delete them from the list and notice the user
            try:
                my_ip = (urlopen(req, timeout=CALL_TIMEOUT).read().decode('utf8')).replace('\n','')
                print('#', n, '-', my_ip, '==',  proxy['ip'])
                result.append(True)

            except Exception as err:  # If error, delete this proxy and find another one
                # del proxies[proxy_index]
                print("Exception:", err)
                # print('Proxy ' + proxy['ip'] + ':' + proxy['port'] + ' is deleted.')
                # proxy_index = random_proxy(proxies)
                # proxy = proxies[proxy_index]
                # # req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
                result.append(False)

        return result


###############################################
# Main function
###############################################
if __name__ == '__main__':
    # 0. Creat an object using the class
    bingo = bingo_proxy()
    # 1. Get the proxy list from the websites.
    proxy_list = bingo.retrieve_proxy_ips(proxy_website_list=PROXY_WEBSITES)
    print("[INFO] Found %d proxies" % len(proxy_list))

    # Test single process first
    if test_single == True:
        bingo.test_single_process_proxy(proxies=proxy_list)

    # # 2. Test the proxies with multi-process
    print("THREADS ", NB_THREAD)
    pool = ThreadPool(NB_THREAD)
    results = pool.imap_unordered(bingo.test_multi_process_proxy, proxy_list)

    # 4. Get the result
    for status in results:
        print(status)
