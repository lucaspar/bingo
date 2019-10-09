import re
import requests
from bs4 import BeautifulSoup
from collections import deque
from urllib.parse import urlsplit, urljoin

url = "https://en.wikipedia.org/wiki/Main_Page"
new_urls = deque([url])
processed_urls = set()
foreign_urls = set()
broken_urls = set()
local_urls = set()

# TODO: submit found URLs to balancer; request new URLs from it.
while len(new_urls):

    # remove URL from queue
    url = new_urls.popleft()
    processed_urls.add(url)
    print("Processing %s" % url)

    # make request
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        # TODO: save fetched document to S3
    except(requests.exceptions.MissingSchema,
           requests.exceptions.ConnectionError,
           requests.exceptions.InvalidURL,
           requests.exceptions.InvalidSchema):
        # TODO: add http code to send balancer
        broken_urls.add(url)
        continue

    # split url into parts
    url_parts = urlsplit(url)
    base_url = "{0.scheme}://{0.netloc}".format(url_parts)
    path = url[:url.rfind('/') + 1] if '/' in url_parts.path else url

    for link in soup.find_all('a'):

        # no hyperlink
        if "href" not in link.attrs:
            continue
        anchor = link.attrs["href"]

        # turn relative urls into absolute
        if anchor.startswith('/'):
            absolute = urljoin(base_url, anchor)
        elif not anchor.startswith('http'):
            absolute = urljoin(path, anchor)
        else:
            absolute = anchor

        absolute_parts = urlsplit(absolute)

        # Cases in which the URL will be discarded:
        #   If `absolute` is not a valid URL : TODO
        #   If `absolute_parts.scheme` is not known (http/https)
        #   If `absolute` has a file extension and it is not of interest
        known_schem = ["http", "https"]
        known_exten = ["html", "php", "jsp", "aspx"]
        last_words = absolute_parts.path.split('/')[-1].split('.')
        if absolute_parts.scheme not in known_schem or \
            len(last_words) > 1 and (last_words[-1] not in known_exten):
            continue

        # differ local and foreign urls (other domain/subdomain)
        if url_parts.netloc == absolute_parts.netloc:
            local_urls.add(absolute)
        else:
            foreign_urls.add(absolute)

        # check if new url has never been seen
        if (absolute not in new_urls) and \
            (absolute not in processed_urls):
            new_urls.append(absolute)

    print("URLs:\t\tNew:{}\tLocal: {}\tForeign: {}\tProcessed: {}"\
        .format(len(new_urls), len(local_urls), len(foreign_urls), len(processed_urls)))
