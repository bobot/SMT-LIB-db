import re
import datetime
import subprocess
import mmap
import json
import sqlite3

import modules.solvers


def setup_benchmarks(connection):
    connection.execute(
        """CREATE TABLE Benchmarks(
        id INTEGER PRIMARY KEY,
        filename TEXT NOT NULL,
        family INT,
        logic NVARCHAR(100) NOT NULL,
        isIncremental BOOL,
        size INT,
        compressedSize INT,
        license INT,
        generatedOn DATETTIME,
        generatedBy TEXT,
        generator TEXT,
        application TEXT,
        description TEXT,
        category TEXT,
        passesDolmen BOOL,
        passesDolmenStrict BOOL,
        subbenchmarkCount INT NOT NULL,
        FOREIGN KEY(family) REFERENCES Families(id)
        FOREIGN KEY(license) REFERENCES Licenses(id)
    );"""
    )

    connection.execute(
        """CREATE TABLE Subbenchmarks(
        id INTEGER PRIMARY KEY,
        benchmark INT,
        number INT,
        normalizedSize INT,
        compressedSize INT,
        assertsCount INT,
        declareFunCount INT,
        declareConstCount INT,
        declareSortCount INT,
        defineFunCount INT,
        defineFunRecCount INT,
        constantFunCount INT,
        defineSortCount INT,
        declareDatatypeCount INT,
        maxTermDepth INT,
        status TEXT,

        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
    );"""
    )

    connection.execute(
        """CREATE TABLE Families(
        id INTEGER PRIMARY KEY,
        name NVARCHAR(100) NOT NULL,
        folderName TEXT NOT NULL,
        date DATE,
        benchmarkCount INT NOT NULL,
        UNIQUE(folderName)
    );"""
    )

    connection.execute(
        """CREATE TABLE TargetSolvers(
        id INTEGER PRIMARY KEY,
        benchmark INTEGER NOT NULL,
        solverVariant TEXT NOT NULL,
        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id),
        FOREIGN KEY(solverVariant) REFERENCES SolverVariants(id)
    );"""
    )

    # id is declared INT to force it to not be an alias to rowid
    connection.execute(
        """CREATE TABLE Symbols(
        id INT PRIMARY KEY,
        name TEXT);"""
    )

    connection.execute(
        """CREATE TABLE SymbolsCounts(
        symbol INT,
        subbenchmark INT,
        count INT NOT NULL,
        FOREIGN KEY(symbol) REFERENCES Symbols(id)
        FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    );"""
    )

    with open("./klhm/src/smtlib-symbols", "r") as symbolFile:
        count = 1
        for line in symbolFile:
            if line[0] == ";":
                continue
            connection.execute(
                """
                INSERT OR IGNORE INTO Symbols(id,name)
                VALUES(?,?);
                """,
                (
                    count,
                    line.strip(),
                ),
            )
            count = count + 1
        connection.commit()


def parse_family(name):
    """
    Parses the filename component that reperesents a family and a date.
    Possible cases are:
        yyyymmdd-NAME
        yyyy-NAME
        NAME
    """
    match = re.match(r"(\d\d\d\d)(\d\d)(\d\d)-(.*)", name)
    if match:
        try:
            return datetime.date(int(match[1]), int(match[2]), int(match[3])), match[4]
        except ValueError:
            return None, name
    match = re.match(r"(\d\d\d\d)-(.*)", name)
    if match:
        return datetime.date(int(match[1]), 1, 1), match[2]
    return None, name


def calculate_benchmark_count(connection):
    """
    Calculates the number of benchmarks in each family.
    """
    connection.execute(
        "UPDATE Families SET benchmarkCount = (SELECT COUNT(id) FROM Benchmarks WHERE Benchmarks.family=Families.id);"
    )
    connection.commit()


def get_license_id(connection, license):
    if license == None:
        license = "https://creativecommons.org/licenses/by/4.0/"
    license = license.replace("http:", "https:")
    for row in connection.execute(
        "SELECT id FROM Licenses WHERE name=? OR link=? OR spdxIdentifier=?",
        (license, license, license),
    ):
        return row[0]

    raise Exception("Could not determine license.")


def add_benchmark(dbFile, benchmark, dolmenPath):
    """
    Populates the database with the filenames of the benchmarks.
    Does not populate metadata fields or anything else.
    """
    print(f"Adding {benchmark}")
    parts = benchmark.parts

    incrementalCount = parts.count("incremental")
    nonincrementalCount = parts.count("non-incremental")
    count = incrementalCount + nonincrementalCount

    if count != 1:
        raise Exception(
            f"Benchmark path {benchmark} does not contain at most one 'incremental' or 'non-incremental'."
        )
    if incrementalCount > 0:
        parts = parts[parts.index("incremental") :]
        isIncremental = True
    else:
        parts = parts[parts.index("non-incremental") :]
        isIncremental = False

    logic = parts[1]
    familyFolder = parts[2]
    date, familyName = parse_family(familyFolder)
    fileName = "/".join(parts[3:])

    klhm = subprocess.run(
        f"./klhm/zig-out/bin/klhm {benchmark}",
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    klhmData = json.loads(klhm.stdout)
    subbenchmarkObjs = klhmData[0:-1]
    benchmarkObj = klhmData[-1]

    generatedOn = None
    try:
        generatedOn = datetime.datetime.fromisoformat(benchmarkObj["generatedOn"])
    except (ValueError, TypeError):
        pass

    dolmen = subprocess.call(
        f"{dolmenPath} --check-flow=true --strict=false {benchmark}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if dolmen == 2 or dolmen == 125:
        dolmen = None
    elif dolmen == 0:
        dolmen = True
    else:
        dolmen = False

    dolmenStrict = subprocess.call(
        f"{dolmenPath} --check-flow=true --strict=true {benchmark}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if dolmenStrict == 2 or dolmenStrict == 125:
        dolmenStrict = None
    elif dolmenStrict == 0:
        dolmenStrict = True
    else:
        dolmenStrict = False

    if dolmenStrict == None or dolmen == None:
        print("Have none!")

    connection = sqlite3.connect(dbFile, timeout=30.0)
    # This should not be necessary, because WAL mode is persistent, but we
    # add it here to be sure.
    connection.execute("PRAGMA journal_mode=wal")
    # Disable to-disc syncing, might corrupt database on system crash, but since
    # this script is used to build the database upfront, this is mostly harmless.
    connection.execute("PRAGMA synchronous = OFF")

    cursor = connection.cursor()
    familyId = None
    # short circuit
    for row in cursor.execute(
        "SELECT id FROM Families WHERE folderName=?", (familyFolder,)
    ):
        familyId = row[0]

    if not familyId:
        cursor.execute(
            """
            INSERT OR IGNORE INTO Families(name, foldername, date, benchmarkCount)
            VALUES(?,?,?,?);
            """,
            (familyName, familyFolder, date, 0),
        )
        familyId = cursor.lastrowid

    licenseId = get_license_id(connection, benchmarkObj["license"])

    cursor.execute(
        """
        INSERT INTO Benchmarks(filename,
                               family,
                               logic,
                               isIncremental,
                               size,
                               compressedSize,
                               license,
                               generatedOn,
                               generatedBy,
                               generator,
                               application,
                               description,
                               category,
                               passesDolmen,
                               passesDolmenStrict,
                               subbenchmarkCount)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
        """,
        (
            fileName,
            familyId,
            benchmarkObj["logic"],
            benchmarkObj["isIncremental"],
            benchmarkObj["size"],
            benchmarkObj["compressedSize"],
            licenseId,
            generatedOn,
            benchmarkObj["generatedBy"],
            benchmarkObj["generator"],
            benchmarkObj["application"],
            benchmarkObj["description"],
            benchmarkObj["category"],
            dolmen,
            dolmenStrict,
            benchmarkObj["subbenchmarkCount"],
        ),
    )
    benchmarkId = cursor.lastrowid

    if benchmarkObj["targetSolver"]:
        targetSolvers = benchmarkObj["targetSolver"]
        # Hacks for the two space sperated cases
        if targetSolvers == "Boolector Z3 STP":
            targetSolvers = ["Boolector", "Z3", "STP"]
        elif targetSolvers == "CVC4 Mathsat SPASS-IQ YICES Z3":
            targetSolvers = ["CVC4", "Mathsat", "SPASS-IQ", "YICES", "Z3"]
        else:
            # Split on '/', " or ", and ","
            targetSolvers = targetSolvers.replace("/", ",")
            targetSolvers = targetSolvers.replace(" or ", ",")
            targetSolvers = targetSolvers.split(",")
            targetSolvers = map(lambda x: x.strip(), targetSolvers)
        for targetSolver in targetSolvers:
            try:
                id = modules.solvers.global_variant_lookup[targetSolver]
                cursor.execute(
                    """
                       INSERT INTO TargetSolvers(benchmark,
                                                 solverVariant)
                       VALUES(?,?);
                       """,
                    (benchmarkId, id),
                )
            except KeyError:
                print(f"WARNING: Target solver '{targetSolver}' not known.")
        connection.commit()

    for idx in range(len(subbenchmarkObjs)):
        subbenchmarkObj = subbenchmarkObjs[idx]
        cursor.execute(
            """
            INSERT INTO Subbenchmarks(benchmark,
                                      number,
                                      normalizedSize,
                                      compressedSize,
                                      assertsCount,
                                      declareFunCount,
                                      declareConstCount,
                                      declareSortCount,
                                      defineFunCount,
                                      defineFunRecCount,
                                      constantFunCount,
                                      defineSortCount,
                                      declareDatatypeCount,
                                      maxTermDepth,
                                      status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
            """,
            (
                benchmarkId,
                idx + 1,
                subbenchmarkObj["normalizedSize"],
                subbenchmarkObj["compressedSize"],
                subbenchmarkObj["assertsCount"],
                subbenchmarkObj["declareFunCount"],
                subbenchmarkObj["declareConstCount"],
                subbenchmarkObj["declareSortCount"],
                subbenchmarkObj["defineFunCount"],
                subbenchmarkObj["defineFunRecCount"],
                subbenchmarkObj["constantFunCount"],
                subbenchmarkObj["defineSortCount"],
                subbenchmarkObj["declareDatatypeCount"],
                subbenchmarkObj["maxTermDepth"],
                subbenchmarkObj["status"],
            ),
        )
        subbenchmarkId = cursor.lastrowid
        symbolCounts = subbenchmarkObj["symbolFrequency"]
        for symbolIdx in range(len(symbolCounts)):
            if symbolCounts[symbolIdx] > 0:
                connection.execute(
                    """
                    INSERT INTO SymbolsCounts(symbol,
                                              subbenchmark,
                                              count)
                    VALUES(?,?,?);
                    """,
                    (symbolIdx + 1, subbenchmarkId, symbolCounts[symbolIdx]),
                )
    connection.commit()
    connection.close()


def guess_benchmark_id(
    connection, isIncremental, logic, familyFoldername, fullFilename
):
    """
    Guess the id of a benchmark.  The guessing is necessary, because
    benchmarks might have moved paths between competitions.  The function
    first tests whether there one unique benchmark with a subset of the
    parameters.  First, it uses only `fullFilename`, then additionally
    `familyFoldername`, then additionally `isIncremental`
    then `logic`.
    The `isIncremental` field is always enforced.
    If any of these thests returns one unique benchmark, its id is
    returned.  If any returns non, or if all return more than one
    benchmark, None is returned.

    The priorities are informed by how often a component of the path change.
    E.g., the logic changed in the past for some benchmarks, because they were
    missclassified.
    """

    _, benchmarkFamily = parse_family(familyFoldername)

    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks WHERE filename=?
        """,
        (fullFilename,),
    )
    l = r.fetchall()
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]
    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Families ON Families.Id = Benchmarks.family
            WHERE filename=? AND Families.folderName=?
        """,
        (fullFilename, familyFoldername),
    )
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]

    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Families ON Families.Id = Benchmarks.family
            WHERE filename=? AND isIncremental=? AND Families.folderName=?
        """,
        (fullFilename, isIncremental, familyFoldername),
    )
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]
    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Families ON Families.Id = Benchmarks.family
            WHERE filename=? AND logic=? AND isIncremental=? AND Families.folderName=?
        """,
        (fullFilename, isIncremental, logic, familyFoldername),
    )
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]
    return None


def guess_subbenchmark_id(connection, logic, familyFoldername, fullFilename):
    """
    Same as guess_benchmark_id, but returns the id of the sole subbenchmark
    of a non-incremental benchmark.
    """
    benchmarkId = guess_benchmark_id(
        connection, False, logic, familyFoldername, fullFilename
    )
    if not benchmarkId:
        return None
    for r in connection.execute(
        """
        SELECT Id FROM Subbenchmarks WHERE benchmark=?
        """,
        (benchmarkId,),
    ):
        return r[0]
    return None
