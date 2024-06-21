#!/usr/bin/env bash

DB=smtlib.sqlite

rm -f $DB

echo "Prepopulate"

./prepopulate.py $DB

echo "Add benchmarks"

find ~/Work/SMT-LIB-db/SMT-LIB-ss/ -name '*smt2' | parallel -j 4 ./addbenchmark.py $DB

echo "Postpopulate"

# ./postprocess.py $DB ~/SMT-COMP/smt-comp-master
