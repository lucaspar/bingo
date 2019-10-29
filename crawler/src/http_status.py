# What to do after receiving different HTTP status codes

# configure the action functions as needed:
def default_action(url, res):
    print("Default")

def do_nothing(url, res):
    print("Doing nothing")

def redirect(url, res):
    print("Redirecting")

def drop(url, res):
    print("Dropping URL")

def try_again(url, res):
    print("Trying again")

# look-up list of known http status codes:
HTTP_STATUS_CODES = {

    # 1xx are information status.
    #   These are commented out because in normal circumnstances they won't be returned
    # 100: do_nothing,  # Continue / Request received, please continue
    # 101: do_nothing,  # Switching Protocols / Switching to new protocol; obey Upgrade header

    # 2xx means okay
    200: do_nothing,  # OK / Request fulfilled, document follows
    201: do_nothing,  # Created / Document created, URL follows
    202: do_nothing,  # Accepted / Request accepted, processing continues off-line
    203: do_nothing,  # Non-Authoritative Information / Request fulfilled from cache
    204: do_nothing,  # No Content / Request fulfilled, nothing follows
    205: do_nothing,  # Reset Content / Clear input form for further input.
    206: do_nothing,  # Partial Content / Partial content follows.

    # 3xx are redirects
    300: redirect,  # Multiple Choices / Object has several resources -- see URI list
    301: redirect,  # Moved Permanently / Object moved permanently -- see URI list
    302: redirect,  # Found / Object moved temporarily -- see URI list
    303: redirect,  # See Other / Object moved -- see Method and URL list
    304: redirect,  # Not Modified / Document has not changed since given time
    305: redirect,  # Use Proxy / You must use proxy specified in Location to access this  / resource.
    307: redirect,  # Temporary Redirect / Object moved temporarily -- see URI list

    # 4xx are request errors
    400: drop,  # Bad Request / Bad request syntax or unsupported method
    401: drop,  # Unauthorized / No permission -- see authorization schemes
    402: drop,  # Payment Required / No payment -- see charging schemes
    403: drop,  # Forbidden / Request forbidden -- authorization will not help
    404: drop,  # Not Found / Nothing matches the given URI
    405: drop,  # Method Not Allowed / Specified method is invalid for this server.
    406: drop,  # Not Acceptable / URI not available in preferred format.
    407: drop,  # Proxy Authentication Required / You must authenticate with  / this proxy before proceeding.
    408: drop,  # Request Timeout / Request timed out; try again later.
    409: drop,  # Conflict / Request conflict.
    410: drop,  # Gone / URI no longer exists and has been permanently removed.
    411: drop,  # Length Required / Client must specify Content-Length.
    412: drop,  # Precondition Failed / Precondition in headers is false.
    413: drop,  # Request Entity Too Large / Entity is too large.
    414: drop,  # Request-URI Too Long / URI is too long.
    415: drop,  # Unsupported Media Type / Entity body in unsupported format.
    416: drop,  # Requested Range Not Satisfiable / Cannot satisfy request range.
    417: drop,  # Expectation Failed / Expect condition could not be satisfied.

    # 5xx are server errors
    500: try_again,  # Internal Server Error / Server got itself in trouble
    501: try_again,  # Not Implemented / Server does not support this operation
    502: try_again,  # Bad Gateway / Invalid responses from another server/proxy.'
    503: try_again,  # Service Unavailable' / 'The server cannot process the request due to a high load'
    504: try_again,  # Gateway Timeout / The gateway server did not receive a timely response
    505: try_again,  # HTTP Version Not Supported / Cannot fulfill request.

}

# Usage example:
def sample():

    import requests

    # test all status codes
    urls = []
    for code in HTTP_STATUS_CODES.keys():
        urls.append("https://httpstat.us/" + str(code))

    # unknown status
    urls.append("https://httpstat.us/418")

    # run actions
    for url in urls:
        response = requests.get(url)
        try:
            print(url, response)
            HTTP_STATUS_CODES[response.status_code](url, response)  # <= use the look-up above like this
        except KeyError:
            print(url, "UNKNOWN status:", response.status_code)
            default_action(url, response)

if __name__ == "__main__":
    sample()
