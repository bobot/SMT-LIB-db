import sqlite3
from flask import Flask, g, abort, render_template, request

DATABASE = "smtlib_post.sqlite"


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


@app.route("/benchmark/<int:benchmark_id>")
def show_benchmark(benchmark_id):
    cur = get_db().cursor()
    for row in cur.execute(
        """
        SELECT filename, logic, s.folderName, s.date, isIncremental, size,
               compressedSize, l.name, l.link, l.spdxIdentifier, generatedOn,
               generatedBy, generator, application, description, category,
               subbenchmarkCount FROM Benchmarks AS b
                  INNER JOIN Sets AS s ON s.Id = b.benchmarkSet
                  INNER JOIN Licenses AS l ON l.Id = b.license
        WHERE b.id=?""",
        (benchmark_id,),
    ):
        return render_template("benchmark.html", benchmark=row)
    abort(404)


def retrieve_picked_data(cur, request):
    logicData = None
    setData = None
    benchmarkData = None
    if "logic-id" in request.form:
        for row in cur.execute(
            "SELECT id,logic FROM Benchmarks WHERE id=?",
            (request.form["logic-id"],),
        ):
            logicData = row
    if "set-id" in request.form:
        for row in cur.execute(
            "SELECT id,date,name FROM Sets WHERE id=?",
            (request.form["set-id"],),
        ):
            setData = row
    if "benchmark-id" in request.form:
        for row in cur.execute(
            "SELECT id,filename FROM Benchmarks WHERE id=?",
            (request.form["benchmark-id"],),
        ):
            benchmarkData = row

    return logicData, setData, benchmarkData


@app.post("/search_logic")
def search_logic():
    logic = request.form.get("search-logic", None)
    benchmarkSet = request.form.get("set-id", None)
    benchmark = request.form.get("benchmark-id", None)
    cur = get_db().cursor()
    if benchmarkSet and benchmark:
        ret = cur.execute(
            """
           SELECT id,logic FROM Benchmarks
           WHERE logic LIKE '%'||?||'%'
           AND benchmarkSet=? AND id=?
           GROUP BY logic
           ORDER BY logic ASC
           LIMIT 101
           """,
            (logic, benchmarkSet, benchmark),
        )
    elif benchmarkSet:
        ret = cur.execute(
            """
           SELECT id,logic FROM Benchmarks
           WHERE logic LIKE '%'||?||'%'
           AND benchmarkSet=?
           GROUP BY logic
           ORDER BY logic ASC
           LIMIT 101
           """,
            (logic, benchmarkSet),
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
        logicData, setData, benchmarkData = retrieve_picked_data(cur, request)
        return render_template(
            "search_bar.html",
            logicData=row,
            setData=setData,
            benchmarkData=benchmarkData,
        )
    abort(404)


@app.post("/search_set")
def search_set():
    logic = request.form.get("logic-id", None)
    benchmarkSet = request.form.get("search-set", None)
    benchmark = request.form.get("benchmark-id", None)
    cur = get_db().cursor()
    if benchmark:
        ret = cur.execute(
            """
             SELECT s.id,s.date,s.name FROM Sets as s
             INNER JOIN Benchmarks AS b ON b.benchmarkSet = s.id 
             WHERE s.name LIKE '%'||?||'%' AND b.id=?
             ORDER BY s.date ASC,
                      s.name ASC
             LIMIT 101
             """,
            (benchmarkSet, benchmark),
        )
    elif logic:
        ret = cur.execute(
            """
             SELECT id,date,name FROM Sets AS s
             WHERE s.name LIKE '%'||?||'%'
             AND EXISTS (SELECT 1 FROM Benchmarks WHERE benchmarkSet = s.id
                AND id = ?)
             ORDER BY date ASC,
                      name ASC
             LIMIT 101
           """,
            (benchmarkSet, logic),
        )
    else:
        ret = cur.execute(
            """
            SELECT id,date,name FROM Sets WHERE name LIKE '%'||?||'%'
            ORDER BY date ASC,
                     name ASC
            LIMIT 101
            """,
            (benchmarkSet,),
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
    return render_template("search_suggestions.html", data=data, update="set")


@app.post("/pick_set/<int:set_id>")
def pick_set(set_id):
    cur = get_db().cursor()
    for row in cur.execute(
        "SELECT id,date,name FROM Sets WHERE id=?",
        (set_id,),
    ):
        logicData, setData, benchmarkData = retrieve_picked_data(cur, request)
        return render_template(
            "search_bar.html",
            logicData=logicData,
            setData=row,
            benchmarkData=benchmarkData,
        )
    abort(404)


@app.post("/search_benchmark")
def search_benchmark():
    logic = request.form.get("logic-id", None)
    benchmarkSet = request.form.get("set-id", None)
    benchmark = request.form.get("search-benchmark", None)
    cur = get_db().cursor()
    if logic and benchmarkSet:
        ret = cur.execute(
            """
           SELECT id,filename FROM Benchmarks
           WHERE filename LIKE '%'||?||'%'
           AND logic=(SELECT logic FROM Benchmarks WHERE id=?)
           AND benchmarkSet=?
           ORDER BY filename ASC
           LIMIT 101
           """,
            (benchmark, logic, benchmarkSet),
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
    elif benchmarkSet:
        ret = cur.execute(
            """
           SELECT id,filename FROM Benchmarks
           WHERE filename LIKE '%'||?||'%'
           AND benchmarkSet=?
           ORDER BY filename ASC
           LIMIT 101
           """,
            (benchmark, benchmarkSet),
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
        "SELECT id,filename,logic,benchmarkSet FROM Benchmarks WHERE id=?",
        (benchmark_id,),
    ):
        logicData = {"id": row["id"], "logic": row["logic"]}
        for setRow in cur.execute(
            "SELECT id,date,name FROM Sets WHERE id=?",
            (row["benchmarkSet"],),
        ):
            return render_template(
                "search_bar.html",
                logicData=logicData,
                setData=setRow,
                benchmarkData=row,
            )
    abort(404)


@app.post("/clear_input/<string:input>")
def clear_input(input):
    if not input in ["logic", "set", "benchmark"]:
        abort(404)
    logic = request.form.get("logic-id", None)
    logicValue = request.form.get("search-logic", None)
    if input != "logic" and logic:
        logicData = {"id": logic, "logic": logicValue}
    else:
        logicData = None
    benchmarkSet = request.form.get("set-id", None)
    benchmarkSetDate = request.form.get("date-store", None)
    benchmarkSetValue = request.form.get("search-logic", None)
    if input != "set" and benchmarkSet:
        benchmarkSetData = {
            "id": benchmarkSet,
            "name": benchmarkSetValue,
            "date": benchmarkSetDate,
        }
    else:
        benchmarkSetData = None
    benchmark = request.form.get("benchmark-id", None)
    benchmarkValue = request.form.get("search-benchmark", None)
    if input != "benchmark" and benchmark:
        benchmarkData = {"id": benchmark, "filename": benchmarkValue}
    else:
        benchmarkData = None
    return render_template(
        "search_bar.html",
        logicData=logicData,
        setData=benchmarkSetData,
        benchmarkData=benchmarkData,
    )


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()
