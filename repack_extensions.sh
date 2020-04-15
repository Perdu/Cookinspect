#!/bin/bash

# You need to first manually extract these extensions for this script to work,
#  because chromium's command line only works if they already exist.
# In chromium → More tools → Extensions, activate developer mode, then click
#  "pack extension". For each extension, pack the corresponding folder and move
#  both the crx and the pem file to the extension/ folder.

chromium --pack-extension=extensions/override_cmp --pack-extension-key=extensions/override_cmp.pem
chromium --pack-extension=extensions/cookie_glasses --pack-extension-key=extensions/cookie_glasses.pem
chromium --pack-extension=extensions/override_cmp_monitor_postmessages --pack-extension-key=extensions/override_cmp_monitor_postmessages.pem
chromium --pack-extension=extensions/monitor_postmessages --pack-extension-key=extensions/monitor_postmessages.pem
chromium --pack-extension=extensions/watch_requests --pack-extension-key=extensions/watch_requests.pem
chromium --pack-extension=extensions/get_euconsent --pack-extension-key=extensions/get_euconsent.pem
chromium --pack-extension=extensions/probe_cmp_postmessage --pack-extension-key=extensions/probe_cmp_postmessage.pem
