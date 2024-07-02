import tempfile
import subprocess
import csv
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
            f"tar xvf {folder}/{year}/results/raw-results.tar.xz -C {folder}/{year}/results",
            shell=True,
        )
        subprocess.run(
            f"{folder}/{year}/scoring/clean_result_csvs.sh", shell=True, cwd=tmpdir
        )
        with open(f"{tmpdir}/results-sq.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")
            for row in reader:
                solver = row["solver"]
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
                    continue

                # remove the 'track_single_query/' from the start
                fullbench = row["benchmark"][19:]
                benchmarkId = benchmarks.guess_benchmark_id(
                    connection, fullbench, isIncremental=False
                )
                if not benchmarkId:
                    # print(f"WARNING: Benchmark {fullbench} of SMT-COMP {year} not found")
                    continue
                for r in connection.execute(
                    """
                    SELECT Id FROM Subbenchmarks WHERE benchmark=?
                    """,
                    (benchmarkId,),
                ):
                    subbenchmarkId = r[0]

                try:
                    cpuTime = float(row["cpu time"])
                except ValueError:
                    cpuTime = None
                try:
                    wallclockTime = float(row["wallclock time"])
                except ValueError:
                    wallclockTime = None

                if row["result"] == "starexec-unknown":
                    status = "unknown"
                elif row["result"] != row["expected"]:
                    status = "unknown"
                else:
                    status = row["result"]

                # TODO: subbenchmark is here actually the benchmark ID
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
                        status,
                    ),
                )
    connection.commit()


def add_smt_comps(connection, folder):
    add_smt_comp_generic(connection, folder, "2021", "2021-07-18")
    # add_smt_comp_generic(connection, folder, "2022", "2022-08-10")
    # add_smt_comp_generic(connection, folder, "2023", "2023-07-06")


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
    print("Adding ratings for SMT-COMP 2022")
    add_ratings_for(connection, "SMT-COMP 2022")
    print("Adding ratings for SMT-COMP 2023")
    add_ratings_for(connection, "SMT-COMP 2023")
