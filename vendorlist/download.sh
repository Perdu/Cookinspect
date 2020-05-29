#!/bin/bash

function download_vl() {
    wget -O vendorlist_"$1".json https://vendorlist.consensu.org/v-"$1"/vendorlist.json #|| rm vendorlist_"$1".json
    return $?
}

function download_vl_v2() {
    wget -O v2/vendorlistv2_"$1".json https://vendorlist.consensu.org/v2/archives/vendor-list-v"$1".json #|| rm vendorlistv2_"$1".json
    return $?
}

if [ ! -d "v2" ]
then
    mkdir v2
fi
if [ "$#" == "0" ]
then
    # download all latest vendorlists
    lastest_vendorlist_number=$(ls -1 | grep vendorlist | sed 's/vendorlist_\(.*\)\.json/\1/' | sort -g | tail -n 1)
    res=0
    while [ $res == 0 ]
    do
        lastest_vendorlist_number=$(( $lastest_vendorlist_number + 1 ))
        download_vl "$lastest_vendorlist_number"
        res=$?
    done
    rm vendorlist_"$lastest_vendorlist_number".json

    # download all latest v2 vendorlists
    lastest_vendorlist_number=$(ls -1 v2/ | grep vendorlist | sed 's/vendorlistv2_\(.*\)\.json/\1/' | sort -g | tail -n 1)
    res=0
    while [ $res == 0 ]
    do
        lastest_vendorlist_number=$(( $lastest_vendorlist_number + 1 ))
        download_vl_v2 "$lastest_vendorlist_number"
        res=$?
    done
    rm v2/vendorlistv2_"$lastest_vendorlist_number".json
else
    # download vendorlist given in argument
    download_vl "$1"
fi
