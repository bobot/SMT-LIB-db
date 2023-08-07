#!/usr/bin/env bash

DB=smtlib.sqlite

rm -f $DB

echo "Prepopulate"

./prepopulate.py $DB

echo "Add benchmarks"

parallel -j 4 ./addbenchmark.py $DB -- `find ~/SMT-LIB/SMT-LIB-ss/ -name '*smt2'`

echo "Postpopulate"

./postprocess.py $DB ~/SMT-COMP/smt-comp-master
