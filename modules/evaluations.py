import tempfile
import subprocess
import json
import csv

from pathlib import Path
from modules import benchmarks

import modules.solvers


def setup_evaluations(connection):
    connection.execute(
        """CREATE TABLE Evaluations(
        id INTEGER PRIMARY KEY,
        name TEXT,
        date DATE,
        link TEXT
        );"""
    )

    connection.execute(
        """CREATE TABLE Results(
        id INTEGER PRIMARY KEY,
        evaluation INTEGER,
        subbenchmark INT,
        solverVariant INT,
        cpuTime REAL,
        wallclockTime REAL,
        status TEXT,
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
        FOREIGN KEY(solverVariant) REFERENCES SolverVaraiants(id)
        );"""
    )

    connection.execute(
        """CREATE TABLE Ratings(
        id INTEGER PRIMARY KEY,
        subbenchmark INT,
        evaluation INT,
        rating REAL,
        consideredSolvers INT,
        successfulSolvers INT,
        FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        );"""
    )


def write_result(
    connection, evaluationId, solver, subbenchmarkId, outcome, cpuTime, wallclockTime
):
    solverVariantId = None
    for r in connection.execute(
        """
            SELECT Id FROM SolverVariants WHERE fullName=? AND evaluation=?
            """,
        (solver, evaluationId),
    ):
        solverVariantId = r[0]
    if not solverVariantId:
        # We do not care about the results from solvers that are not on the list.
        # Note that some solvers are omitted on purpose, for example
        # if there is a fixed version.
        print(f"nf: {solver}")
        return
    connection.execute(
        """
            INSERT INTO Results(evaluation, subbenchmark, solverVariant, cpuTime, wallclockTime, status)
            VALUES(?,?,?,?,?,?);
            """,
        (
            evaluationId,
            subbenchmarkId,
            solverVariantId,
            cpuTime,
            wallclockTime,
            outcome,
        ),
    )


# CSV format used 2014
def add_smt_comp_2014(connection, compressedCsvFilename):
    name = f"SMT-COMP 2014"
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link)
        VALUES(?,?,?);
        """,
        (name, "2014-07-21", f"https://smt-comp.github.io/2014/"),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding SMT-COMP 2014 results")
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            f"tar -xf '{compressedCsvFilename}'",
            cwd=tmpdir,
            shell=True,
        )
        csvName = Path(compressedCsvFilename.stem).stem
        with open(f"{tmpdir}/{csvName}.csv", newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            for row in reader:
                solver = f"{row[3]} {row[5]}"
                cpuTime = row[8]
                wallclockTime = row[9]
                status = row[10]
                # Discard disagreements
                if status == "starexec-unknown":
                    status = "unknown"
                else:
                    if row[11] != "starexec-unknown" and status != "starexec-unknown":
                        status = "unknown"
                benchmarkField = row[1].split("/")
                logic = benchmarkField[0]
                benchmarkSet = benchmarkField[1]
                benchmarkName = "/".join(benchmarkField[2:])
                benchmarkId = benchmarks.guess_benchmark_id(
                    connection, False, logic, benchmarkSet, benchmarkName
                )
                if not benchmarkId:
                    print(f"WARNING: Benchmark {fullbench} of SMT-COMP {year} not found")
                    continue
                for r in connection.execute(
                    """
                    SELECT Id FROM Subbenchmarks WHERE benchmark=?
                    """,
                    (benchmarkId,),
                ):
                    subbenchmarkId = r[0]
                write_result(
                    connection,
                    evaluationId,
                    solver,
                    subbenchmarkId,
                    status,
                    cpuTime,
                    wallclockTime,
                )
    connection.commit()


# CSV format used 2015-2017
def add_smt_comp_oldstyle(connection, compressedCsvFilename, year, date):
    name = f"SMT-COMP {year}"
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link)
        VALUES(?,?,?);
        """,
        (name, date, f"https://smt-comp.github.io/{year}/"),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding oldstyle SMT-COMP {year} results")
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            f"tar -xf '{compressedCsvFilename}'",
            cwd=tmpdir,
            shell=True,
        )
        csvName = Path(compressedCsvFilename.stem).stem
        with open(f"{tmpdir}/{csvName}.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")
            for row in reader:
                solver = f"{row['solver']} {row['configuration']}"
                cpuTime = row["cpu time"]
                wallclockTime = row["wallclock time"]
                status = row["result"]
                # Discard disagreements
                if status == "starexec-unknown":
                    status = "unknown"
                else:
                    if (
                        row["expected"] != "starexec-unknown"
                        and status != "starexec-unknown"
                    ):
                        status = "unknown"
                benchmarkField = row["benchmark"].split("/")
                logic = benchmarkField[0]
                benchmarkSet = benchmarkField[1]
                benchmarkName = "/".join(benchmarkField[2:])
                benchmarkId = benchmarks.guess_benchmark_id(
                    connection, False, logic, benchmarkSet, benchmarkName
                )
                if not benchmarkId:
                    print(f"WARNING: Benchmark {fullbench} of SMT-COMP {year} not found")
                    continue
                for r in connection.execute(
                    """
                    SELECT Id FROM Subbenchmarks WHERE benchmark=?
                    """,
                    (benchmarkId,),
                ):
                    subbenchmarkId = r[0]
                write_result(
                    connection,
                    evaluationId,
                    solver,
                    subbenchmarkId,
                    status,
                    cpuTime,
                    wallclockTime,
                )
    connection.commit()


def add_smt_comp_generic(connection, folder, year, date):
    name = f"SMT-COMP {year}"
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link)
        VALUES(?,?,?);
        """,
        (name, date, f"https://smt-comp.github.io/{year}/"),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding SMT-COMP {year} results")
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            f"gunzip -fk {folder}/data/results-sq-{year}.json.gz",
            shell=True,
        )
        with open(f"{folder}/data/results-sq-{year}.json") as resultfile:
            jsonObject = json.load(resultfile)
            results = jsonObject["results"]
            for result in results:
                assert result["track"] == "SingleQuery"
                solver = result["solver"]

                fileField = result["file"]
                setField = fileField["family"][0]
                fullbench = "/".join(fileField["family"][1:] + [fileField["name"]])

                benchmarkId = benchmarks.guess_benchmark_id(
                    connection, False, fileField["logic"], setField, fullbench
                )
                if not benchmarkId:
                    print(f"WARNING: Benchmark {fullbench} of SMT-COMP {year} not found")
                    continue
                for r in connection.execute(
                    """
                    SELECT Id FROM Subbenchmarks WHERE benchmark=?
                    """,
                    (benchmarkId,),
                ):
                    subbenchmarkId = r[0]

                cpuTime = result["cpu_time"]
                wallclockTime = result["wallclock_time"]
                status = result["result"]
                write_result(
                    connection,
                    evaluationId,
                    solver,
                    subbenchmarkId,
                    status,
                    cpuTime,
                    wallclockTime,
                )

    connection.commit()


def add_smt_comps(connection, smtcompwwwfolder, smtcompfolder):
    path2014 = smtcompfolder / "2014/csv/combined.tar.xz"
    add_smt_comp_2014(connection, path2014)
    path2015 = smtcompfolder / "2015/csv/Main_Track.tar.xz"
    add_smt_comp_oldstyle(connection, path2015, "2015", "2015-07-02")
    path2016 = smtcompfolder / "2016/csv/Main_Track.tar.xz"
    add_smt_comp_oldstyle(connection, path2016, "2016", "2016-07-02")
    path2017 = smtcompfolder / "2017/csv/Main_Track.tar.xz"
    add_smt_comp_oldstyle(connection, path2017, "2017", "2017-07-23")
    add_smt_comp_generic(connection, smtcompwwwfolder, "2018", "2018-07-14")
    add_smt_comp_generic(connection, smtcompwwwfolder, "2019", "2019-07-07")
    add_smt_comp_generic(connection, smtcompwwwfolder, "2020", "2020-07-06")
    add_smt_comp_generic(connection, smtcompwwwfolder, "2021", "2021-07-18")
    add_smt_comp_generic(connection, smtcompwwwfolder, "2022", "2022-08-10")
    add_smt_comp_generic(connection, smtcompwwwfolder, "2023", "2023-07-06")


def add_ratings_for(connection, competition):
    """
    - for each logic
        - calculate n = |solvers that solve at least one benchmark|
        - for each benchmark
                - calculate m = |solvers that solve that benchmark|
                - rating = 1 - m/n
    """
    for r in connection.execute(
        """
        SELECT Id FROM Evaluations WHERE name=?
        """,
        (competition,),
    ):
        evaluationId = r[0]

    for logicRow in connection.execute(
        """
        SELECT DISTINCT logic FROM Benchmarks
        """
    ):
        logic = logicRow[0]
        for logicSolversRow in connection.execute(
            """
            SELECT COUNT(DISTINCT sv.id) FROM SolverVariants AS sv 
                INNER JOIN Results AS r ON sv.Id = r.solverVariant
                INNER JOIN Benchmarks AS b ON b.id = r.subbenchmark
            WHERE (r.status = 'unsat' OR r.status = 'sat')
                AND b.logic=? AND r.evaluation=?
            """,
            (logic, evaluationId),
        ):
            logicSolvers = logicSolversRow[0]
        if logicSolvers == 0:
            continue
        for benchmarkRow in connection.execute(
            """
            SELECT id FROM Benchmarks WHERE logic=?
            """,
            (logic,),
        ):
            benchmark = benchmarkRow[0]
            for benchmarkSolversRow in connection.execute(
                """
                SELECT COUNT(DISTINCT sv.id) FROM SolverVariants AS sv 
                    INNER JOIN Results AS r ON sv.Id = r.solverVariant
                    INNER JOIN Benchmarks AS b ON b.id = r.subbenchmark
                WHERE (r.status = 'unsat' OR r.status = 'sat')
                    AND b.id=? AND r.evaluation=?
                """,
                (benchmark, evaluationId),
            ):
                benchmarkSolvers = benchmarkSolversRow[0]
            rating = 1 - benchmarkSolvers / logicSolvers
            connection.execute(
                """
                INSERT INTO Ratings(subbenchmark, evaluation, rating, consideredSolvers, successfulSolvers)
                VALUES(?,?,?,?,?);
                """,
                (benchmark, evaluationId, rating, logicSolvers, benchmarkSolvers),
            )
    connection.commit()


def add_ratings(connection):
    return
    print("Adding ratings for SMT-COMP 2018")
    add_ratings_for(connection, "SMT-COMP 2018")
    print("Adding ratings for SMT-COMP 2019")
    add_ratings_for(connection, "SMT-COMP 2019")
    print("Adding ratings for SMT-COMP 2020")
    add_ratings_for(connection, "SMT-COMP 2020")
    print("Adding ratings for SMT-COMP 2021")
    add_ratings_for(connection, "SMT-COMP 2021")
    print("Adding ratings for SMT-COMP 2022")
    add_ratings_for(connection, "SMT-COMP 2022")
    print("Adding ratings for SMT-COMP 2023")
    add_ratings_for(connection, "SMT-COMP 2023")
