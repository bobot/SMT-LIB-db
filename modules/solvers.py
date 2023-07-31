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

static_solvers = [
    ( 1, "Bitwuzla", "https://bitwuzla.github.io/"),
    ( 2, "COLIBRI", "https://colibri.frama-c.com/"),
    ( 3, "CVC4", "https://cvc4.github.io/"),
    ( 4, "cvc5", "https://cvc5.github.io/"),
    ( 5, "MathSAT", "https://mathsat.fbk.eu/"),
    ( 6, "NRA-LS", "https://github.com/minghao-liu/NRA-LS"),      
    ( 7, "OpenSMT", "https://verify.inf.usi.ch/opensmt"),
    ( 8, "OSTRICH", "https://github.com/uuverifiers/ostrich"),
    ( 9, "Par4", ""),
    (10, "Q3B", "https://github.com/martinjonas/Q3B/"),
    (11, "Q3B-pBNN", "https://www.fi.muni.cz/~xpavlik5/Q3B-pBDD/"),
    (12, "SMTInterpol", "https://ultimate.informatik.uni-freiburg.de/smtinterpol"),
    (13, "SMT-RAT", "https://smtrat.github.io/"), 
    (14, "solmt", "https://github.com/ethereum/solidity/"),
    (15, "STP", "https://stp.github.io/"),
    (16, "UltimateEliminator+MathSAT", "https://ultimate.informatik.uni-freiburg.de/eliminator/"),
    (17, "Vampire", "https://vprover.github.io/"),
    (18, "veriT", "https://verit-solver.org/"),
    (19, "veriT+raSAT+Redlog", "https://verit-solver.org/"),
    (20, "Yices2", "https://yices.csl.sri.com/"),
    (21, "Yices-ismt", "https://github.com/MRVAPOR/Yices-ismt"),
    (22, "YicesQS", "https://github.com/disteph/yicesQS"),
    (23, "Z3++", "https://z3-plus-plus.github.io/"),
    (24, "Z3", "https://github.com/Z3Prover/z3"),
    (25, "Z3++BV", "https://z3-plus-plus.github.io/"),
    (26, "Z3str4", "https://z3str4.github.io/"),
]

# Lists solver variants in SMT-COMP results, etc.
static_solver_variants = [
    ("Bitwuzla-fixed", 1),
    ("COLIBRI 22_06_18", 2),
    ("CVC4-sq-final", 3),
    ("cvc5-default-2022-07-02-b15e116-wrapped", 4),
    ("MathSAT-5.6.8", 5),
    ("NRA-LS-FINAL", 6),
    ("opensmt fixed", 7),
    ("OSTRICH 1.2", 8),
    ("Par4-wrapped-sq", 9),
    ("Q3B", 10),
    ("Q3B-pBDD SMT-COMP 2022 final", 11),
    ("smtinterpol-fixed-2.5-1148-gf2d8e6b0", 12),
    ("SMT-RAT-MCSAT", 13),
    ("solsmt-5b37426cad388922a-wrapped", 14),
    ("STP 2022.4", 15),
    ("UltimateEliminator+MathSAT-5.6.7-wrapped", 16),
    ("vampire_4.7_smt_fix-wrapped", 17),
    ("veriT", 18),
    ("veriT+raSAT+Redlog", 19),
    ("Yices 2.6.2 for SMTCOMP 2021", 20),
    ("yices-ismt-0721", 21),
    ("yicesQS-2022-07-02-optim-under10", 22),
    ("z3++0715", 23),
    ("z3-4.8.17", 24),
    ("z3++bv_0702", 25),
    ("Z3str4", 26)
]

def populate_tables(connetion):
    connetion.executemany(
        "INSERT INTO Solvers(id, name, link) VALUES(?,?,?);", static_solvers
    )

    connetion.executemany(
        "INSERT INTO SolverVariants(fullName, solver) VALUES(?,?);", static_solver_variants
    )
