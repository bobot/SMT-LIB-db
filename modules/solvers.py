def setup_solvers(connection):
    create_tables(connection)
    populate_tables(connection)
    connection.commit()


def create_tables(connection):
    connection.execute(
        """CREATE TABLE Solvers(
        id INTEGER PRIMARY KEY,
        name TEXT,
        link TEXT);"""
    )

    # To distinguishe versions etc.
    connection.execute(
        """CREATE TABLE SolverVariants(
        id INTEGER PRIMARY KEY,
        fullName TEXT,
        solver INT,
        evaluation INT,
        FOREIGN KEY(solver) REFERENCES Solvers(id)
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        );"""
    )


# Canonical names of SMT solvers
known_solvers = [
    ("Bitwuzla", "https://bitwuzla.github.io/"),
    ("COLIBRI", "https://colibri.frama-c.com/"),
    ("CVC4", "https://cvc4.github.io/"),
    ("cvc5", "https://cvc5.github.io/"),
    ("MathSAT", "https://mathsat.fbk.eu/"),
    ("NRA-LS", "https://github.com/minghao-liu/NRA-LS"),
    ("OpenSMT", "https://verify.inf.usi.ch/opensmt"),
    ("OSTRICH", "https://github.com/uuverifiers/ostrich"),
    ("Par4", ""),
    ("Q3B", "https://github.com/martinjonas/Q3B/"),
    ("Q3B-pBNN", "https://www.fi.muni.cz/~xpavlik5/Q3B-pBDD/"),
    ("SMTInterpol", "https://ultimate.informatik.uni-freiburg.de/smtinterpol"),
    ("SMT-RAT", "https://smtrat.github.io/"),
    ("solmt", "https://github.com/ethereum/solidity/"),
    ("STP", "https://stp.github.io/"),
    (
        "UltimateEliminator+MathSAT",
        "https://ultimate.informatik.uni-freiburg.de/eliminator/",
    ),
    ("Vampire", "https://vprover.github.io/"),
    ("veriT", "https://verit-solver.org/"),
    ("veriT+raSAT+Redlog", "https://verit-solver.org/"),
    ("Yices2", "https://yices.csl.sri.com/"),
    ("Yices-ismt", "https://github.com/MRVAPOR/Yices-ismt"),
    ("YicesQS", "https://github.com/disteph/yicesQS"),
    ("Z3++", "https://z3-plus-plus.github.io/"),
    ("Z3", "https://github.com/Z3Prover/z3"),
    ("Z3++BV", "https://z3-plus-plus.github.io/"),
    ("Z3string", "https://z3string.github.io/"),
    ("CVC3", "https://cs.nyu.edu/acsys/cvc3/"),
    ("ABC", "https://dl.acm.org/doi/10.1007/978-3-642-14295-6_5"),
    ("Norn", "https://user.it.uu.se/~jarst116/norn/"),
    ("S3P", "https://trinhmt.github.io/home/S3/"),
    ("Trau", "https://github.com/diepbp/Trau"),
    ("Alt-Ergo", "https://alt-ergo.ocamlpro.com/"),
    ("Barcelogic", "https://www.cs.upc.edu/~oliveras/bclt-main.html"),
    ("Boolector", "https://boolector.github.io/"),
    ("Yices", "https://yices.csl.sri.com/old/yices1-documentation.html"),
    ("CryptoMiniSat", "https://www.msoos.org/cryptominisat5/"),
    ("Z3-Trau", "https://github.com/diepbp/z3-trau"),
    ("Kaluza", "https://doi.org/10.1109/SP.2010.38"),
    ("SLENT", "https://github.com/NTU-ALComLab/SLENT"),
    ("Woorpje", "https://www.informatik.uni-kiel.de/~mku/woorpje/"),
    ("Kepler_22", "https://doi.org/10.1007/978-3-030-02768-1_19"),
    (
        "SPASS-IQ",
        "https://www.mpi-inf.mpg.de/de/departments/automation-of-logic/software/spass-workbench/spass-iq",
    ),
    ("iProver", "https://gitlab.com/korovin/iprover"),
    ("NRA-LS", "https://github.com/minghao-liu/NRA-LS"),
    ("UltimateIntBlastingWrapper+SMTInterpol", "https://ultimate-pa.org/"),
    ("Z3alpha", "https://github.com/JohnLyu2/z3alpha"),
    ("Z3-Noodler", "https://github.com/VeriFIT/z3-noodler"),
    ("Z3-Owl", "https://z3-owl.github.io/"),
    ("Yaga", "https://d3s.mff.cuni.cz/software/yaga/"),
    ("mc2", "https://github.com/c-cube/mc2"),
    ("AProVE", "https://aprove.informatik.rwth-aachen.de/"),
    ("YicesLS", "https://smt-comp.github.io/2021/system-descriptions/YicesLS.pdf"),
]

solver_count = 1
solver_table = []

# Lists solver variants that are not in scope of a comptetition.
# E.g., those used as "Target Solver"
global_solver_variants = {
    "Bitwuzla": ["Bitwuzla-wrapped", "bitwuzla", "Bitwuzla (with SymFPU)"],
    "CVC4": ["CVC4 (with SymFPU)"],
    "cvc5": ["CVC5"],
    "MathSAT": ["Mathsat5", "MathSAT5", "Mathsat"],
    "OSTRICH": ["Ostrich"],
    "Vampire": ["vampire"],
    "Yices2": ["yices2", "Yices 2"],
    "Z3": ["z3", "z3;"],
    "Z3string": ["Z3-str2", "Z3str3", "Z3str4", "Z3str3RE"],
    "Woorpje": ["WOORPJE"],
    "Yices": ["YICES"],
}

# TODO: is it possible that solvers occur in two names that count (i.e. not
#       just a non-fixed and a fixed version.
evaluation_solver_variants = {
    # TODO: what is "master-2018-06-10-b19c840-competition-default"
    "SMT-COMP 2021": [
        ("AProVE", "AProVE NIA 2014"),
        ("Bitwuzla", "Bitwuzla-fixed"),
        ("COLIBRI", "COLIBRI_21_06_23"),
        ("cvc5", "cvc5-fixed"),
        ("iProver", "iProver-v3.5-final-fix2"),
        ("MathSAT", "mathsat-5.6.6"),
        ("mc2", "mc2 2021-06-07"),
        ("OpenSMT", "OpenSMT-fixed"),
        ("Par4", "Par4-wrapped-sq"),
        ("SMTInterpol", "smtinterpol-2.5-823-g881e8631"),
        ("SMT-RAT", "smtrat-SMTCOMP"),
        ("STP", "STP 2021.0"),
        ("UltimateEliminator+MathSAT", "UltimateEliminator+MathSAT-5.6.6"),
        ("Vampire", "vampire_smt_4.6-fixed"),
        ("veriT+raSAT+Redlog", "veriT+raSAT+Redlog"),
        ("veriT", "veriT"),
        ("Yices2", "Yices 2.6.2 bug fix"),
        ("YicesLS", "YicesLS_0611_1448"),
        ("YicesQS", "yices-QS-2021-06-13under10"),
        ("Z3string", "Z3str4 SMTCOMP 2021 v1.1"),
        ("Z3", "z3-4.8.11"),
    ],
    "SMT-COMP 2022": [
        ("Bitwuzla", "Bitwuzla-fixed"),
        ("COLIBRI", "COLIBRI 22_06_18"),
        ("CVC4", "CVC4-sq-final"),
        ("cvc5", "cvc5-default-2022-07-02-b15e116-wrapped"),
        ("MathSAT", "MathSAT-5.6.8"),
        ("NRA-LS", "NRA-LS-FINAL"),
        ("OpenSMT", "opensmt fixed"),
        ("OSTRICH", "OSTRICH 1.2"),
        ("Par4", "Par4-wrapped-sq"),
        ("Q3B", "Q3B"),
        ("Q3B-pBNN", "Q3B-pBDD SMT-COMP 2022 final"),
        ("SMTInterpol", "smtinterpol-fixed-2.5-1148-gf2d8e6b0"),
        ("SMT-RAT", "SMT-RAT-MCSAT"),
        ("STP", "STP 2022.4"),
        ("UltimateEliminator+MathSAT", "UltimateEliminator+MathSAT-5.6.7-wrapped"),
        ("Vampire", "vampire_4.7_smt_fix-wrapped"),
        ("veriT+raSAT+Redlog", "veriT+raSAT+Redlog"),
        ("veriT", "veriT"),
        ("Yices2", "Yices 2.6.2 for SMTCOMP 2021"),
        ("Yices-ismt", "yices-ismt-0721"),
        ("YicesQS", "yicesQS-2022-07-02-optim-under10"),
        ("Z3++BV", "z3++bv_0702"),
        ("Z3string", "Z3str4"),
        ("Z3++", "z3++0715"),
        ("Z3", "z3-4.8.17"),
        ("solsmt", "solsmt-5b37426cad388922a-wrapped"),
    ],
    "SMT-COMP 2023": [
        ("Bitwuzla", "Bitwuzla-fixed"),
        ("COLIBRI", "COLIBRI 2023_05_10"),
        ("CVC4", "CVC4-sq-final"),
        ("cvc5", "cvc5-default-2023-05-16-ea045f305"),
        ("iProver", "iProver-3.8-fix"),
        ("NRA-LS", "cvc5-NRA-LS-sq"),
        ("OpenSMT", "OpenSMT a78dcf01"),
        ("OSTRICH", "OSTRICH 1.3 SMT-COMP fixed"),
        ("Par4", "Par4-wrapped-sq"),
        ("Q3B", "Q3B"),
        ("SMTInterpol", "smtinterpol-2.5-1272-g2d6d356c"),
        ("SMT-RAT", "SMT-RAT-MCSAT"),
        ("STP", "STP 2022.4"),
        ("UltimateEliminator+MathSAT", "UltimateEliminator+MathSAT-5.6.9"),
        ("Vampire", "vampire_4.8_smt_pre"),
        ("Yices2", "Yices 2 for SMTCOMP 2023"),
        ("Yices-ismt", "yices-ismt-sq-0526"),
        ("YicesQS", "yicesQS-2022-07-02-optim-under10"),
        ("Z3alpha", "z3alpha"),
        ("Z3-Noodler", "Z3-Noodler"),
        ("Z3-Owl", "z3-Owl-Final"),
        ("Z3++", "z3++0715"),  # TODO: there is also Z3++_sq_0526.
        ("Z3", "z3-4.8.17"),
        ("Yaga", "Yaga_SMT-COMP-2023_presubmition"),
    ],
}

global_variant_table = []
global_variant_count = 1

# Helper to insert benchmarks with fewer database queries
global_variant_lookup = {}
for name, url in known_solvers:
    id = solver_count
    solver_count = solver_count + 1
    solver_table.append((id, name, url))

    # Also add the original name as a variant
    global_variant_table.append((global_variant_count, name, id))
    global_variant_lookup[name] = global_variant_count
    global_variant_count = global_variant_count + 1
    try:
        for variant in global_solver_variants[name]:
            global_variant_table.append((global_variant_count, variant, id))
            global_variant_lookup[variant] = global_variant_count
            global_variant_count = global_variant_count + 1
    except KeyError:
        pass


def populate_tables(connetion):
    connetion.executemany(
        "INSERT INTO Solvers(id, name, link) VALUES(?,?,?);", solver_table
    )

    connetion.executemany(
        "INSERT INTO SolverVariants(id, fullName, solver) VALUES(?,?,?);",
        global_variant_table,
    )


def populate_evaluation_solvers(connection, evaluationName, evaluationId):
    solvers = evaluation_solver_variants[evaluationName]
    for solver, variant in solvers:
        for row in connection.execute(
            "SELECT id FROM Solvers WHERE name=?",
            (solver,),
        ):
            solverId = row[0]
        connection.execute(
            "INSERT INTO SolverVariants(fullName, solver, evaluation) VALUES(?,?,?);",
            (variant, solverId, evaluationId),
        )
