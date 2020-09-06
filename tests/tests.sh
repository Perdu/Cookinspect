#!/bin/bash

function run() {
    address=$1
    keyword=$2
    echo "Testing grepping $keyword on page $address"
    python cookinspect.py -a --ignore-robots-txt "$address" 2>/dev/null | grep -F "$keyword" >/dev/null
    if [ $? -ne 0 ]
    then
        echo "*** Test failed: grep $keyword on page $address"
    fi
}

function other_commands() {
    command=$1
    keyword=$2
    echo "Testing grepping $keyword on command $command"
    python cookinspect.py $command | grep -F "$keyword" > /dev/null
    if [ $? -ne 0 ]
    then
        echo "*** Test failed: grep $keyword with command $command"
    fi
}

other_commands "-h" "usage: cookinspect.py"
other_commands "https://doctissimo.fr" "Access allowed"
other_commands "https://lepoint.fr" "Access refused"
run "https://lepoint.fr" "Consent string:"
run "https://www.tpi.it" "Violations"
run "https://www.mariefrance.fr" "VIOLATION: Consent set in consent string before any user action (GET)"
run "https://www.immobilienscout24.de" "Consent set in consent string before any user action (direct)"
run "https://www.immobilienscout24.de" "VIOLATION: Consent set in consent string before any user action (postmessage)"
run "https://www.chefkoch.de" "VIOLATION: Consent set in consent string before any user action (post)"
