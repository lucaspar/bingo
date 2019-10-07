# Use a free public proxy list for python requests
# Find good proxy services
# Run some tests on these options

# Author: Jin Huang
# Initial version date: 10/04/2019
# Reference for rotating proxies: https://codelike.pro/create-a-crawler-with-rotating-ip-proxy-in-python/

"""
Useful proxy list websites
    https://www.sslproxies.org/ (100 IPs all Https, tested)
    http://spys.one/en/https-ssl-proxy/ (90 IPs which are https, NOT TESTED YET)
    https://hidemy.name/en/proxy-list/?type=hs#list (Over 2000 https, NOT TESTED YET)
    https://www.proxy-list.download/HTTPS (1500 https, NOT TESTED YET)

"""

from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import random
from multiprocessing.pool import ThreadPool
from time import time as timer
from urllib.request import urlopen
import threading
import time

###############################################
# Define some parameters
###############################################
# Proxies from these countries will be allowed
country_list = ['United States', 'United Kingdom', 'Belarus',
                'Czech Republic', 'Spain', 'Brazil', 'France',
                'Canada', 'Poland', 'Armenia', 'Ukraine', 'France',
                'Mexico', 'Georgia', 'Hungary']
proxy_websites = ['https://www.sslproxies.org/']
nb_thread = 2
nb_requests = 4
step_random_proxy = 2
target_url = 'http://icanhazip.com'

###############################################
# Define the functions
###############################################
def retrieve_proxy_ips(proxy_website_list):
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
        proxies_doc = urlopen(proxies_req).read().decode('utf8')

        soup = BeautifulSoup(proxies_doc, 'html.parser')
        proxies_table = soup.find(id='proxylisttable')

        if (proxy_website == 'https://www.sslproxies.org/'):
            # Find the proxies and feature in this website
            print("[INFO] Start retrieving proxies from https://www.sslproxies.org/")
            for row in proxies_table.tbody.find_all('tr'):
                proxies_no_filter.append({
                    'ip': row.find_all('td')[0].string,
                    'port': row.find_all('td')[1].string,
                    'country': row.find_all('td')[3].string,
                    'https': row.find_all('td')[6].string})

        #TODO: Add other proxy websites as well as the conditions for them


    # Filter the whole list and only get those satisfy our conditions
    print("[INFO] Filtering the proxy list...")

    for proxy_ip in proxies_no_filter:
        if (proxy_ip['country'] in country_list) and (proxy_ip['https'] == 'yes'):
            proxies.append(proxy_ip)
        else:
            pass

    return proxies

def random_proxy(proxies):
    """
    :param proxies: A proxy list
    :return: Random index for a proxy
    """
    return random.randint(0, len(proxies) - 1)


def test_single_process_proxy(proxies,
                            nb_request=nb_requests,
                            test_url=target_url ,
                            step_for_random_proxy=step_random_proxy):
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

    proxy_index = random_proxy(proxies)
    proxy = proxies[proxy_index]

    # Proxy rotation
    for n in range(1, nb_request + 1):
        req = Request(test_url)
        req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')

        # Every certain number of requests, generate a new proxy
        if n % step_for_random_proxy == 0:
            proxy_index = random_proxy(proxies)
            proxy = proxies[proxy_index]
            req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
        else:
            pass

        # Intercept broken proxies and delete them from the list and notice the user
        try:
            my_ip = urlopen(req).read().decode('utf8')
            print('#' + str(n) + ': ' + my_ip)
            # result.append(True)

        except:  # If error, delete this proxy and find another one
            del proxies[proxy_index]
            print('Proxy ' + proxy['ip'] + ':' + proxy['port'] + ' is deleted.')
            proxy_index = random_proxy(proxies)
            proxy = proxies[proxy_index]
            # req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
            # result.append(False)

    # return result

def test_multi_process_proxy(proxies,
                            nb_request=nb_requests,
                            test_url=target_url ,
                            step_for_random_proxy=step_random_proxy):
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

    result = []

    proxy_index = random_proxy(proxies)
    proxy = proxies[proxy_index]

    # Proxy rotation
    for n in range(1, nb_request + 1):
        req = Request(test_url)
        req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')

        # Every certain number of requests, generate a new proxy
        if n % step_for_random_proxy == 0:
            proxy_index = random_proxy(proxies)
            proxy = proxies[proxy_index]
            req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
        else:
            pass

        # Intercept broken proxies and delete them from the list and notice the user
        try:
            my_ip = urlopen(req).read().decode('utf8')
            print('#' + str(n) + ': ' + my_ip)
            result.append(True)

        except:  # If error, delete this proxy and find another one
            del proxies[proxy_index]
            print('Proxy ' + proxy['ip'] + ':' + proxy['port'] + ' is deleted.')
            proxy_index = random_proxy(proxies)
            proxy = proxies[proxy_index]
            # req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
            result.append(False)

    return result

###############################################
# Main function
###############################################
if __name__ == '__main__':
    # 1. Get the proxy list from the websites.
    proxy_list = retrieve_proxy_ips(proxy_website_list=proxy_websites)
    print("[INFO] Found %d proxies" % len(proxy_list))

    # Test single process first
    test_single_process_proxy(proxies=proxy_list)

    # ?. Get number of process and proxies we need for each thread
    """
    multi_process_proxy_list = []

    for i in range(nb_thread):
        proxy_index = random_proxy(proxy_list)
        proxy = proxy_list[proxy_index]
        multi_process_proxy_list.append(proxy)
    """

    # # 2. Test the proxies with multi-process
    results = ThreadPool(nb_thread).imap_unordered(test_multi_process_proxy,
                                                   proxy_list)

    # 4. Get the result
    for status in results:
        print(status)

