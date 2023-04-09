# Viu Kodi Addon (Unofficial)

[![Kodi version](https://img.shields.io/badge/kodi%20versions-19-blue)](https://kodi.tv/)
[![GitHub release](https://img.shields.io/github/release/maynero/plugin.video.viu.svg)](https://github.com/maynero/plugin.video.viu/releases)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-yellow.svg)](https://opensource.org/licenses/GPL-3.0)
[![Build Status](https://img.shields.io/github/actions/workflow/status/maynero/plugin.video.viu/release.yml)](https://github.com/maynero/plugin.video.viu/actions?query=branch%3Amaster)

## Disclaimer
This plugin is not affiliated nor supported by Viu.

## Limitations: 
 - Login only support emails
 - Limited artwork

## Note: 
 - The addon was only tested with Kodi 19.0.
 - Only tested on PH site of Viu, but might work with others.
 - I'm not a python developer, expect some quirks.

## Credits
 - plugin.video.youngkbell.viu by mani-coder for the base code on this addon: https://github.com/mani-coder/plugin.video.youngkbell.viu
 - add-ons for the player.py code: https://github.com/add-ons

## Releases
### v0.0.8 (2023-04-10)
- Add user agent when connecting to Viu APIs

### v0.0.7 (2023-04-02)
- Fix missing stream URL due to API changes

### v0.0.6 (2023-03-20)
- Viu site changes

### v0.0.5 (2022-08-25)
- Fix unsorted video items when some episodes are only available on premium

### v0.0.4 (2022-05-27)
- Fix issue where "coming soon" video are being sent to UpNext
- Fix issue where "coming soon" video can be played but it actually played previous episode

### v0.0.3 (2022-05-13)
- Add undefined preferred_subtitle variable

### v0.0.2 (2022-05-13)
- Add support for account login
- Add support for Up Next
- Fix logging labels

### v0.0.1-alpha (2022-05-09)
- Initial release
