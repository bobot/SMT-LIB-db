#!/usr/bin/env python3

import sqlite3
import os
import argparse
import polars as pl
import altair as alt
from jinja2 import Environment, PackageLoader, select_autoescape

"""
    Writes index.html and the overview of families and logics.
"""

env = Environment(loader=PackageLoader("logics"), autoescape=select_autoescape())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA cache_size = 10000;")

    logic_template = env.get_template("logic.html")

    res = connection.execute(
        """
            SELECT logic FROM Logics
        """
    )
    logics = res.fetchall()
    logics.append("ALL")

    try:
        os.mkdir("out/logics")
    except:
        pass

    for logic in logics:
        logic_print_name= logic[0]
        logic_name = logic_print_name
        if logic_print_name == "ALL":
            logic_name = "%"

        print(f"Generating {logic_print_name}")

        years = list(range(2005, 2025))
        fresh = []
        used = []
        solved = []
        crafted = []
        industrial = []
        random = []
        for year in years:
            yearstr = f"{year}-12-31"
            oldyearstr = f"{year-1}-12-31"
            # Counts benchark where there was a sat/unsat at some point before
            for row in connection.execute(
                """
                SELECT count(DISTINCT bnch.id) FROM Benchmarks AS bnch
                JOIN Queries AS qr  ON qr.benchmark = bnch.id
                JOIN Results AS res ON res.query = qr.id
                JOIN Evaluations as eval ON eval.id = res.evaluation
                WHERE NOT bnch.isIncremental
                AND eval.date <= ?
                AND (res.status == 'sat' OR res.status == 'unsat')
                AND bnch.logic LIKE ?;
                """,
                (oldyearstr, logic_name),
            ):
                this_solved = row[0]
                solved.append(this_solved)
            # Counts benchark that have a first occurence before the current year
            for row in connection.execute(
                """
                SELECT count(DISTINCT bnch.id) FROM Benchmarks AS bnch
                JOIN Queries AS  qr ON qr.benchmark = bnch.id
                JOIN Results AS res ON res.query = qr.id
                JOIN Evaluations AS eval ON eval.id = res.evaluation
                WHERE NOT bnch.isIncremental
                AND eval.date <= ?
                AND bnch.logic LIKE ?;
                """,
                (oldyearstr, logic_name),
            ):
                this_used = row[0]
                used.append(this_used - this_solved)
            # Counts fresh number of benchmarks
            for row in connection.execute(
                """
                SELECT COUNT(bnch.id) FROM Benchmarks AS bnch
                JOIN Families AS fam ON fam.id = bnch.family
                WHERE NOT bnch.isIncremental
                AND bnch.logic LIKE ?
                AND fam.firstOccurrence <= ?;
                """,
                (logic_name, yearstr),
            ):
                this_fresh = row[0]
                fresh.append(this_fresh - this_used)

            for categoryRow in connection.execute(
                """
                SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
                JOIN Families AS fam ON fam.id = b.family
                WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
                """,
                (logic_name, "crafted", yearstr),
            ):
                crafted.append(categoryRow[0])
            for categoryRow in connection.execute(
                """
                SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
                JOIN Families AS fam ON fam.id = b.family
                WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
                """,
                (logic_name, "random", yearstr),
            ):
                random.append(categoryRow[0])
            for categoryRow in connection.execute(
                """
                SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
                JOIN Families AS fam ON fam.id = b.family
                WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
                """,
                (logic_name, "industrial", yearstr),
            ):
                industrial.append(categoryRow[0])

        res = connection.execute("""
                SELECT COUNT(bench.id) FROM Families AS fam
                JOIN Benchmarks AS bench ON bench.family = fam.id
                WHERE bench.logic = ?
                GROUP BY fam.id;
            """, (logic_name,))
        family_sizes = res.fetchall()
        family_sizes = list(map(lambda x: x[0], family_sizes))

        res = connection.execute("SELECT id,name,date FROM Evaluations")
        evaluations = res.fetchall()
        solvers = []
        evalDates = []
        for evalId, evalName, evalDate in evaluations:
            for logicSolversRow in connection.execute(
                """
                SELECT COUNT(DISTINCT s.id) FROM Solvers AS s
                    INNER JOIN SolverVariants AS sv ON sv.solver = s.id
                    INNER JOIN Results AS r ON sv.id = r.solverVariant
                    INNER JOIN Benchmarks AS b ON b.id = r.query
                WHERE b.logic LIKE ? AND r.evaluation=? AND b.isIncremental=0
                """,
                (logic_name, evalId),
            ):
                solvers.append(logicSolversRow[0])
                evalDates.append(evalDate)

        mydata = {
            "years": years,
            "solved": solved,
            "used": used,
            "fresh": fresh,
        }
        pf = pl.DataFrame(mydata)
        timelinechart = (
            alt.Chart(pf, title="Timeline")
            .transform_fold(["fresh", "used", "solved"], as_=["type", "value"])
            .mark_area()
            .encode(x="years:T", y="value:Q", color=alt.Color("type:N", legend=alt.Legend(title='Freshness')))
            .properties(width=800, height=300)
        )

        catdata = {
            "years": years,
            "industrial": industrial,
            "crafted": crafted,
            "random": random,
        }
        pf2 = pl.DataFrame(catdata)
        catchart = (
            alt.Chart(pf2, title="Category")
            .transform_fold(["industrial", "crafted", "random"], as_=["type", "value"])
            .mark_area()
            .encode(
                x=alt.X("years:T"),
                y=alt.Y("value:Q").stack("normalize"),
                color=alt.Color("type:N", 
                legend=alt.Legend(title='Category'))
            )
            .properties(width=800, height=300)
        )

        famsizedata = {"value": family_sizes}
        pf3 = pl.DataFrame(famsizedata)
        histochart = (
            alt.Chart(pf3, title="Family Size Histogram").mark_bar().encode(
                x=alt.X("value:Q", bin=True, title="Family Size"),
                y=alt.Y('count()', title="Famlilies"),
            )
            .properties(width=800, height=300)
        )

        solverdata = {
            "years": evalDates,
            "solvers": solvers,
        }
        pf4 = pl.DataFrame(solverdata)
        solverchart = (
            alt.Chart(pf4, title="Solvers")
            .transform_fold(["solvers"], as_=["type", "value"])
            .mark_line(size=2)
            .encode(
                x=alt.X("years:T"),
                y=alt.Y("value:Q")
            )
            .properties(width=800, height=300)
        )

        chartstring = (timelinechart & catchart & histochart & solverchart).to_html(fullhtml=False)

        print(f"\tWriting {logic_print_name}.html")
        logic_template.stream(logic=logic_print_name, charts=chartstring).dump(
            f"out/logics/{logic_print_name}.html"
        )
