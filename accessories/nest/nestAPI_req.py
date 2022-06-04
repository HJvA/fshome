#https://developers.google.com/nest/device-access/api/thermostat
#https://console.nest.google.com/device-access/project/4bc67721-1e34-4099-9bc2-a12305257b34/information
#https://console.developers.google.com/apis/credentials?pli=1
#https://accounts.google.com/signin/oauth/v2/consentsummary?authuser=0&part=AJi8hANJScTIpMlKjPvOoraqfZxEsXiQG-QF3561t5zQhBgFMYp1xDo5mi4pguMgl8jnsYqhUJvKSuL8Z7oOtcSDJIkuOftPLkRxTZgNM9NLSIJ5GewfxLM-4elYyqF41mwxdxDxHypn2LGL718n6dsW4_6fXgCSJav5mWBYdy3-ropZo0uwQbpKEiF2iZDVSQpgxD8MpnUQCiCar7YdW3abBRfPPsGFTkWefbMkhpIi60aomNo37-03XPnsIC8YigIxwb3F7CfiCJwu0Ex6I5eFjHL6sbjThXAmGKxfP_8YNn5GieYykR0VbCJ4F-upbNW8Vy9Jry4p31j1x3VxuDjbp_GAk5fSp0JdPOU2mehU8SXNRQGszz4Mlv5V0FVOD6mnDNhlr-9xS1UmZ-uhwD1IAynS3t57xrnpXP2XOicCAic9sqNZ7Vc_7EAshkEvBbaKfj0eQRZGMgnAkBMRoidNP545GnsjFD9jPQm5kTJhl_r7-MUwr3Il_XzYNvVCP1joN08AU4GfOfUMHpD3xSMRolZyGKe5Q7jECveyz4Zuj537kNKt1zajSHJFERa5ISxkXbCJGal-Cv41wLo4nFxLcXxLGmA2QdCgCwGRR5WE6kwlaY4QOtU&hl=fr&as=S319694745%3A1644089994475580&client_id=83367521530-9ij3jtk7g53laiti5k1suj27fqqjtg52.apps.googleusercontent.com&rapt=AEjHL4NIf6WNuP-PnfgJqMlWdXFtx6ileWwxBhHG7DRTRqAHgJmHmAZxb3EHsiNX13N3wnvyR-wFMWJ7GzdYJ5viFJ8LUXKjlw
#https://www.google.com/?code=4/0AX4XfWjnf-szIMC2toK19IpRpC45vR2Lf68DqZmDayLSE27YBzRD3EzN6N5uzZgwGAQ2Ew&scope=https://www.googleapis.com/auth/sdm.service#spf=1644090043019

import asyncio, aiohttp #, functools

#import math
import time,os
from datetime import datetime,timedelta,timezone
import logging
import requests

import http.client
from urllib.parse import urlparse

projectId  = "4bc67721-1e34-4099-9bc2-a12305257b34"
#clientId = "83367521530-oorhvbkivncibg6ujg2gdbe0rs8q05i8.apps.googleusercontent.com"
#authId = "83367521530-oorhvbkivncibg6ujg2gdbe0rs8q05i8.apps.googleusercontent.com"
#clSecr = "g06MpcuFaPYdKxDC2eRuC8Iz9oNa"
apiKey="AIzaSyDm21ibF3V-BFcTK_w1lCDyKjBwgkpH358"
deviceId="AVPHwEsua0mnPG7_VrosqoUayVRL9I4E3poM2lWzjAT0V37i-rwRLFmkJGxsp9cR1q9tLWqKIkEFsYbwSLueb3fjm5qd2Q"

clientId="83367521530-9ij3jtk7g53laiti5k1suj27fqqjtg52.apps.googleusercontent.com"
clSecr = "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"
redirect_uri = 'https://www.google.com'
code="4/0AX4XfWiMqTpRcLEW9qhfFPHdIeaM2ISeRIARxg786KWwUJ5nv45pyByniQNbk0Uyq5XVaw"
code="4/0AX4XfWjqnHjysBEL_-ssFCpdQ6vukTBSJuwxWpN2W05lys9Ul7ZrKwuam6_T_-_Mxta00A"
code="4/0AX4XfWjnf-szIMC2toK19IpRpC45vR2Lf68DqZmDayLSE27YBzRD3EzN6N5uzZgwGAQ2Ew"
#&scope=https://www.googleapis.com/auth/sdm.service
code="4/0AX4XfWjeDdEydDmHgbF9F4bKZHZ1HUEk0gXFjSsybUCMxGzT6783mqpVM6B3M8v4gRgCNg"
#&scope=https://www.googleapis.com/auth/sdm.service#spf=1644142557732
#https://www.google.com/?
code="4/0AX4XfWhYmS2F4v0Yr44KOvC5F3qD9tdKYB8fEJecKNQo_is-BtU10RTxGDsap9IXsqjFmg"
#&scope=https://www.googleapis.com/auth/sdm.service#spf=1644143164694
code="4/0AX4XfWgt72anbyGu1aFER4IQNlS3KS1229Q9UWi2NUvE-6x70p2pMnkfDpg-nGXD1oqlIA"
#&scope=https://www.googleapis.com/auth/sdm.service#spf=1644155684985
code="4/0AX4XfWjuzZp23rYGyHQPha7ZsZFfVlWTagn1sJBDwbBVfMADJ0HuyIBV3Dxot53iWQpkVA"  #henkjanvanaalderen
#&scope=https://www.googleapis.com/auth/sdm.service#spf=1644157548348
code="4/0AX4XfWg5TY11sZzbVEfXHpuzvd_C8GvYGczReQVfnGjS1wb1IrjeDJVJnQuAPExGsSJ72Q"
#&scope=https://www.googleapis.com/auth/sdm.service#spf=1644158918583

refreshtoken="1//09U2FOnyERg0TCgYIARAAGAkSNwF-L9Irv1D5rZTqe4CgtEjPx8B1G93Ss0qpcdJIBnvdGxWlCXbhG_xG7OEf_uWcCOknz6qRwiY"
				#"1//09s2AHrHA9JzkCgYIARAAGAkSNwF-L9IrnBg4LBexRjn4F5Q8OR-m3coZdCjuiJPnNFfPAmko4UOt63_ySzBgFvYtF-WaGMCnr6o"
				#"1//094I7VYBgBR-lCgYIARAAGAkSNwF-L9IrM2xHbBvBerVoxdaCTXtcqY6HpGbYusEjHEpfbVcQFSjngjWcQhEXUdgHJHbvP_lA91Q"
				#"1//099-qNH9t1_ImCgYIARAAGAkSNwF-L9IrSPv9IJQ5AVRb6ZaJybckick0dPloDi2_67h297eaUIa6_AUii6D1PpCU6xpdFPdGB44"

params = (
    ('client_id', clientId),
    ('client_secret', clSecr),
    ('code', code),
    ('grant_type', 'authorization_code'),
    ('redirect_uri', redirect_uri),
)
def getToken():
	""" get access_token using authorization-code
	"""
	#
	#https://www.google.com?code=authorization-code&scope=https://www.googleapis.com/auth/sdm.service
	response = requests.post('https://www.googleapis.com/oauth2/v4/token', params=params)
	logger.info('tokResp:{}'.format(response.json()))
	resp = response.json()
	#logger.info('getToken resp:{}'.format(response.))
	#access_token = response_json['token_type'] + ' ' + str(response_json['access_token'])
	if 'access_token' in resp:
		logger.info("Access token:'{}' type:'{}'".format(resp['access_token'], resp['token_type']))
		refresh_token = resp['refresh_token']
		logger.info("Refresh token:'{}'".format( refresh_token))
		return resp


url= "https://smartdevicemanagement.googleapis.com/v1"
#https://nestservices.google.com/partnerconnections/project-id/auth?redirect_uri=https://www.google.com&access_type=offline&prompt=consent&client_id=oauth2-client-id&response_type=code&scope=https://www.googleapis.com/auth/sdm.service
url = 'https://nestservices.google.com/partnerconnections/'+projectId+'/auth?redirect_uri='+redirect_uri+'&access_type=offline&prompt=consent&client_id='+clientId+'&response_type=code&scope=https://www.googleapis.com/auth/sdm.service'
#entered in webbr: and picked gmail account and switched on access
#https://nestservices.google.com/partnerconnections/4bc67721-1e34-4099-9bc2-a12305257b34/auth?redirect_uri=https://www.google.com&access_type=offline&prompt=consent&client_id=83367521530-9ij3jtk7g53laiti5k1suj27fqqjtg52.apps.googleusercontent.com&response_type=code&scope=https://www.googleapis.com/auth/sdm.service
#resp="https://www.google.com/?code=4/0AX4XfWjqnHjysBEL_-ssFCpdQ6vukTBSJuwxWpN2W05lys9Ul7ZrKwuam6_T_-_Mxta00A&scope=https://www.googleapis.com/auth/sdm.service#spf=1644080314866"
url='https://www.googleapis.com/oauth2/v4/token?client_id='+clientId+'&client_secret='+clSecr+'&code='+code+'&grant_type=authorization_code&redirect_uri=https://www.google.com'


def refresh(refreshtoken):
	url="https://www.googleapis.com/oauth2/v4/token?client_id={}&client_secret={}&refresh_token={}&grant_type=refresh_token"
	#url.format(clientId, clSecr, refreshtoken)
	resp = requests.post(url.format(clientId, clSecr, refreshtoken))
	logger.info('{}\nrefresh:{}'.format(url.format(clientId, clSecr, refreshtoken),resp))
	if resp:  # and resp.status_code == 443:
		return resp.json()

def connect(accesstoken, endpoint='structures'):
	url="https://smartdevicemanagement.googleapis.com/v1/enterprises/{}/{}".format(projectId, endpoint)
	headers = {'Content-Type': 'application/json', 'Authorization': "Bearer {}".format(accesstoken) }
	#https://smartdevicemanagement.googleapis.com/v1/enterprises/project-id/structures' -H 'Content-Type: application/json' -H 'Authorization: Bearer access-token'
	resp = requests.get(url, headers=headers)
	#logger.info('resp:{}'.format(resp))
	if resp:
		logger.info('{}:{}'.format(endpoint, resp.json())) #.decode("utf-8")))
	return resp
	
	conn = http.client.HTTPSConnection("developer-api.nest.com")
	headers = {'authorization': "Bearer {0}".format(token)}
	conn.request("GET", "/", headers=headers)
	response = conn.getresponse()
	logger.info('resp:{}'.format(response.json()))

	if response.status == 307:
	    redirectLocation = urlparse(response.getheader("location"))
	    conn = http.client.HTTPSConnection(redirectLocation.netloc)
	    conn.request("GET", "/", headers=headers)
	    response = conn.getresponse()
	    if response.status != 200:
	        raise Exception("Redirect with non 200 response")
	
	data = response.read()
	logger.info('data:{}'.format(data))  #.decode("utf-8")))

if __name__ == '__main__':	# just testing the API and gets userId if neccesary
	#from lib import tls
	#import secret
	logger = logging.getLogger()
	[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers persist between calls
	logger.addHandler(logging.StreamHandler())	# use console
	logger.addHandler(logging.FileHandler(filename= os.path.expanduser('nestApi.log'), mode='w', encoding='utf-8')) #details to log file
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S%z")))
	js = refresh(refreshtoken)
	if not js:
		js = getToken()
	logger.info('jsonTokens:{}'.format(js))
	if js:
		token = js['access_token']
		#token = js['refresh_token'] 
		dat = connect(token)
		dat = connect(token, 'devices/'+deviceId).json()
		name = dat['devices'][0]['name']
		devId = name.split('/')[-1]
		traits = dat['devices'][0]['traits']
		hum = traits['sdm.devices.traits.Humidity']['ambientHumidityPercent']
		tempC = traits['sdm.devices.traits.Temperature']['ambientTemperatureCelsius']
		Tsetp = traits['sdm.devices.traits.ThermostatTemperatureSetpoint']['heatCelsius']
		
		logger.info('device:{}\n T:{} H:{} Ts:{}'.format(devId,tempC,hum,Tsetp))
		
	