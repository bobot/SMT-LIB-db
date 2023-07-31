import tempfile
import subprocess
import csv
from modules import benchmarks

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
        subbenchmark INT,
        solverVariant INT,
        cpuTime REAL,
        wallclockTime REAL,
        status TEXT,
        FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
        FOREIGN KEY(solverVariant) REFERENCES SolverVaraiants(id)
        );"""
    )

def add_smt_comp_2022(connection, folder):
    connection.execute(
        """
        INSERT INTO Evaluations(name, date, link)
        VALUES(?,?,?);
        """,
        ("SMT-COMP 2022", "2022-08-10", "https://smt-comp.github.io/2022/"),
    )
    connection.commit()
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            f"tar xvf {folder}/2022/results/raw-results.tar.xz -C {tmpdir}",
            shell=True,
        )
        with open(f"{tmpdir}/raw-results-sq.csv", newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                # remove the 'track_single_query/' from the start
                fullbench = row['benchmark'][19:]
                try:
                    benchmarkId = benchmarks.get_benchmark_id(connection, fullbench, isIncremental=False)
                except NameError:
                    print(f"WARNING: Benchmark {fullbench} of SMT-COMP 2022 not found")
                    continue

                solver = row['solver']
                solverVariantId = None
                for row in connection.execute(
                    """
                    SELECT Id FROM SolverVariants WHERE fullName=?
                    """, (solver, )
                ):
                    solverVariantId = row[0]
                if not solverVariantId:
                    # We do not care about the results from solvers that are not on the list.
                    continue

                try:
                    cpuTime = float(row['cpu time'])
                except ValueError:
                    cpuTime = None
                try:
                    wallclockTime = float(row['wallclock time'])
                except ValueError:
                    wallclockTime = None
                
                if row['result'] == "starexec-unknown":
                    status = "unknown"
                elif row['result'] != row['expected']:
                    status = "unknown"
                else:
                    status = row['result']
 
                connection.execute(
                    """
                    INSERT INTO Results(subbenchmark, solverVariant, cpuTime, wallclockTime, status)
                    VALUES(?,?,?,?);
                    """,
                    (benchmarkId, solverVariantId, cpuTime, wallclockTime, status),
                )
    connection.commit()

def add_smt_comps(connection, folder):
    add_smt_comp_2022(connection, folder)
