import re
import datetime


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
        normalizedSize INT,
        compressedSize INT,
        defineFunCount INT,
        maxTermDepth INT,
        numSexps INT,
        numPatterns INT,
        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
    );"""
    )

    connection.execute(
        """CREATE TABLE Sets(
        id INTEGER PRIMARY KEY,
        name NVARCHAR(100) NOT NULL,
        folderName TEXT NOT NULL,
        date DATE,
        benchmarkCount INT NOT NULL
    );"""
    )


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


def populate_files(connection, folder):
    """
    Populates the database with the filenames of the benchmarks.
    Does not populate metadata fields or anything else.
    """
    count = 0
    for benchmarkAbs in folder.glob("*/*/*/**/*.smt2"):
        count = count + 1
        benchmark = benchmarkAbs.relative_to(folder)
        print(f"Inserting {count:>8} {benchmark}")

        parts = benchmark.parts
        isIncremental = False
        if parts[0] == "incremental":
            isIncremental = True
        logic = parts[1]
        setFolder = parts[2]
        date, setName = parse_set(setFolder)
        fileName = "/".join(parts[3:])

        setId = None
        for row in connection.execute(
            "SELECT id FROM Sets WHERE folderName=?", (setFolder,)
        ):
            setId = row[0]
        if not setId:
            cursor = connection.execute(
                """
                INSERT INTO Sets(name, foldername, date, benchmarkCount)
                VALUES(?,?,?,?);
                """,
                (setName, setFolder, date, 0),
            )
            setId = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO Benchmarks(filename, benchmarkSet, logic, isIncremental, subbenchmarkCount)
            VALUES(?,?,?,?,?);
            """,
            (fileName, setId, logic, isIncremental, 0),
        )
        connection.commit()
    connection.execute(
        "UPDATE Sets SET benchmarkCount = (SELECT COUNT(id) FROM Benchmarks WHERE Benchmarks.benchmarkSet=Sets.id);"
    )
    connection.commit()
