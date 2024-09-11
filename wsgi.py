import sqlite3
import os
from flask import Flask, g, abort, render_template, request

DATABASE = os.environ['SMTLIB_DB']

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
        SELECT b.id, filename, logic, s.folderName, s.date, isIncremental, size,
               b.compressedSize, l.name, l.link, l.spdxIdentifier, generatedOn,
               generatedBy, generator, application, description, category,
               passesDolmen, passesDolmenStrict,
               subbenchmarkCount, family,
               s.name AS familyName
               FROM Benchmarks AS b
                  INNER JOIN Families AS s ON s.Id = b.family
                  INNER JOIN Licenses AS l ON l.Id = b.license
        WHERE b.id=?""",
        (benchmark_id,),
    ):
        return row
    return None


def get_subbenchmarks(cursor, benchmark_id):
    res = cursor.execute(
        """
           SELECT id,number FROM Subbenchmarks WHERE benchmark=? 
           ORDER BY number ASC
           """,
        (benchmark_id,),
    )
    return res.fetchall()


def get_subbenchmark(cursor, subbenchmark_id):
    for row in cursor.execute(
        """
        SELECT * FROM Subbenchmarks AS u
        WHERE u.id=?""",
        (subbenchmark_id,),
    ):
        return row
    return None


# Returns the benchmark data, a list of subbenchmarks, and the data
#         for the first subbenchmark.
def get_canonical_benchmark_data(cursor, benchmark_id):
    benchmark = get_benchmark(cursor, benchmark_id)
    if benchmark:
        subbenchmarks = get_subbenchmarks(cursor, benchmark_id)
        firstSubbenchmark = get_subbenchmark(cursor, subbenchmarks[0]["id"])
        return (benchmark, subbenchmarks, firstSubbenchmark)
    return (None, None, None)


@app.route("/benchmark/dynamic/<int:benchmark_id>")
def dynamic_benchmark(benchmark_id):
    cur = get_db().cursor()
    (benchmark, subbenchmarks, first) = get_canonical_benchmark_data(cur, benchmark_id)
    if benchmark:
        return render_template(
            "benchmark.html",
            subbenchmarks=subbenchmarks,
            firstSubbenchmark=first,
            benchmark=benchmark,
        )
    abort(404)


@app.route("/subbenchmark/dynamic/<int:subbenchmark_id>")
def dynamic_subbenchmark(subbenchmark_id):
    cur = get_db().cursor()
    sb = get_subbenchmark(cur, subbenchmark_id)
    if sb:
        return render_template("subbenchmark.html", subbenchmark=sb)
    abort(404)


@app.route("/benchmark/<int:benchmark_id>")
def show_benchmark(benchmark_id):
    cur = get_db().cursor()
    (benchmark, subbenchmarks, first) = get_canonical_benchmark_data(cur, benchmark_id)
    if benchmark:
        logicData = {"id": benchmark["id"], "logic": benchmark["logic"]}
        familyData = {
            "id": benchmark["family"],
            "name": benchmark["familyName"],
            "date": benchmark["date"],
        }
        benchmarkData = {"id": benchmark["id"], "filename": benchmark["filename"]}

        return render_template(
            "index.html",
            include="benchmark",
            benchmark=benchmark,
            subbenchmarks=subbenchmarks,
            firstSubbenchmark=first,
            logicData=logicData,
            familyData=familyData,
            benchmarkData=benchmarkData,
        )
    abort(404)


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
            "SELECT id,filename FROM Benchmarks WHERE id=?",
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
           SELECT id,filename FROM Benchmarks
           WHERE filename LIKE '%'||?||'%'
           AND logic=(SELECT logic FROM Benchmarks WHERE id=?)
           AND family=?
           ORDER BY filename ASC
           LIMIT 101
           """,
            (benchmark, logic, family),
        )
    elif logic:
        ret = cur.execute(
            """
           SELECT id,filename FROM Benchmarks
           WHERE filename LIKE '%'||?||'%'
           AND logic=(SELECT logic FROM Benchmarks WHERE id=?)
           ORDER BY filename ASC
           LIMIT 101
           """,
            (benchmark, logic),
        )
    elif family:
        ret = cur.execute(
            """
           SELECT id,filename FROM Benchmarks
           WHERE filename LIKE '%'||?||'%'
           AND family=?
           ORDER BY filename ASC
           LIMIT 101
           """,
            (benchmark, family),
        )
    else:
        ret = cur.execute(
            """
           SELECT id,filename FROM Benchmarks
           WHERE filename LIKE '%'||?||'%'
           ORDER BY filename ASC
           LIMIT 101
           """,
            (benchmark,),
        )
    entries = ret.fetchall()
    ret.close()
    data = [{"id": row["id"], "value": row["filename"]} for row in entries]
    return render_template("search_suggestions.html", data=data, update="benchmark")


@app.post("/pick_benchmark/<int:benchmark_id>")
def pick_benchmark(benchmark_id):
    # Note: the benchmark_id is actually the benchmark id of a benchmark that
    # has that benchmark.
    cur = get_db().cursor()
    for row in cur.execute(
        "SELECT id,filename,logic,family FROM Benchmarks WHERE id=?",
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
        benchmarkData = {"id": benchmark, "filename": benchmarkValue}
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
