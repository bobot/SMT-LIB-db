import re
import datetime
import subprocess
import mmap
import json


def setup_benchmarks(connection):
    connection.execute(
        """CREATE TABLE Benchmarks(
        id INTEGER PRIMARY KEY,
        filename TEXT NOT NULL,
        benchmarkSet INT,
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
        subbenchmarkCount INT NOT NULL,
        FOREIGN KEY(benchmarkSet) REFERENCES Sets(id)
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
        """CREATE TABLE Sets(
        id INTEGER PRIMARY KEY,
        name NVARCHAR(100) NOT NULL,
        folderName TEXT NOT NULL,
        date DATE,
        benchmarkCount INT NOT NULL,
        UNIQUE(folderName)
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


def parse_set(name):
    """
    Parses the filename component that reperesents a set and a date.
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
    Calculates the number of benchmarks in each set.
    """
    connection.execute(
        "UPDATE Sets SET benchmarkCount = (SELECT COUNT(id) FROM Benchmarks WHERE Benchmarks.benchmarkSet=Sets.id);"
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


def add_benchmark(connection, benchmark):
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
    setFolder = parts[2]
    date, setName = parse_set(setFolder)
    fileName = "/".join(parts[3:])

    setId = None
    # short circuit
    for row in connection.execute(
        "SELECT id FROM Sets WHERE folderName=?", (setFolder,)
    ):
        setId = row[0]

    if not setId:
        connection.execute(
            """
            INSERT OR IGNORE INTO Sets(name, foldername, date, benchmarkCount)
            VALUES(?,?,?,?);
            """,
            (setName, setFolder, date, 0),
        )
        connection.commit()
        for row in connection.execute(
            "SELECT id FROM Sets WHERE folderName=?", (setFolder,)
        ):
            setId = row[0]

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

    licenseId = get_license_id(connection, benchmarkObj["license"])

    generatedOn = None
    try:
        generatedOn = datetime.datetime.fromisoformat(benchmarkObj["generatedOn"])
    except (ValueError, TypeError):
        pass

    # TODO: parse target solver
    connection.execute(
        """
        INSERT INTO Benchmarks(filename,
                               benchmarkSet,
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
                               subbenchmarkCount)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?);
        """,
        (
            fileName,
            setId,
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
            benchmarkObj["subbenchmarkCount"],
        ),
    )
    connection.commit()
    benchmarkId = None
    for row in connection.execute(
        "SELECT id FROM Benchmarks WHERE fileName=? AND benchmarkSet=? AND logic=?",
        (fileName, setId, benchmarkObj["logic"]),
    ):
        benchmarkId = row[0]

    for idx in range(len(subbenchmarkObjs)):
        subbenchmarkObj = subbenchmarkObjs[idx]
        connection.execute(
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
        connection.commit()
        subbenchmarkId = None
        for row in connection.execute(
            "SELECT id FROM Subbenchmarks WHERE benchmark=? AND number=?",
            (benchmarkId, idx + 1),
        ):
            subbenchmarkId = row[0]
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


def get_benchmark_id(
    connection, fullFilename, isIncremental=None, logic=None, setFoldername=None
):
    """
    Gets the id of a benchmark from a benchmark filepath.  If all optional arguments are None then the
    path must have the form "[non-]incremental/LOGIC/SETFOLDERNAME/BENCHMARKPATH"

    If an optional argument is not None, the corresponding component must be omitted from the path.
    Furthermore, if any of those arguments is not None, the preceding arguments must not be None.
    Hence, if `logic="QF_UF"` then `isIncremental` must be set and `fullFilename` is of the form
    "SETFOLDERNAME/BENCHMARKPATH".
    """
    if isIncremental == None:
        slashIdx = fullFilename.find("/")
        if fullFilename[:slashIdx] == "non-incremental":
            isIncremental = False
        else:
            isIncremental = True
        fullFilename = fullFilename[slashIdx + 1 :]

    if not logic:
        slashIdx = fullFilename.find("/")
        logic = fullFilename[:slashIdx]
        fullFilename = fullFilename[slashIdx + 1 :]

    if not setFoldername:
        slashIdx = fullFilename.find("/")
        setFoldername = fullFilename[:slashIdx]
        fullFilename = fullFilename[slashIdx + 1 :]

    benchmarkId = None
    for row in connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Sets ON Sets.Id = Benchmarks.benchmarkSet
            WHERE filename=? AND logic=? AND Sets.folderName=?
        """,
        (fullFilename, logic, setFoldername),
    ):
        benchmarkId = row[0]
    return benchmarkId
