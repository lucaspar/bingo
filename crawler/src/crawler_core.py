from bs4 import BeautifulSoup
import requests
import requests.exceptions
from urllib.parse import urlsplit 
from urllib.parse import urlparse
from collections import deque
import re


url = "https://www3.nd.edu/~cpoellab/teaching/cse60641/"
new_urls = deque([url])
processed_urls = set()
local_urls = set()
foreign_urls = set()
broken_urls = set()

while len(new_urls): 
    url = new_urls.popleft()
    processed_urls.add(url)
    print("Processing %s" % url)
    try: 
        response = requests.get(url)
    except(requests.exceptions.MissingSchema,
           requests.exceptions.ConnectionError,
           requests.exceptions.InvalidURL,
           requests.exceptions.InvalidSchema):
        broken_urls.add(url)
        continue 
		
    parts = urlsplit(url)
    base = "{0.netloc}".format(parts)
    strip_base = base.replace("www.", "")
    base_url = "{0.scheme}://{0.netloc}".format(parts)
    path = url[:url.rfind('/')+1] if '/' in parts.path else url
		
    soup = BeautifulSoup(response.text, "lxml")
		
    for link in soup.find_all('a'): 
        anchor = link.attrs["href"] if "href" in link.attrs else ''
		
        if anchor.startswith('/'): 
            local_link = base_url + anchor 
            local_urls.add(local_link) 
        elif strip_base in anchor: 
            local_urls.add(anchor)
        elif not anchor.startswith('http'): 
            local_link = path + anchor 
            local_urls.add(local_link)
        else: 
            foreign_urls.add(anchor)
		
        for i in local_urls: 
            if not i in new_urls and not i in processed_urls: 
                new_urls.append(i)
#           if not link in new_urls and not link in processed_urls:
#               new.urls.append(link)

