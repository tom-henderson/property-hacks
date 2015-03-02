# -*- coding: utf-8 -*-
import json
import urllib
from time import sleep
from pprint import pprint
from collections import defaultdict

import requests
import mechanize
import cookielib
from bs4 import BeautifulSoup as bs
from selenium import webdriver

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
    url = "http://maps.aucklandcouncil.govt.nz/"
    url += "ArcGIS/rest/services/Applications/ACWebsite/MapServer/2/query"
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

    url = "http://maps.aucklandcouncil.govt.nz/"
    url += "ArcGIS/rest/services/Applications/ACWebsite/MapServer/3/query"
    json_data = requests.get(url, params=payload).text
    data = json.loads(json_data)

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


def valuation_search(address):
    """ Fetch valuation data using selenium. Returns a dict containing:
            assessment_number
            annual_rates
            land_value
            capital_value
            latest_capital_value
            latest_land_value
            latest_improvement_value
            valuation_date
            land_area
            certificate_of_title_number
            legal_description
    """
    browser = webdriver.Chrome('./chromedriver')

    address_data = get_valuation_number(address)[0]
    url = "http://www.aucklandcouncil.govt.nz/"
    url += "EN/ratesbuildingproperty/ratesvaluations/ratespropertysearch/"
    url += "Pages/yourrates.aspx?vr={}&pa={}".format(
        address_data['vr'],
        address_data['pa'].replace(ILLEGAL_CHARS, "")
    )

    browser.get(url)
    data = None
    while not data:
        sleep(1)  # Wait for ajax to load
        try:
            data = browser.execute_script("return document.getElementById('summaryinforwrapper').innerHTML")
        except:
            pass

    browser.quit()

    soup = bs(data)

    result = defaultdict(lambda: '')

    rows = soup.findAll('div', {"class": "summaryitem"})
    for row in rows:
        if len(row.findAll('div')) == 2:
            title = row.find('div', {"class": "summaryitemtitle"}).text.strip()
            value = row.find('div', {"class": "summaryitemvalue"}).text.strip()

            if title == 'Assessment number:':
                result['assessment_number'] = value

            elif title == 'Total annual rates (2014/2015)':
                value = value.split('\n')[0].strip().replace(u'\xa0', '')
                result['annual_rates'] = value

            elif title == 'Land value:':
                result['land_value'] = value

            elif title == 'Capital value:':
                result['capital_value'] = value

            elif title == 'Latest capital value':
                result['latest_capital_value'] = value

            elif title == 'Latest land value:':
                result['latest_land_value'] = value

            elif title == 'Latest improvement value:':
                result['latest_improvement_value'] = value

            elif title == 'Certificate of title number:':
                result['certificate_of_title_number'] = value

            elif title == 'Legal description:':
                result['legal_description'] = value

            elif title == 'Land area:':
                result['land_area'] = value

            elif title == 'Valuation as at date:':
                day = value.split('\n')[0].strip()
                month = value.split('\n')[1].strip()
                year = value.split('\n')[2].strip()
                result['valuation_date'] = "{} {} {}".format(
                    day,
                    month,
                    year
                )

    return result

address = '44 Queen Street Auckland'
results = get_valuation_number(address)

for result in results:
    print "Address: {}".format(result['pa'])
    print "Valuation Number: {}".format(result['vr'])
    valuation_data = valuation_search(address)
    print "Land Value: {}".format(valuation_data['latest_land_value'])
    print "Improvements: {}".format(valuation_data['latest_improvement_value'])
    print "Capital Value: {}".format(valuation_data['latest_capital_value'])
    print
