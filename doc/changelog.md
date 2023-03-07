# Changelog fshome project

If you notice that something is missing, please open an issue or submit a PR.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/).

<!--
Sections
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Breaking Changes
### Developers
### Confinement
-->
## [1.5.1] - 2023-03-07
### Added
- Hue API V2 (having event driven updates instead of polling)
- inkplate 6 plus nicer fonts, higher resolution
- weathericons (preliminary)
- use of typing module to have strickter parameter types
- use of mypy tool to check source code
- tls.clavier class for universal keyboard keys detection

## [1.5.0] - 2022-06-04
### Added
- inkplate 6 plus display on micropython with i2c comm interface
- scd30 Sensirion CO2 sensor
- bme680 temperature, humidity, pressure sensor
- tmp117 precise temperature sensor  

## [1.4.7] - 2021-12-29
### Changed
- DVrng for power type to block bad power readings from DSMR

## [1.4.6] - 2021-08-26
### Added
- inkplate display updated sync time & timezone
- openweather reading o3 pm2_5 pm10 aqi ... for location..
### Changed 
- grtls.py having micropython tools derived from tls.py

## [1.4.5] - 2021-05-16
### Added
- inkplate display now using micropython in native mode using restfull fshome api
- inkplate displays actual graph of data retrieved over network from fshome server
- micropython on inkplate measuring temperature using onewire sensor
- restfull api extended to PUT quantity value in fshome database
- grtls.py modified/added to support micropython time related functions 
- secret.py (to be created yourself) containing password definitions etc  

## [1.4.4] - 2021-04-11
### Added
- inkplate peripheral test (e-paper display handled on seperate raspberry)
- fssite restfull api requesting ancient data over the network
- openweather data from internet
### Changed
- moved to Raspberry 3+; tested installation (better bluetooth reception)

## [1.4.3] - 2020-08-23
### Added 
- sounder : plays wav files as signaller reacting to events
## [1.4.2] - 2020-06-28
### Added
- deCONZ webSocket allows real time event handling
### Changed
- logging to /tmp folder, which might be located on RAM to reduce sdcard wear  
  (also updated /etc/fstab to include /tmp on tmpfs)
- fssite now only shows sources in its picklist that have recent results stored  
### Fixed
- gasVolume read correctly from DSMR meter as it the smart meter was installed

## [1.4.1] - 2020-06-16
### Added
- dresden electronik deCONZ Raspbee II together with HUE bridge for Tradfri on/off switch

## [1.4.0] - 2020-06-14
### Changed
- DSMR & WNDR reduced data rate using sinceStamp  
### Fixed
- asyncio loop errors in hueAPI and WNDR (using no semaphore)

## [1.3.9] - 2020-06-02
### Confinement
- fs20 SIG2 signaller accepts motion events e.g. from hue motion sensor  
### Added
- devicetype DEVT['signal']
- tested async http together : hue and wndr

## [1.3.8] - 2020-05-20
### Changed
- hueAPI now uses aiohttp instead of requests for having full async operation  

## [1.3.7] - 2020-04-22
### Added
- netgear wndr router for logging LAN traffic
- tailScale for making bottle fssite server accessible to world

## [1.3.6] - 2020-02-02
### Added
- signaller event handler enhanced for aios setDigPulse as actuator
- aios setDigPulse method generates a single pulse on digital output pin
### Changed
- dbLogger self.execute runs most sql
- layout fssite optimised for various ipad / iphone browsers
- bluepyBase.py does not depend on project lib files (for logging)

## [1.3.5] - 2020-01-06
### Added
- storing event descriptors, beeing supported by user interface web page

## [1.3.4] - 2019-12-29
### Added
- illuminance sensor on aios analog channel A1 over BLE  
- setting analog reference voltage using mask config attribute over GATT valid_range descriptor   

## [1.3.3] - 2019-12-11
### Added
- signaller class handles events by exitating actuators

## [1.3.2] - 2019-12-07
### Changed 
- PIR motion sensor on AIOS tested 
- bottle site enhanced with cookies that remember state
- individual AIOS bits can be specified using mask item in config

## [1.3.1] - 2019-11-30
### Added
- PIR motion sensor with GATT notification 

## [1.3.0] - 2019-11-22
### Added
- accessories/BLEAIOS : Bluetooth low energy GATT Automation-IO client
### Changed
- layout bottle html screen : tested with multiple browsers on iphone and ipad

## [1.2.5] - 2019-07-06
### Fixed
- cursor to point back in time
- select multiple working on desktop sites

## [1.2.4] - 2019-06-10
### Fixed
- night - morning - afternoon - evening :labels for 1day x axis
### Changed

## [1.2.3] - 2019-06-10
### Added
- icon for ios home screen
### Changed
- time shift reset ?
- get_logger function for all loggers

## [1.2.2] - 2019-06-06
### Added
- x cursor in chart lets user go back in time
- status line at bottom of page

## [1.2.1] - 2019-05-26
### Added
- Homekit support for Hue lights

## [1.2.0] - 2019-05-10
### Added
- p1smart DSMR dutch utility meters for sampling electric power,energy,voltage

### Breaking Changes
- json setting file stucture unified over sampler families
- HAP fuctions separated from sampler functions; project will run without Homekit

### Changed
- charts will show averaged results over selectable periodes
- each chart quantities will have own colour (stroke) defined in devConst file

## [1.1.0] - 2019-03-10
### Added
- Signify / Philips - Hue API Sensor logging to database
- chart legends

## [1.0.1] - 2019-02-18
### Added
- ('after noon','evening','night','morning') used as x axis labels in 1 day charts

## [1.0.0] - 2019-02-17
### Changed
- serDevice split off from serComm
- oop design for HAP devices
### Fixed
- using utc offset to calculate correctly day boundaries
### Added
- svg chart time ax scaling with user selectable magnitude (day,week,month,year/2,year)

## [0.5.0] - 2019-02-14
### Added
tested with fs20 switch and dimmer and motion detector and doorbell
### Changed
restyled bottle page

## [0.4.0] - 2019-02-14
### Added
histogram for counted quantities. uses svg path for histogram and svg polyline for curves

## [0.3.0] - 2019-02-10
### Added
module restructuring:lib folder and accessories/fs20 folder.
### Fixed
using packages properly instead of sys.path manipulations

## [0.2.0] - 2019-02-03
### Added
setup fshome git structure with imported submodules: bottle and HAP-python

## [0.1.0] - 2019-02-02
### Added
initial commit. derived from HAP-python fork, with fs20 drivers.
having serial communication, statefull serial devices, fs20 devices, HAP-python devices. bottle page with svg chart and css menubar with multiselect dropdowns


