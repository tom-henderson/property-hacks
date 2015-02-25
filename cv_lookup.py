# -*- coding: utf-8 -*-
import requests
import mechanize
import cookielib
from bs4 import BeautifulSoup as bs
import json
import urllib

ILLEGAL_CHARS = ","


def address_search(address):
    """
    Searches an address for possible matches.
    Returns a list of matches.
    """
    payload = {
        'f': 'json',
        'where': "SEARCHADDRESS = '1 Bellcroft Place Belmont'",
        'returnGeometry': 'true',
        'spatialRel': 'esriSpatialRelIntersects',
        'outFields': 'SEARCHADDRESS',
    }
    url = "http://maps.aucklandcouncil.govt.nz/ArcGIS/rest/services/Applications/ACWebsite/MapServer/2/query"
    json_data = requests.get(url, params=payload).text
    data = json.loads(json_data)

    geometry = {
        "x": data['features'][0]['geometry']['x'],
        "y": data['features'][0]['geometry']['y'],
        "spatialReference": data['spatialReference'],
    }

    payload = {
        'f': "json",
        'where': "",
        'returnGeometry': "false",
        'spatialRel': "esriSpatialRelIntersects",
        'geometry': json.dumps(geometry),
        'geometryType': "esriGeometryPoint",
        'inSR': "2193",
        'outFields': "VALUATIONREF",
        'outSR': "2193",
    }

    url = "http://maps.aucklandcouncil.govt.nz/ArcGIS/rest/services/Applications/ACWebsite/MapServer/3/query"
    json_data = requests.get(url, params=payload).text
    data = json.loads(json_data)

    # for match in data['features']:
    #     print "Found possible match: {}, {}".format(
    #         match['attributes']['VALUATIONREF'],
    #         match['attributes']['FORMATTEDADDRESS']
    #     )

    return [{'vr': match['attributes']['VALUATIONREF'],
            'pa': match['attributes']['FORMATTEDADDRESS']}
            for match in data['features']]


def get_valuation_number(address):
    """
    Takes an address and returns the valuation number for the latest
    council valuation.
    If the lookup fails, calls address_search() to look for possible matches.
    """
    if not address or address == '':
        return False

    url = 'http://www.aucklandcouncil.govt.nz/_vti_bin/propertylocator.asmx'
    soap_template = u"""<?xml version="1.0" encoding="utf-8"?>
                        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                        <soap:Body><DoValuationAddressSearch xmlns="http://www.manukau.govt.nz">
                        <searchString>{}</searchString>
                        <resultCount>{}</resultCount>
                        <wsUrl>http://mapws.aucklandcouncil.govt.nz/ServiceCentre/ARCSearchService.svc/SearchSoap</wsUrl>
                        <proxyBypassAddress></proxyBypassAddress>
                        <proxyAddress></proxyAddress>
                        </DoValuationAddressSearch>
                        </soap:Body>
                        </soap:Envelope>"""
    numberOfItemsToReturn = 25

    soapMessage = soap_template.format(
        address.replace(ILLEGAL_CHARS, ""),
        numberOfItemsToReturn,
    )

    message = soapMessage.encode('utf8')

    headers = {
        'Content-Type': "text/xml; charset=utf-8"
    }

    response = requests.post(
        url=url,
        headers=headers,
        data=message,
        verify=False
    )

    if response.status_code != 200:
        return None

    # print response.text
    soup = bs(response.text)

    if soup.find('valuationnumber').text:
        return [{
            'vr':soup.find('valuationnumber').text,
            'pa': address
        }]

    return address_search(address)


def get_rates(address):
    valuation_number = get_valuation_number(address)
    url = "http://www.aucklandcouncil.govt.nz/EN/ratesbuildingproperty/ratesvaluations/ratespropertysearch/Pages/yourrates.aspx"

    payload = {
        'vr': valuation_number,
        'pa': address.replace(ILLEGAL_CHARS, "")
    }

    result = requests.get(url, params=payload)
    if result.status_code != 200:
        return False

    br = mechanize.Browser()
    cj = cookielib.LWPCookieJar()

    br.set_cookiejar(cj)

    # br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    # br.set_handle_redirect(True)
    # br.set_handle_referer(True)
    # br.set_handle_robots(False)

    user_agent = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
    br.addheaders = [('User-agent', user_agent)]

    br.open(result.url)
    br.select_form('aspnetForm')
    br.submit()
    print br.response().read()
    return br

address = '44 Queen Street Auckland'
results = get_valuation_number(address)

for result in results:
    print "Address: {}".format(result['pa'])
    print "Valuation Number: {}".format(result['vr'])

url = "http://www.aucklandcouncil.govt.nz/EN/ratesbuildingproperty/ratesvaluations/ratespropertysearch/Pages/yourrates.aspx"
print url

