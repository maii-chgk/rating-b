import urllib2
import json

def url2json(url):
	response = urllib2.urlopen(url)
	return json.load(response)