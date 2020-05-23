#!/bin/bash

if [ "$#" -lt "2" ]
then
    echo "Usage: run.sh DOMAINS_LIST_FILE OUTPUT_LOG_FILE  [--semi-automatic|--full|--test-cmp]"
    exit 1
fi

function kill_descendant_processes() {
    processes=$(pgrep -g $$)
    for p in $processes
    do
        if [ $p != $$ ]
        then
            echo "Killling " $p $(ps o comm --pid $p | tail -1)
            kill -9 $p
        fi
    done
}

if [ "$3" == "--semi-automatic" ]
then
    for i in $(cat "$1") ; do python -u cookinspect.py --semi-automatic-violations-check https://www."$i" 2>&1 | tee -a "$2" ; kill_descendant_processes ; done
elif [ "$3" == "--test-cmp" ]
then
    for i in $(cat "$1") ; do python -u cookinspect.py -t https://www."$i" 2>&1 | tee -a "$2" ; kill_descendant_processes ; done
elif [ "$3" == "--full" ]
then
    for i in $(cat "$1") ; do python -u cookinspect.py --full-violations-check https://www."$i" 2>&1 | tee -a "$2" ; kill_descendant_processes ; done
else
    for i in $(cat "$1") ; do python -u cookinspect.py --automatic-violations-check https://www."$i" 2>&1 | tee -a "$2" ; kill_descendant_processes ; done
fi
