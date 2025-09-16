import sqlite3
import os
import polars as pl
import altair as alt
from flask import Flask, g, abort, render_template, request
from typing import *
from collections import defaultdict
from random import Random
import math

U = TypeVar("U")


def correlation_sorting(
    solvers: List[U], corrs: Mapping[Tuple[U, U], float], nb_iteration: int
) -> None:
    """
    Strangely I can't find an easy to use lib creating a well clustered correlation matrix. block modelling.

    We use simulated annealing
    """
    if len(solvers) <= 2:
        return

    r = Random(0)

    def neighbor(i: int) -> float:
        s = 0.0
        n = 0.0
        for off in range(-4, 4):
            if off == 0:
                continue
            # Try to break the symmetry left-right
            if off > 0:
                bias = 0.1
            else:
                bias = 0.0
            if 0 <= i + off and i + off < len(solvers):
                coef = (1.0 + bias) / abs(off)
                s += (1.0 - corrs[solvers[i + off], solvers[i]]) * coef
                n += coef
        # At the bounds there is only one neighbor
        return s / n

    def swap(i: int, j: int) -> None:
        tmp = solvers[i]
        solvers[i] = solvers[j]
        solvers[j] = tmp

    for i in range(0, nb_iteration):
        # Differrent selection heuristics
        if False:
            a = r.randint(0, len(solvers) - 2)
            b = a + 1
        elif False:
            a = r.randint(0, len(solvers) - 1)
            b = r.randint(0, len(solvers) - 2)
            if a <= b:
                b += 1
        else:
            a = r.randint(0, len(solvers) - 2)
            b = r.randint(a + 1, len(solvers) - 1)
        s1 = neighbor(a) + neighbor(b)
        swap(a, b)
        s2 = neighbor(a) + neighbor(b)
        swap(a, b)
        t = 1 - (i / (nb_iteration + 1))
        if s2 < s1 or math.exp((s1 - s2) / t) > r.uniform(0.0, 1.0):
            swap(a, b)


c_query = pl.col("id")
c_name = pl.col("name")
c_solver = pl.col("solver")
c_solver2 = pl.col("solver2")
c_ev_id = pl.col("ev_id")
c_ev_id2 = pl.col("ev_id2")
c_cpuTime = pl.col("cpuTime")
c_cpuTime2 = pl.col("cpuTime2")
c_status = pl.col("status")
c_status2 = pl.col("status2")
c_bucket = pl.col("bucket")
c_bucket2 = pl.col("bucket2")


def init_routes(app, get_db):
    @app.route("/charts/<string:logic_name>")
    def show_charts(logic_name):
        df = pl.read_database(
            query="""
            SELECT ev.name, ev.date, ev.link, ev.id as ev_id, sol.name AS solver,
                       sovar.fullName, res.status, res.cpuTime,
                       query.id, bench.logic
                FROM Results AS res
                INNER JOIN Benchmarks AS bench ON bench.id = query.benchmark
                INNER JOIN Queries AS query ON res.query = query.id
                INNER JOIN Evaluations AS ev ON res.evaluation = ev.id
                INNER JOIN SolverVariants AS sovar ON res.solverVariant = sovar.id
                INNER JOIN Solvers AS sol ON sovar.solver = sol.id
                WHERE bench.logic = ?""",
            execute_options={"parameters": [logic_name]},
            connection=get_db(),
            schema_overrides={"wallclockTime": pl.Float64, "cpuTime": pl.Float64},
        )
        results = (
            df.lazy()
            .filter(c_cpuTime.is_not_null())
            .with_columns(
                bucket=pl.lit(10.0).pow(c_cpuTime.log(10).floor()),
                solver=pl.concat_str(c_solver, c_name, separator=" "),
            )
        )

        results_with = results.select(
            c_query,
            solver2=c_solver,
            ev_id2=c_ev_id,
            bucket2=c_bucket,
            cpuTime2=c_cpuTime,
            status2=c_status,
        )

        cross_results = results.join(results_with, on=[c_query], how="left")

        corr = (
            cross_results.group_by(c_solver, c_solver2)
            .agg(corr=pl.corr(c_cpuTime, c_cpuTime2, method="pearson"))
            .sort(c_solver, c_solver2)
            .select(c_solver, c_solver2, "corr")
        )

        cross_results = (
            cross_results.group_by(
                c_solver,
                c_solver2,
                c_status,
                c_status2,
                c_bucket,
                c_bucket2,
            )
            .len()
            .sort(c_solver, c_solver2)
        )

        df_corr, df_results, df_buckets, df_status, df_solvers = pl.collect_all(
            [
                corr,
                cross_results,
                results.select(c_bucket.unique()),
                results.select(c_status.unique()),
                results.select(c_solver.unique()),
            ]
        )

        bucket_domain: list[float] = list(df_buckets["bucket"])
        status_domain: list[int] = list(df_status["status"])
        status_domain.sort()

        solver_domain: list[str, str] = list(df_solvers["solver"])
        solver_domain.sort(key=lambda x: x.lower())

        if True:
            # Two provers can have no benchmars in common, their pairs is not in df_corrs
            corrs: DefaultDict[Tuple[str, str], float] = defaultdict(lambda: 0.0)
            for row in df_corr.rows(named=False):
                corrs[row[0], row[1]] = row[2]
            correlation_sorting(solver_domain, corrs, 10000)

        # Create heatmap with selection
        solvers = alt.selection_point(
            fields=["solver", "solver2"],
            name="solvers",
            value=[
                {
                    "solver": solver_domain[0],
                    "solver2": solver_domain[min(1, len(solver_domain) - 1)],
                }
            ],
            toggle=False,
        )
        answer_xy = alt.selection_point(fields=["answer", "answer2"], name="answer")
        logic = alt.selection_point(fields=["logic"], name="logic")
        division = alt.selection_point(fields=["division"], name="division")
        g_select_provers = (
            alt.Chart(df_corr, title="Click a tile to compare solvers")
            .mark_rect()
            .encode(
                alt.X("solver", title="solver1").scale(domain=solver_domain),
                alt.Y("solver2", title="solver2").scale(
                    domain=list(reversed(solver_domain))
                ),
                alt.Color("corr", scale=alt.Scale(domain=[-1, 1], scheme="blueorange")),
                stroke=alt.when(solvers).then(alt.value("lightgreen")),
                strokeWidth=alt.value(3),
                opacity=alt.value(0.8),
            )
            .add_params(solvers)
        )

        with alt.data_transformers.disable_max_rows():
            charts = g_select_provers.to_html(fullhtml=False)

        return render_template(
            "charts.html",
            logicData=logic_name,
            printed=df_corr._repr_html_(),
            charts=charts,
        )
