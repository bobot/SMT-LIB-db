import tempfile
import subprocess
import json
import csv
import re

from pathlib import Path
from modules import benchmarks
from bs4 import BeautifulSoup

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


def make_stats_dict(name):
    return {
        "name": name,
        "lookups": 0,
        "lookupFailures": 0,
        "benchmarks": set(),
        "unkownBenchmarks": set(),
    }


def print_stats_dict(stats):
    lookupPercentage = stats["lookupFailures"] / stats["lookups"] * 100.0
    benchmarkPercentage = (
        len(stats["unkownBenchmarks"]) / len(stats["benchmarks"]) * 100.0
    )
    print(
        f"{stats['name']}\t\tMissing entries: {stats['lookupFailures']} {lookupPercentage:.2f}% Unknown Benchmark: {stats['lookupFailures']} {lookupPercentage:.2f}%"
    )


def benchmark_status(solved_status, expected="unkown"):
    if solved_status in ["-", "starexec-unknown"]:
        solved_status = "unknown"
    if (
        expected in ["sat", "unsat"]
        and solved_status in ["sat", "unsat"]
        and not expected == solved_status
    ):
        return "unknown"
    return solved_status


old_header_regex = r"^Detailed results for (.+) at ([A-Z0-9_]+)$"


def add_smt_comp_early(connection, year, date):
    name = f"SMT-COMP {year}"
    stats = make_stats_dict(name)
    # Date is the day the PDPAR (pre. SMT) workshop happened.
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link)
        VALUES(?,?,?);
        """,
        (name, date, f"https://smtcomp.sourceforge.net/{year}/"),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding SMT-COMP {year} results")
    for htmlFile in Path(f"./early-SMT-COMP/{year}").glob("results-*-*.shtml"):
        soup = BeautifulSoup(open(htmlFile), "html.parser")
        header = re.match(old_header_regex, soup.find("h1").text)
        solver = header[1]
        logic = header[2]

        # Legacy logic, no longer used.
        if logic == "QF_UFBV32":
            logic = "QF_BV"

        table = soup.find("table", "score")
        if not table:
            table = soup.find("table", "score2")
        for c in table.find_all("tr"):
            tds = list(c.find_all("td"))
            # the header
            if len(tds) == 0:
                continue
            assert len(tds) == 4
            correct = tds[3].text
            if not correct == "yes":
                answer = "unknown"
            else:
                answer = tds[1].text

            try:
                time = float(tds[2].text)
            except ValueError:
                time = float("NaN")

            benchmarkFields = tds[0].text.split("/")
            benchmarkSet = benchmarkFields[0]
            benchmarkName = "/".join(benchmarkFields[1:]) + "2"

            subbenchmarkId = benchmarks.guess_subbenchmark_id(
                connection, logic, benchmarkSet, benchmarkName, stats
            )
            if not subbenchmarkId:
                print(
                    f"WARNING: Benchmark {benchmarkName} of SMT-COMP {year} not found ({logic}, {benchmarkSet})"
                )
                subbenchmarkId = 1
                # continue

            write_result(
                connection,
                evaluationId,
                solver,
                subbenchmarkId,
                answer,
                None,
                time,
            )
    return stats


# CSV format used for smt eval 2013
def add_smt_eval_2013(connection, csvDataFile):
    name = f"SMT Evaluation 2013"
    stats = make_stats_dict(name)
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link)
        VALUES(?,?,?);
        """,
        (name, "2013-07-02", f"https://smtcomp.sourceforge.net/2013/"),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()

    # Maps benchmark ids in the csv to ids in the database.
    # This is necessary for the "FillInRun"s that don't contain full filenames.
    # TODO: this could be an optimization for the other formats
    # "FillInRun" are 593 the pairs originally omitted due to a "bug" (see paper).
    benchmarkIdMapping = {}

    print(f"Adding SMT Evaluation 2013 results")
    with open(csvDataFile, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",")
        for row in reader:
            solver = f"{row[' solver']} {row['configuration']}"
            # This is wallclock time. It tops out at 1500s, which is the
            # wallclock time limit specified n the paper.
            time = row["time(s)"]
            if time == "-":
                time = float("NaN")
            else:
                time = float(time)

            status = row["result"]
            status = benchmark_status(status)
            benchmarkField = row[" benchmark"].split("/")
            if row["benchmark id"] in benchmarkIdMapping:
                subbenchmarkId = benchmarkIdMapping[row["benchmark id"]]
            else:
                if benchmarkField[0] == "FillInRun":
                    print(
                        f"WARNING: Fill in run {row[' benchmark']} of SMT Evaluation 2013 not found"
                    )
                    continue

                logic = benchmarkField[1]
                benchmarkSet = benchmarkField[2]
                benchmarkName = "/".join(benchmarkField[3:])

                subbenchmarkId = benchmarks.guess_subbenchmark_id(
                    connection, logic, benchmarkSet, benchmarkName, stats
                )
                if not subbenchmarkId:
                    print(
                        f"WARNING: Benchmark {benchmarkName} of SMT Evaluation 2013 not found"
                    )
                    continue
                benchmarkIdMapping[row["benchmark id"]] = subbenchmarkId

            write_result(
                connection,
                evaluationId,
                solver,
                subbenchmarkId,
                status,
                None,
                time,
            )
    connection.commit()
    return stats


# CSV format used 2014
def add_smt_comp_2014(connection, compressedCsvFilename):
    name = f"SMT-COMP 2014"
    stats = make_stats_dict(name)
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
                status = benchmark_status(status, row[11])
                benchmarkField = row[1].split("/")
                logic = benchmarkField[0]
                benchmarkSet = benchmarkField[1]
                benchmarkName = "/".join(benchmarkField[2:])
                subbenchmarkId = benchmarks.guess_subbenchmark_id(
                    connection, logic, benchmarkSet, benchmarkName, stats
                )
                if not subbenchmarkId:
                    print(
                        f"WARNING: Benchmark {benchmarkName} of SMT-COMP 2014 not found"
                    )
                    continue
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
    return stats


# CSV format used 2015-2017
def add_smt_comp_oldstyle(connection, compressedCsvFilename, year, date):
    name = f"SMT-COMP {year}"
    stats = make_stats_dict(name)
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
                status = benchmark_status(status, row["expected"])
                benchmarkField = row["benchmark"].split("/")
                logic = benchmarkField[0]
                benchmarkSet = benchmarkField[1]
                benchmarkName = "/".join(benchmarkField[2:])
                subbenchmarkId = benchmarks.guess_subbenchmark_id(
                    connection, logic, benchmarkSet, benchmarkName, stats
                )
                if not subbenchmarkId:
                    print(
                        f"WARNING: Benchmark {benchmarkName} of SMT-COMP {year} not found ({logic}, {benchmarkSet})"
                    )
                    continue
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
    return stats


def add_smt_comp_generic(connection, folder, year, date):
    name = f"SMT-COMP {year}"
    stats = make_stats_dict(name)
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
                familyField = fileField["family"][0]
                fullbench = "/".join(fileField["family"][1:] + [fileField["name"]])

                subbenchmarkId = benchmarks.guess_subbenchmark_id(
                    connection, fileField["logic"], familyField, fullbench, stats
                )
                if not subbenchmarkId:
                    print(
                        f"WARNING: Benchmark {fullbench} of SMT-COMP {year} not found ({fileField['logic']}, {familyField})"
                    )
                    continue
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


def add_smt_comps(connection, smtcompwwwfolder, smtcompfolder, smtevalcsv):
    stats = []
    s = add_smt_comp_early(connection, "2005", "2005-07-12")
    stats.append(s)
    s = add_smt_comp_early(connection, "2006", "2006-08-21")
    stats.append(s)
    s = add_smt_eval_2013(connection, smtevalcsv)
    stats.append(s)
    path2014 = smtcompfolder / "2014/csv/combined.tar.xz"
    s = add_smt_comp_2014(connection, path2014)
    stats.append(s)
    path2015 = smtcompfolder / "2015/csv/Main_Track.tar.xz"
    s = add_smt_comp_oldstyle(connection, path2015, "2015", "2015-07-02")
    stats.append(s)
    path2016 = smtcompfolder / "2016/csv/Main_Track.tar.xz"
    s = add_smt_comp_oldstyle(connection, path2016, "2016", "2016-07-02")
    stats.append(s)
    path2017 = smtcompfolder / "2017/csv/Main_Track.tar.xz"
    s = add_smt_comp_oldstyle(connection, path2017, "2017", "2017-07-23")
    stats.append(s)
    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2018", "2018-07-14")
    stats.append(s)
    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2019", "2019-07-07")
    stats.append(s)
    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2020", "2020-07-06")
    stats.append(s)
    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2021", "2021-07-18")
    stats.append(s)
    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2022", "2022-08-10")
    stats.append(s)
    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2023", "2023-07-06")
    stats.append(s)
    for stat in stats:
        print_stats_dict(stat)


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
    return stats


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
