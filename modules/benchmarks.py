import re
import datetime
import subprocess
import mmap


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


def calculate_benchmark_count(connection):
    """
    Calculates the number of benchmarks in each set.
    """
    connection.execute(
        "UPDATE Sets SET benchmarkCount = (SELECT COUNT(id) FROM Benchmarks WHERE Benchmarks.benchmarkSet=Sets.id);"
    )
    connection.commit()


def get_license_id(connection, license):
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
            "Benchmark path does not contain at most one 'incremental' or 'non-incremental'."
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

    size = benchmark.stat().st_size

    cc = subprocess.run(
        f"gzip -c {benchmark} | wc -c",
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    )
    compressedSize = int(cc.stdout)

    with open(benchmark, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)

        licenseRegex = re.compile(b'\(\s*set-info\s*:license\s*"([^"]+)"\s*\)')
        embeddedLicenseRegex = re.compile(b"\(\s*set-info\s*:license\s*\|")
        categoryRegex = re.compile(b'\(\s*set-info\s*:category\s*"([a-zA-Z]+)"\s*\)')
        checksatRegex = re.compile(b"\(\s*check-sat\s*\)")

        matchResult = re.search(licenseRegex, mm)
        if not matchResult:
            matchResult = re.search(embeddedLicenseRegex, mm)
            if not matchResult:
                license = None
            license = "CMU SoSy Lab"
        else:
            license = matchResult.group(1).decode("utf-8")

        licenseId = get_license_id(connection, license)

        matchResult = re.search(categoryRegex, mm)
        if not matchResult:
            raise Exception("Could not match category.")
        category = matchResult.group(1).decode("utf-8")

        numChecksats = len(re.findall(checksatRegex, mm))
        if numChecksats == 0:
            raise Exception("Could not find any check-sat commands.")

        mm.close()

    # The following are in the metadata header and might be tricky to parse:
    # generatedOn
    # generatedBy
    # description
    # generator
    # application

    connection.execute(
        """
        INSERT INTO Benchmarks(filename,
                               benchmarkSet,
                               logic,
                               isIncremental,
                               size,
                               compressedSize,
                               license,
                               category,
                               subbenchmarkCount)
        VALUES(?,?,?,?,?,?,?,?,?);
        """,
        (
            fileName,
            setId,
            logic,
            isIncremental,
            size,
            compressedSize,
            licenseId,
            category,
            numChecksats,
        ),
    )
    connection.commit()


def get_benchmark_id(connection, fullFilename, isIncremental = None, logic = None, setFoldername = None):
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
        fullFilename = fullFilename[slashIdx+1:]

    if not logic:
        slashIdx = fullFilename.find("/")
        logic = fullFilename[:slashIdx]
        fullFilename = fullFilename[slashIdx+1:]
    
    if not setFoldername:
        slashIdx = fullFilename.find("/")
        setFoldername = fullFilename[:slashIdx]
        fullFilename = fullFilename[slashIdx+1:]

    benchmarkId = None
    for row in connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Sets ON Sets.Id = Benchmarks.benchmarkSet
            WHERE filename=? AND logic=? AND Sets.folderName=?
        """, (fullFilename, logic, setFoldername)
    ):
        benchmarkId = row[0]
    return benchmarkId

