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
        FOREIGN KEY(solver) REFERENCES Solvers(id)
        );"""
    )


# Canonical names of SMT solvers
static_solvers = [
    (1, "Bitwuzla", "https://bitwuzla.github.io/"),
    (2, "COLIBRI", "https://colibri.frama-c.com/"),
    (3, "CVC4", "https://cvc4.github.io/"),
    (4, "cvc5", "https://cvc5.github.io/"),
    (5, "MathSAT", "https://mathsat.fbk.eu/"),
    (6, "NRA-LS", "https://github.com/minghao-liu/NRA-LS"),
    (7, "OpenSMT", "https://verify.inf.usi.ch/opensmt"),
    (8, "OSTRICH", "https://github.com/uuverifiers/ostrich"),
    (9, "Par4", ""),
    (10, "Q3B", "https://github.com/martinjonas/Q3B/"),
    (11, "Q3B-pBNN", "https://www.fi.muni.cz/~xpavlik5/Q3B-pBDD/"),
    (12, "SMTInterpol", "https://ultimate.informatik.uni-freiburg.de/smtinterpol"),
    (13, "SMT-RAT", "https://smtrat.github.io/"),
    (14, "solmt", "https://github.com/ethereum/solidity/"),
    (15, "STP", "https://stp.github.io/"),
    (
        16,
        "UltimateEliminator+MathSAT",
        "https://ultimate.informatik.uni-freiburg.de/eliminator/",
    ),
    (17, "Vampire", "https://vprover.github.io/"),
    (18, "veriT", "https://verit-solver.org/"),
    (19, "veriT+raSAT+Redlog", "https://verit-solver.org/"),
    (20, "Yices2", "https://yices.csl.sri.com/"),
    (21, "Yices-ismt", "https://github.com/MRVAPOR/Yices-ismt"),
    (22, "YicesQS", "https://github.com/disteph/yicesQS"),
    (23, "Z3++", "https://z3-plus-plus.github.io/"),
    (24, "Z3", "https://github.com/Z3Prover/z3"),
    (25, "Z3++BV", "https://z3-plus-plus.github.io/"),
    (26, "Z3string", "https://z3string.github.io/"),
    (27, "CVC3", "https://cs.nyu.edu/acsys/cvc3/"),
    (28, "ABC", "https://dl.acm.org/doi/10.1007/978-3-642-14295-6_5"),
    (29, "Norn", "https://user.it.uu.se/~jarst116/norn/"),
    (30, "S3P", "https://trinhmt.github.io/home/S3/"),
    (31, "Trau", "https://github.com/diepbp/Trau"),
    (32, "Alt-Ergo", "https://alt-ergo.ocamlpro.com/"),
    (33, "Barcelogic", "https://www.cs.upc.edu/~oliveras/bclt-main.html"),
    (34, "Boolector", "https://boolector.github.io/"),
    (35, "Yices", "https://yices.csl.sri.com/old/yices1-documentation.html"),
    (36, "CryptoMiniSat", "https://www.msoos.org/cryptominisat5/"),
    (37, "Z3-Trau", "https://github.com/diepbp/z3-trau"),
    (38, "Kaluza", "https://doi.org/10.1109/SP.2010.38"),
    (39, "SLENT", "https://github.com/NTU-ALComLab/SLENT"),
    (40, "Woorpje", "https://www.informatik.uni-kiel.de/~mku/woorpje/"),
    (41, "Kepler_22", "https://doi.org/10.1007/978-3-030-02768-1_19"),
    (42, "SPASS-IQ", "https://www.mpi-inf.mpg.de/de/departments/automation-of-logic/software/spass-workbench/spass-iq"),
]

# Lists solver variants in SMT-COMP results, etc.
static_solver_variants = {
    "Bitwuzla": ["Bitwuzla-fixed", "bitwuzla", "Bitwuzla (with SymFPU)"],
    "COLIBRI": ["COLIBRI 22_06_18"],
    "CVC4": ["CVC4-sq-final", "CVC4 (with SymFPU)"],
    "cvc5": ["cvc5-default-2022-07-02-b15e116-wrapped", "CVC5"],
    "MathSAT": ["MathSAT-5.6.8", "Mathsat5", "MathSAT5", "Mathsat"],
    "NRA-LS": ["NRA-LS-FINAL"],
    "OpenSMT": ["opensmt fixed"],
    "OSTRICH": ["OSTRICH 1.2", "Ostrich"],
    "Par4": ["Par4-wrapped-sq"],
    "Q3B": ["Q3B"],
    "Q3B-pBNN": ["Q3B-pBDD SMT-COMP 2022 final"],
    "SMTInterpol": ["smtinterpol-fixed-2.5-1148-gf2d8e6b0"],
    "SMT-RAT": ["SMT-RAT-MCSAT"],
    "solmt": ["solsmt-5b37426cad388922a-wrapped"],
    "STP": ["STP 2022.4"],
    "UltimateEliminator+MathSAT": ["UltimateEliminator+MathSAT-5.6.7-wrapped"],
    "Vampire": ["vampire_4.7_smt_fix-wrapped", "vampire"],
    "veriT": ["veriT"],
    "veriT+raSAT+Redlog": ["veriT+raSAT+Redlog"],
    "Yices2": ["Yices 2.6.2 for SMTCOMP 2021", "yices2", "Yices 2"],
    "Yices-ismt": ["yices-ismt-0721"],
    "YicesQS": ["yicesQS-2022-07-02-optim-under10"],
    "Z3++": ["z3++0715"],
    "Z3": ["z3-4.8.17", "z3", "z3;"],
    "Z3++BV": ["z3++bv_0702"],
    "Z3string": ["Z3-str2", "Z3str3", "Z3str4", "Z3str3RE"],
    "Woorpje": ["WOORPJE"],
    "Yices": ["YICES"],
}

solver_table = []
variant_table = []

solver_count = 1
variant_count = 1

# Helper to insert benchmarks with fewer database queries
variant_lookup = {}
for name, url in static_solvers:
    id = solver_count
    solver_count = solver_count + 1
    solver_table.append((id, name, url))

    variant_table.append((variant_count, name, id))
    # Also add the original name as a variant
    variant_table.append((variant_count, name, id))
    variant_lookup[name] = variant_count
    variant_count = variant_count + 1
    try:
        for variant in static_solver_variants[name]:
            variant_table.append((variant_count, variant, id))
            variant_lookup[variant] = variant_count
            variant_count = variant_count + 1
    except KeyError:
        pass


def populate_tables(connetion):
    connetion.executemany(
        "INSERT INTO Solvers(id, name, link) VALUES(?,?,?);", solver_table
    )

    connetion.executemany(
        "INSERT INTO SolverVariants(id, fullName, solver) VALUES(?,?,?);",
        variant_table,
    )
