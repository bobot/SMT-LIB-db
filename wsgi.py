"""
This is a simple webapp that lets users visualize the data stored for
individual benchmarks.

It is built on top of flask.  It expects the environment variable `SMTLIB_DB`
to be set to the filepath of the database file to use.

To run a local test server execute:
    SMTLIB_DB=./smtlib2025.sqlite flask --app wsgi run
"""

import sqlite3
import os
import polars as pl
import altair as alt
from flask import Flask, g, abort, render_template, request
from typing import *
from collections import defaultdict
from random import Random
import math


DATABASE = os.environ["SMTLIB_DB"]


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


app = Flask(__name__, static_folder="webapp/static", template_folder="webapp/templates")


@app.route("/")
def index():
    return render_template("index.html")


def get_benchmark(cursor, benchmark_id):
    for row in cursor.execute(
        """
        SELECT b.id, b.name, logic, s.folderName, s.date, isIncremental, size,
               b.compressedSize, l.name, l.link, l.spdxIdentifier, generatedOn,
               generatedBy, generator, application, description, category,
               passesDolmen, passesDolmenStrict,
               queryCount, family, s.firstOccurrence,
               s.name AS familyName,
               l.name AS licenseName
               FROM Benchmarks AS b
                  INNER JOIN Families AS s ON s.Id = b.family
                  INNER JOIN Licenses AS l ON l.Id = b.license
        WHERE b.id=?""",
        (benchmark_id,),
    ):
        return row
    return None


def get_queries(cursor, benchmark_id):
    res = cursor.execute(
        """
           SELECT id,idx FROM Queries WHERE benchmark=? 
           ORDER BY idx ASC
           LIMIT 151
           """,
        (benchmark_id,),
    )
    return res.fetchall()


def get_query(cursor, query_id):
    for row in cursor.execute(
        """
        SELECT * FROM Queries AS u
        WHERE u.id=?""",
        (query_id,),
    ):
        return row
    return None


# Returns the benchmark data, a list of queries, and the data
#         for the first query.
def get_canonical_benchmark_data(cursor, benchmark_id):
    benchmark = get_benchmark(cursor, benchmark_id)
    if benchmark:
        queries = get_queries(cursor, benchmark_id)
        firstId = queries[0]["id"]
        firstQuery = get_query(cursor, firstId)
        res = cursor.execute(
            """
            SELECT ev.name, ev.date, ev.link, sol.name AS solverName,
                   sovar.fullName, res.status, res.wallclockTime, res.cpuTime,
                   rat.rating, rat.consideredSolvers, rat.successfulSolvers
            FROM Results AS res
            INNER JOIN Evaluations AS ev ON res.evaluation = ev.id
            INNER JOIN SolverVariants AS sovar ON res.solverVariant = sovar.id
            INNER JOIN Solvers AS sol ON sovar.solver = sol.id
            LEFT JOIN Ratings AS rat ON rat.evaluation = ev.id AND rat.query = res.query
            WHERE res.query = ?
            ORDER BY ev.date, sol.id, sovar.id
               """,
            (firstId,),
        )
        evaluation = res.fetchall()
        return (benchmark, queries, firstQuery, evaluation)
    return (None, None, None, None)


@app.route("/benchmark/dynamic/<int:benchmark_id>")
def dynamic_benchmark(benchmark_id):
    cur = get_db().cursor()
    (benchmark, queries, first, evaluation) = get_canonical_benchmark_data(
        cur, benchmark_id
    )
    if benchmark:
        res = cur.execute(
            """
            SELECT s.name,sc.count FROM SymbolCounts AS sc
            INNER JOIN Symbols AS s ON s.id = sc.symbol
            WHERE sc.query=?
            ORDER BY s.id
            """,
            (first["id"],),
        )
        symbols = res.fetchall()
        return render_template(
            "benchmark.html",
            queries=queries,
            firstQuery=first,
            benchmark=benchmark,
            evaluation=evaluation,
            symbols=symbols,
        )
    abort(404)


@app.route("/query/dynamic/<int:query_id>")
def dynamic_query(query_id):
    cur = get_db().cursor()
    sb = get_query(cur, query_id)
    if sb:
        res = cur.execute(
            """
            SELECT s.name,sc.count FROM SymbolCounts AS sc
            INNER JOIN Symbols AS s ON s.id = sc.symbol
            WHERE sc.query=?
            ORDER BY s.id
            """,
            (query_id,),
        )
        symbols = res.fetchall()
        res = cur.execute(
            """
            SELECT ev.name, ev.date, ev.link, sol.name AS solverName,
                   sovar.fullName, res.status, res.wallclockTime, res.cpuTime,
                   rat.rating, rat.consideredSolvers, rat.successfulSolvers
            FROM Results AS res
            INNER JOIN Evaluations AS ev ON res.evaluation = ev.id
            INNER JOIN SolverVariants AS sovar ON res.solverVariant = sovar.id
            INNER JOIN Solvers AS sol ON sovar.solver = sol.id
            LEFT JOIN Ratings AS rat ON rat.evaluation = ev.id AND rat.query = res.query
            WHERE res.query = ?
            ORDER BY ev.date, sol.id, sovar.id
               """,
            (query_id,),
        )
        evaluation = res.fetchall()
        return render_template(
            "query.html", query=sb, symbols=symbols, evaluation=evaluation
        )
    abort(404)


@app.route("/benchmark/<int:benchmark_id>")
def show_benchmark(benchmark_id):
    cur = get_db().cursor()
    (benchmark, queries, first, evaluation) = get_canonical_benchmark_data(
        cur, benchmark_id
    )
    if benchmark:
        logicData = {"id": benchmark["id"], "logic": benchmark["logic"]}
        familyData = {
            "id": benchmark["family"],
            "name": benchmark["familyName"],
            "date": benchmark["date"],
        }
        benchmarkData = {"id": benchmark["id"], "name": benchmark["name"]}
        res = cur.execute(
            """
            SELECT s.name,sc.count FROM SymbolCounts AS sc
            INNER JOIN Symbols AS s ON s.id = sc.symbol
            WHERE sc.query=?""",
            (first["id"],),
        )
        symbols = res.fetchall()

        return render_template(
            "index.html",
            include="benchmark",
            benchmark=benchmark,
            queries=queries,
            firstQuery=first,
            logicData=logicData,
            familyData=familyData,
            benchmarkData=benchmarkData,
            evaluation=evaluation,
            symbols=symbols,
        )
    abort(404)


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


def retrieve_picked_data(cur, request):
    logicData = None
    familyData = None
    benchmarkData = None
    if "logic-id" in request.form:
        for row in cur.execute(
            "SELECT id,logic FROM Benchmarks WHERE id=?",
            (request.form["logic-id"],),
        ):
            logicData = row
    if "family-id" in request.form:
        for row in cur.execute(
            "SELECT id,date,name FROM Families WHERE id=?",
            (request.form["family-id"],),
        ):
            familyData = row
    if "benchmark-id" in request.form:
        for row in cur.execute(
            "SELECT id,name FROM Benchmarks WHERE id=?",
            (request.form["benchmark-id"],),
        ):
            benchmarkData = row

    return logicData, familyData, benchmarkData


@app.post("/search_logic")
def search_logic():
    logic = request.form.get("search-logic", None)
    family = request.form.get("family-id", None)
    benchmark = request.form.get("benchmark-id", None)
    cur = get_db().cursor()
    if family and benchmark:
        ret = cur.execute(
            """
           SELECT id,logic FROM Benchmarks
           WHERE logic LIKE '%'||?||'%'
           AND family=? AND id=?
           GROUP BY logic
           ORDER BY logic ASC
           LIMIT 101
           """,
            (logic, family, benchmark),
        )
    elif family:
        ret = cur.execute(
            """
           SELECT id,logic FROM Benchmarks
           WHERE logic LIKE '%'||?||'%'
           AND family=?
           GROUP BY logic
           ORDER BY logic ASC
           LIMIT 101
           """,
            (logic, family),
        )
    elif benchmark:
        ret = cur.execute(
            """
           SELECT id,logic FROM Benchmarks
           WHERE logic LIKE '%'||?||'%' AND id=?
           GROUP BY logic
           ORDER BY logic ASC
           LIMIT 101
           """,
            (logic, benchmark),
        )
    else:
        ret = cur.execute(
            """
           SELECT id,logic FROM Benchmarks
           WHERE logic LIKE '%'||?||'%'
           GROUP BY logic
           ORDER BY logic ASC
           LIMIT 101
           """,
            (logic,),
        )
    entries = ret.fetchall()
    ret.close()
    data = [{"id": row["id"], "value": row["logic"]} for row in entries]
    # The first entry is where the search bar is shown, the other two
    # are cleared via oob update.
    return render_template("search_suggestions.html", data=data, update="logic")


@app.post("/pick_logic/<int:logic_id>")
def pick_logic(logic_id):
    # Note: the logic_id is actually the benchmark id of a benchmark that
    # has that logic.
    cur = get_db().cursor()
    for row in cur.execute(
        "SELECT id,logic FROM Benchmarks WHERE id=?",
        (logic_id,),
    ):
        logicData, familyData, benchmarkData = retrieve_picked_data(cur, request)
        return render_template(
            "search_bar.html",
            logicData=row,
            familyData=familyData,
            benchmarkData=benchmarkData,
        )
    abort(404)


@app.post("/search_family")
def search_family():
    logic = request.form.get("search-logic", None)
    family = request.form.get("search-family", None)
    benchmark = request.form.get("benchmark-id", None)
    cur = get_db().cursor()
    if benchmark:
        ret = cur.execute(
            """
             SELECT s.id,s.date,s.name FROM Families as s
             INNER JOIN Benchmarks AS b ON b.family = s.id 
             WHERE s.name LIKE '%'||?||'%' AND b.id=?
             ORDER BY s.date ASC,
                      s.name ASC
             LIMIT 101
             """,
            (family, benchmark),
        )
    elif logic:
        ret = cur.execute(
            """
             SELECT s.id,s.date,s.name,s.folderName FROM Families AS s
             INNER JOIN Benchmarks AS b ON b.family = s.id
             WHERE s.name LIKE '%'||?||'%' AND b.logic=?
             GROUP BY s.folderName
             ORDER BY s.date ASC,
                      s.name ASC
             LIMIT 101
           """,
            (family, logic),
        )
    else:
        ret = cur.execute(
            """
            SELECT id,date,name FROM Families WHERE name LIKE '%'||?||'%'
            ORDER BY date ASC,
                     name ASC
            LIMIT 101
            """,
            (family,),
        )
    entries = ret.fetchall()
    ret.close()
    data = []
    for row in entries:
        if row["date"]:
            value = f"{row['date']} – {row['name']}"
        else:
            value = row["name"]
        data.append({"id": row["id"], "value": value})
    return render_template("search_suggestions.html", data=data, update="family")


@app.post("/pick_family/<int:family_id>")
def pick_family(family_id):
    cur = get_db().cursor()
    for row in cur.execute(
        "SELECT id,date,name FROM Families WHERE id=?",
        (family_id,),
    ):
        logicData, familyData, benchmarkData = retrieve_picked_data(cur, request)
        return render_template(
            "search_bar.html",
            logicData=logicData,
            familyData=row,
            benchmarkData=benchmarkData,
        )
    abort(404)


@app.post("/search_benchmark")
def search_benchmark():
    logic = request.form.get("logic-id", None)
    family = request.form.get("family-id", None)
    benchmark = request.form.get("search-benchmark", None)
    cur = get_db().cursor()
    if logic and family:
        ret = cur.execute(
            """
           SELECT id,name FROM Benchmarks
           WHERE name LIKE '%'||?||'%'
           AND logic=(SELECT logic FROM Benchmarks WHERE id=?)
           AND family=?
           ORDER BY name ASC
           LIMIT 101
           """,
            (benchmark, logic, family),
        )
    elif logic:
        ret = cur.execute(
            """
           SELECT id,name FROM Benchmarks
           WHERE name LIKE '%'||?||'%'
           AND logic=(SELECT logic FROM Benchmarks WHERE id=?)
           ORDER BY name ASC
           LIMIT 101
           """,
            (benchmark, logic),
        )
    elif family:
        ret = cur.execute(
            """
           SELECT id,name FROM Benchmarks
           WHERE name LIKE '%'||?||'%'
           AND family=?
           ORDER BY name ASC
           LIMIT 101
           """,
            (benchmark, family),
        )
    else:
        ret = cur.execute(
            """
           SELECT id,name FROM Benchmarks
           WHERE name LIKE '%'||?||'%'
           ORDER BY name ASC
           LIMIT 101
           """,
            (benchmark,),
        )
    entries = ret.fetchall()
    ret.close()
    data = [{"id": row["id"], "value": row["name"]} for row in entries]
    return render_template("search_suggestions.html", data=data, update="benchmark")


@app.post("/pick_benchmark/<int:benchmark_id>")
def pick_benchmark(benchmark_id):
    # Note: the benchmark_id is actually the benchmark id of a benchmark that
    # has that benchmark.
    cur = get_db().cursor()
    for row in cur.execute(
        "SELECT id,name,logic,family FROM Benchmarks WHERE id=?",
        (benchmark_id,),
    ):
        logicData = {"id": row["id"], "logic": row["logic"]}
        for familyRow in cur.execute(
            "SELECT id,date,name FROM Families WHERE id=?",
            (row["family"],),
        ):
            return render_template(
                "search_bar.html",
                logicData=logicData,
                familyData=familyRow,
                benchmarkData=row,
            )
    abort(404)


@app.post("/clear_input/<string:input>")
def clear_input(input):
    if not input in ["logic", "family", "benchmark"]:
        abort(404)
    logic = request.form.get("logic-id", None)
    logicValue = request.form.get("search-logic", None)
    if input != "logic" and logic:
        logicData = {"id": logic, "logic": logicValue}
    else:
        logicData = None
    family = request.form.get("family-id", None)
    familyDate = request.form.get("date-store", None)
    familyValue = request.form.get("search-family", None)
    if input != "family" and family:
        familyData = {
            "id": family,
            "name": familyValue,
            "date": familyDate,
        }
    else:
        familyData = None
    benchmark = request.form.get("benchmark-id", None)
    benchmarkValue = request.form.get("search-benchmark", None)
    if input != "benchmark" and benchmark:
        benchmarkData = {"id": benchmark, "name": benchmarkValue}
    else:
        benchmarkData = None
    return render_template(
        "search_bar.html",
        logicData=logicData,
        familyData=familyData,
        benchmarkData=benchmarkData,
    )


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()
