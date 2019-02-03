
# HAP-python-fs20

Application to embed fs20 type devices to the Apple homekit eco system.
Fs20 represents a family of devices with many functions which communicate via the 868 MHz radio frequency.  
The application operates as a homekit bridge e.g. on a Raspberry pi which is connected to your home network. 
Uses a CUL transceiver to receive and send fs20 messages on the 868 MHz RF network  

This project is an extension of the HAP-python project by Ivan Kalchev <ikalchev>.
It is forked from https://github.com/ikalchev/HAP-python

## Table of Contents
1. [Installation](#Installation)
2. [Configuration of devices](#Configure)
3. [Configuration of Homekit](#Homekit)
4. [Use of Homekit rules](#Rules)
5. [Notice](#Notice)

## Installation <a name="Installation"></a>

Starting on a standard Raspberry pi on Raspbian (a debian clone)
fist make sure you have Python 3.5 or later installed
also install git and pip3 (e.g. using apt-get ,install <package>)
then download the HAP-python project 
git clone git://github.com/HJvA/HAP-python

Connect the CUL transceiver to a USB port of your Raspberry. Have the CUL transceiver flashed with the latest firmware from http://culfw.de. Assure that /dev/ttyACM0 appears on your system (it represents a serial port used for the CUL). Maybe you should enable it using raspi-config.

## Configuring devices <a name="Configure"></a>

The fs20.json file should contain the json representation of the fs20 devices that are present in your haus. Delete the fs20.json file to have a fresh install. First run fs20_cul.py for a while to automatically fill the file with the devices the are currently emitting (do Press your fs20 handsenders and buttons to emit something). You can edit the fs20.json file afterwards, and change the dict key to fill in a (unique) display_name. You can also change the 'typ' field to represent the correct type of the device (typ has to correspond to one of the DEVT members listed below)   

## Configuring homekit <a name="Homekit"></a>

To have a fresh install:
First cleanup your devices configured in your IOS home app. Also delete the accessory.state file on your Raspberry. Now run the fsmain.py for a while, and make a screenshot when you see the homekit id number appear on it. Use this number to register the accessory bridge in your IOS Home app. 

## Using homekit rules <a name="Rules"></a>

Homekit Rules can be used to trigger actions when a certain value passes a boundary. So the lights can be switched on when someone is home and it is getting dark.

## Notice <a name="Notice"></a>

Most of the credits to get this working must go to Ivan. Many thanks for that.  
The knowledge about the fs20 devices with the CUL interface is comming from Rudolf Koenig from his fhem project: https://fhem.de
Fs20 devices are/were distributed by https://www.elv.de/fs20-funkschaltsystem.html. (can also be ordered from amazon.de)
