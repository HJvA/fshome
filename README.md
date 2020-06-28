
# fshome

Application to read domotica sensors and operate actuators and store results to a database.  Results can be displayed graphically in a webbrowser and can be linked to the Apple homekit system. 

The application operates as a homekit bridge e.g. on a Raspberry pi which is connected to your home network. 

The project uses the HAP-python project by Ivan Kalchev.
It is cloned as a submodule from <https://github.com/ikalchev/HAP-python>

The project may connect to a bluetooth low energy device (see my BLE-automation project) which collects digital and/or analog signals whichever connected.

The results will be stored in a sqlite database. The quantities recorded will have to be assigned to a source / room in a fs20.json / hue.json / p1DSMR.json / aios.json / WNDR.json / deCONZ.json file.

The measured temeratures and humidities and other recorded events can be displayed in a svg chart in a browser, with selectable quantities and sources. For this a web server is available using the bottle web-framework cloned from <https://github.com/bottlepy/bottle> by Marcel Hellkamp.

## Table of Contents
1. [Features](#Features)
2. [Installation](#Installation)
3. [Configuration of devices](#Configure)
4. [Configuration of Homekit](#Homekit)
5. [Running the application](#Usage)
6. [Use of Homekit rules](#Rules)
7. [Notice](#Notice)

## Features <a name="Features"></a>

The following sensors/actuators are supported:  
- fs20 S300 temperature / humidity sensor  
- fs20 mains switch  
- fs20 doorbell button  
- fs20 dimmer  
- Hue motion / brightness / temperature sensor  
- Hue switches  
- Hue lights 
- DSMR dutch electricity and gas utility meter  
- AIOS GATT Bluetooth Low Energy Automation-IO client
- WNDR4300 router reporting LAN traffic  
- IKEA Tradfri switch|light via deCONZ zigbee gateway

### fs20

Fs20 represents a family of devices with many actuators and sensors which communicate via the 868 MHz radio frequency. The signals can be send and received by a CUL tranceiver.  

### Hue

Signify-Philips-Hue devices represent the Hue ecosystem which control your lights.  

### deCONZ

Alternative or supplemental bridge for Hue lights or other Zigbee devices.  
The raspberry server has been provided with a <https://phoscon.de/en/raspbee2> Zigbee gateway.  
The deCONZ api is similar to the HUE api, however deCONZ allows real time event handling through webSockets. So pressing a button will immediately be handled by the signaller class of fshome.

### DSMR

DSMR is a domestic smart metering system for home electricity and natural gas.

### AIOS

AIOS (Automation IO service) is an Adafruit bluetooth device gathering a variety of quantities: e.g temperature,humidity,TVOC,eCO2 (on I2C bus) and other quantities connected to the ADC and digIO channels. 
e.g. a PIR motion detector connected to digin pin 16, and a photocell connected to analog channel A1, and a HV power LED for giving a light flash connected to digital out P0.04.  

### WNDR

WNDR (netgear WNDR4300 router) reporting LAN traffic. Either "rxToday" or "rxYestday" items can be requested as devadr in WNDR.json

## Installation <a name="Installation"></a>

Starting on a standard Raspberry pi on Raspbian (a debian clone, but almost any linux computer probably will be ok) fist make sure you have Python 3.5 or later installed. Also install git and pip3 (e.g. using  
```bash  
apt-get install <package>
```  ). Then download the fshome project  
 
```bash
git clone git://github.com/HJvA/fshome
cd fshome
git submodule init
git submodule update --depth=1
```  
When using the fs20 devices, connect the CUL transceiver to a USB port of your Raspberry. Have the CUL transceiver flashed with the latest firmware from <http://culfw.de>. Assure that ```/dev/ttyACM0``` appears on your system (it represents a serial port used for the CUL). Maybe you should enable it using raspi-config.

### Tailscale

Tailscale is a service that makes it easy to access your fshome site securely from the internet when you are not at home e.g. from your phone.

- go to  <https://tailscale.com>
- create an account
- install the tailscale client on your devices (both on the server, as on the clients)
- tailscale will provide you with an ip adres for each device in your network of servers and clients
- add the item "tailScale" : "ip.of.bottle.serv" to the fs20.json file
  where the ip... is provided by tailscale as the ip address of the raspberry where fssite.py is running (i.e. the server)
- on your browsing device (i.e. a client), open an internet browser to address <http://ip.of.bottle.serv:8080>

### rclone

rclone is a command line utility to copy or sync files to a (remote) storage provider like google drive   
- install rclone on the fshome server, getting it from <https://github.com/rclone/rclone/releases>  
- create an app on your google account to setup permission to save to your gdrive  
- run the backup.sh script for making a backup  

## Configuring devices <a name="Configure"></a>

The fs20.json file should contain the json representation of the fs20 devices that are present in your haus. Delete the fs20.json file to have a fresh install. First run fs20Sampler.py for a while to automatically fill the file with the devices the are currently emitting (do Press your fs20 handsenders and buttons to emit something). You can edit the fs20.json file afterwards, and change the dict key to fill in a (unique) display_name. You can also change the 'typ' field to represent the correct type of the device (typ has to correspond to one of the DEVT members listed below)  

The hue.json file should contain the json representation of hue devices that are connected to your hue bridge. Clear the hue.json file, except for the ip adress of the bridge on your LAN. Run hueAPI.py once to register fshome on the bridge, and to get an idea which devices are known. Enter the obtained userid in the hue.json file. Run fsmain.py for a while, and exit pressing ctrl-C See the error.log file for a proposed list of devices to be copied in hue.json

Similar setups can be carried out with hueSampler.py and p1DSMR.py and aiosSampler.py

## Configuring homekit <a name="Homekit"></a>

To have a fresh install:
First cleanup your devices configured in your IOS home app. Also delete the accessory.state file on your Raspberry. Now run the fsmain.py for a while, and make a screenshot when you see the homekit id number appear on it (or look for 'pincode' in the log files). Use this number to register the accessory bridge in your IOS Home app. 

Add a unique "aid":n entry in the json files to each quantity to be available for Homekit HAP.

## Using the application <a name="Usage"></a>

The application consist of 2 python3 programs: fsmain.py for aquistion and storage of the measured quantity values and fssite.py serving graphical results to a browser.

Execute the following commands in a terminal:

```bash  
cd ~/fshome  
nohup python3 fsmain.py 2>stderr.log &  
python3 fssite.py  
```

See the log files for error conditions to be resolved.

After a while when enough data has been acquired open a browser window on  
```
<http://<ip.of.rasp.berry>:8080>
```  
Select the room source and select some quantities from the multi select boxes. Also select the timeframe for the chart x-axis. A cursor can be dragged to point to a particular time. The comment field can be editted having a text describing the event pointed. It will be saved pressing the ok button. Otherwise when no text was entered, the time frame will shift to the cursor position when the ok button is pressed.  


## Using rules <a name="Rules"></a>

Several systems allow to define actions following to certain events:  
- Homekit Rules can be used to trigger actions when a certain value passes a boundary. So the lights can be switched on when someone is home and it is getting dark.    
- fshome allows to configure an action when a value changes and is recorded. Enter the following item to a quantiity definition in a conf file:  
```
"signal" : "109=26"  
```  
   where 109 is a quantityid and 26 is a command or data to be set to the quantity.  
- The Hue bridge also can have rules setup. see e.g. the excellent 'Hue Lights' app for this.


## Notice <a name="Notice"></a>

Most of the credits to get this working must go to Ivan. Many thanks for that.  
The knowledge about the fs20 devices with the CUL interface is comming from Rudolf Koenig from his fhem project: <https://fhem.de>
Fs20 devices are/were distributed by <https://www.elv.de/fs20-funkschaltsystem.html>. (can also be ordered from amazon.de)  
Information on the hue devices can be found here <https://www2.meethue.com/en-us>  
Information on the DSMR meter can be found here <https://www.netbeheernederland.nl/dossiers/slimme-meter-15/documenten>  
The bluetooth low energy library <https://github.com/IanHarvey/bluepy>
The BLE AIOS server project : <https://github.com/HJvA/BLE-automation>  
The deCONZ API for the Zigbee gateway: <https://dresden-elektronik.github.io/deconz-rest-doc>

