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
-->

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


