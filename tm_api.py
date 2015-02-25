import json
import urllib
import requests
import requests_oauthlib
from pprint import pprint

import secrets.trademe


class ImproperlyConfigured(Exception):
    pass


class TrademeAPI(object):
    api_url = None
    consumer_key = None
    consumer_secret = None
    oauth_token = None
    oauth_secret = None

    api = None

    def authenticate(self):
        if not self.api_url:
            raise ImproperlyConfigured(
                "No api_url. Are you using the base class by mistake?"
            )

        # https://requests-oauthlib.readthedocs.org/en/latest/
        self.api = requests_oauthlib.OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.oauth_token,
            resource_owner_secret=self.oauth_secret
        )
        return self.api

    def get_api_response(self, endpoint, response_format=None, payload=None):
        if not self.api:
            self.authenticate()

        if not response_format:
            response_format = "json"

        url = "{}{}.{}".format(
            self.api_url,
            endpoint,
            response_format
        )
        return self.api.get(url, params=payload)

    def search_residential(self, payload=None):
        # http://developer.trademe.co.nz/api-reference/search-methods/residential-search/
        endpoint = "/Search/Property/Residential"
        return self.get_api_response(endpoint, payload=None)


class TrademeSandbox(TrademeAPI):
    api_url = "https://api.tmsandbox.co.nz/v1"


class Trademe(TrademeAPI):
    api_url = "https://api.trademe.co.nz/v1"


trademe = TrademeSandbox()
trademe.consumer_key = secrets.trademe.TRADEME_CONSUMER_KEY
trademe.consumer_secret = secrets.trademe.TRADEME_CONSUMER_SECRET
trademe.oauth_token = secrets.trademe.TRADEME_OAUTH_TOKEN
trademe.oauth_secret = secrets.trademe.TRADEME_OAUTH_SECRET

payload = {
    'rows': 1
}
listings = trademe.search_residential()

if listings.status_code == 200:
    data = json.loads(listings.text)
    for result in data.get('List', []):
        print "{}, {}".format(
            result.get('Address', ""),
            result.get('PriceDisplay', "")
        )

