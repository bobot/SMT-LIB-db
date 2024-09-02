#!/usr/bin/env bash

DB=smtlib.sqlite
DOLMEN_BIN=~/Programs/dolmen/_build/install/default/bin/dolmen

rm -f $DB

echo "Prepopulate"

./prepopulate.py $DB

echo "Add benchmarks"

find ~/Work/SMT-LIB-db/SMT-LIB-ss/ -name '*smt2' | parallel -j 4 ./addbenchmark.py $DB $DOLMEN_BIN

echo "Postpopulate"

# ./postprocess.py $DB ~/SMT-COMP/smt-comp-master
