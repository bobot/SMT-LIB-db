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
    ("4Simp", ""),
    ("ABC", "https://dl.acm.org/doi/10.1007/978-3-642-14295-6_5"),
    ("Abziz", "https://mabdula.github.io/"),
    ("Alt-Ergo", "https://alt-ergo.ocamlpro.com/"),
    ("AProVE", "https://aprove.informatik.rwth-aachen.de/"),
    ("Barcelogic", "https://www.cs.upc.edu/~oliveras/bclt-main.html"),
    ("Bitwuzla", "https://bitwuzla.github.io/"),
    ("Boolector", "https://boolector.github.io/"),
    (
        "Boolector-ReasonLS",
        "https://smt-comp.github.io/2019/system-descriptions/boolector-ReasonLS.pdf",
    ),
    ("COLIBRI", "https://colibri.frama-c.com/"),
    ("CryptoMiniSat", "https://www.msoos.org/cryptominisat5/"),
    ("Ctrl-Ergo", "https://gitlab.com/iguerNL/Ctrl-Ergo"),
    ("CVC3", "https://cs.nyu.edu/acsys/cvc3/"),
    ("CVC4", "https://cvc4.github.io/"),
    ("cvc5", "https://cvc5.github.io/"),
    ("iProver", "https://gitlab.com/korovin/iprover"),
    ("Kaluza", "https://doi.org/10.1109/SP.2010.38"),
    ("Kepler_22", "https://doi.org/10.1007/978-3-030-02768-1_19"),
    ("Kleaver", "https://klee-se.org/docs/kleaver-options/"),
    ("LazyBV2Int", "https://github.com/yoni206/lazybv2int"),
    ("MapleSTP", ""),
    ("MathSAT", "https://mathsat.fbk.eu/"),
    ("mc2", "https://github.com/c-cube/mc2"),
    ("MinkeyRink", "https://minkeyrink.com/"),
    ("Norn", "https://user.it.uu.se/~jarst116/norn/"),
    ("NRA-LS", "https://github.com/minghao-liu/NRA-LS"),
    ("OpenSMT", "https://verify.inf.usi.ch/opensmt"),
    ("OSTRICH", "https://github.com/uuverifiers/ostrich"),
    ("Par4", "https://github.com/tjark/Par"),
    ("ProB", "https://prob.hhu.de/w/index.php?title=Main_Page/"),
    ("Q3B", "https://github.com/martinjonas/Q3B/"),
    ("Q3B-pBNN", "https://www.fi.muni.cz/~xpavlik5/Q3B-pBDD/"),
    ("raSAT", ""),
    ("Redlog", "https://redlog.eu/"),
    ("S3P", "https://trinhmt.github.io/home/S3/"),
    ("SLENT", "https://github.com/NTU-ALComLab/SLENT"),
    ("SMTInterpol", "https://ultimate.informatik.uni-freiburg.de/smtinterpol"),
    ("SMT-RAT", "https://smtrat.github.io/"),
    ("solmt", "https://github.com/ethereum/solidity/"),
    (
        "SPASS-IQ",
        "https://www.mpi-inf.mpg.de/de/departments/automation-of-logic/software/spass-workbench/spass-iq",
    ),
    ("SONOLAR", "https://www.informatik.uni-bremen.de/agbs/florian/sonolar/"),
    (
        "SPASS-SAT",
        "https://www.mpi-inf.mpg.de/departments/automation-of-logic/software/spass-workbench/spass-satt/",
    ),
    ("STP", "https://stp.github.io/"),
    ("Toysmt", "https://github.com/msakai/toysolver/"),
    ("Trau", "https://github.com/diepbp/Trau"),
    (
        "UltimateEliminator",
        "https://ultimate.informatik.uni-freiburg.de/eliminator/",
    ),
    ("Vampire", "https://vprover.github.io/"),
    ("veriT", "https://verit-solver.org/"),
    ("Woorpje", "https://www.informatik.uni-kiel.de/~mku/woorpje/"),
    ("XSat", "https://github.com/zhoulaifu/xsat"),
    ("Yaga", "https://d3s.mff.cuni.cz/software/yaga/"),
    ("Yices2", "https://yices.csl.sri.com/"),
    ("Yices", "https://yices.csl.sri.com/old/yices1-documentation.html"),
    ("Yices-ismt", "https://github.com/MRVAPOR/Yices-ismt"),
    ("YicesLS", "https://smt-comp.github.io/2021/system-descriptions/YicesLS.pdf"),
    ("YicesQS", "https://github.com/disteph/yicesQS"),
    ("Z3alpha", "https://github.com/JohnLyu2/z3alpha"),
    ("Z3++BV", "https://z3-plus-plus.github.io/"),
    ("Z3", "https://github.com/Z3Prover/z3"),
    ("Z3++", "https://z3-plus-plus.github.io/"),
    ("Z3-Noodler", "https://github.com/VeriFIT/z3-noodler"),
    ("Z3-Owl", "https://z3-owl.github.io/"),
    ("Z3string", "https://z3string.github.io/"),
    ("Z3-Trau", "https://github.com/diepbp/z3-trau"),
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

# TODO: there are entries of the name "master-2018-06-10-b19c840-competition-default"
#       who are those?
# TODO: is it possible that solvers occur in two names that count (i.e. not
#       just a non-fixed and a fixed version.  Maybe there is an automated way
#       to map entries to results on the webpage.
# TODO: 2014 has solvers in different configurations
evaluation_solver_variants = {
    "SMT-COMP 2014": [
        ("4Simp", ["4Simp - 2014 default"]),
        (
            "Abziz",
            [
                "abziz_portfolio_all_features default",
                "abziz_portfolio_min_features default",
            ],
        ),
        ("AProVE", ["AProVE NIA 2014 default"]),
        (
            "Boolector",
            ["Boolector boolector", "Boolector boolectord", "Boolector boolectorj"],
        ),
        ("CVC3", ["CVC3 default"]),
        # Inconsistency: thereis also a "fixed resubmission" version
        ("CVC4", ["CVC4 f7118b2 default"]),
        (
            "Kleaver",
            [
                "Kleaver-indie-more-typed kleaver_indie_1",
                "Kleaver-indie-more-typed kleaver_portfolio",
            ],
        ),
        ("MathSAT", ["MathSAT-5.2.12-Main default"]),
        # Inconsitency: the participant page claims a "14b" verison was used.
        ("OpenSMT", ["opensmt2-2014-06-14c default"]),
        ("raSAT", ["raSAT-main-track-final default.sh"]),
        ("SMTInterpol", ["smtinterpol-2.1-118-g3dada2f default"]),
        ("SONOLAR", ["sonolar_smtcomp-2014 default"]),
        ("STP", ["stp-cryptominisat4 default"]),
        ("veriT", ["veriT-smtcomp2014 default"]),
        ("Yices2", ["Yices-2.2.1-smtcomp2014 default"]),
        ("Z3", ["Z3-4.3.2.a054b099c1d6-x64-debian-6.0.6-SMT-COMP-2014 default"]),
    ],
    "SMT-COMP 2015": [
        ("AProVE", ["AProVE NIA 2014 default"]),
        (
            "Boolector",
            [
                "Boolector SMT15 QF_BV final boolector_qf_bv",
                "Boolector SMT15 QF_AUFBV final boolector_qf_aufbv",
            ],
        ),
        ("CVC3", ["CVC3 default"]),
        (
            "CVC4",
            [
                "CVC4-master-2015-06-15-9b32405-main default",
                "CVC4-experimental-2015-06-15-ff5745a-main default",
            ],
        ),
        ("MathSAT", ["MathSat 5.3.6 main smtcomp2015_main"]),
        ("OpenSMT", ["OpenSMT2 default", "OpenSMT2-parallel default"]),
        ("raSAT", ["raSAT default.sh"]),
        ("SMT-RAT", ["SMT-RAT-final default", "SMT-RAT-NIA-Parallel-final default"]),
        ("SMTInterpol", ["SMTInterpol v2.1-206-g86e9531 default"]),
        (
            "STP",
            [
                "stp-cryptominisat4 default",
                "stp-cmsat4-v15 default",
                "stp-cmsat4-mt-v15 default",
                "stp-minisat-v15 default",
            ],
        ),
        ("veriT", ["veriT default"]),
        ("Yices2", ["Yices default", "Yices2-NL default"]),
        ("Z3", ["Z3-unstable default", "z3-ijcar14 z3-ijcar14", "z3 4.4.0 default"]),
    ],
    "SMT-COMP 2016": [
        ("ABC", ["ABC_default default_abc", "ABC_glucose glucose"]),
        ("AProVE", ["AProVE NIA 2014 default"]),
        ("Boolector", ["Boolector boolector", "Boolector preprop boolector"]),
        ("CVC4", ["CVC4-master-2016-05-27-cfef263-main default"]),
        ("MapleSTP", ["MapleSTP default", "MapleSTP-mt default"]),
        ("MathSAT", ["mathsat-5.3.11-linux-x86_64-Main default"]),
        ("MinkeyRink", ["Minkeyrink  2016 default"]),
        ("OpenSMT", ["OpenSMT2-2016-05-12 default"]),
        ("ProB", ["ProB competition"]),
        ("Q3B", ["Q3B default"]),
        ("raSAT", ["raSAT 0.3 default.sh", "raSAT 0.4 exp - final default.py"]),
        ("SMTInterpol", ["smtinterpol-2.1-258-g92ab3df default"]),
        ("SMT-RAT", ["SMT-RAT default"]),
        (
            "STP",
            [
                "stp-cms-exp-2016 default",
                "stp-cms-mt-2016 default",
                "stp-cms-st-2016 default",
                "stp-minisat-st-2016 default",
            ],
        ),
        ("Toysmt", ["toysmt default"]),
        (
            "Vampire",
            [
                "vampire_smt_4.1 vampire_smtcomp",
                "vampire_smt_4.1_parallel vampire_smtcomp",
            ],
        ),
        ("veriT", ["veriT-dev default"]),
        ("Yices2", ["Yices-2.4.2 default"]),
        ("Z3", ["z3-4.4.1 default"]),
    ],
    "SMT-COMP 2017": [
        ("AProVE", ["AProVE NIA 2014 default"]),
        (
            "Boolector",
            [
                "Boolector+CaDiCaL SMT17 final boolector",
                "Boolector SMT17 final boolector",
            ],
        ),
        ("COLIBRI", ["COLIBRI 18_06_2017 105a81 default"]),
        ("CVC4", ["CVC4-smtcomp2017-main default"]),
        ("MathSAT", ["mathsat-5.4.1-linux-x86_64-Main default"]),
        ("MinkeyRink", ["MinkeyRink 2017.3a default"]),
        ("OpenSMT", ["opensmt2-2017-06-04 default"]),
        ("Q3B", ["Q3B default"]),
        ("Redlog", ["Redlog default"]),
        ("SMTInterpol", ["SMTInterpol default"]),
        ("SMT-RAT", ["SMTRAT-comp2017_2 default"]),
        ("STP", ["stp_st default", "stp_mt default"]),
        ("Vampire", ["vampire4.2-smt vampire"]),
        (
            "veriT",
            [
                "veriT-2017-06-17 default",
                "veriT+raSAT+Redlog default",
                "veriT+Redlog_20170618 default",
            ],
        ),
        ("XSat", ["xsat-smt-comp-2017 default"]),
        ("Yices2", ["Yices2-Main default"]),
        ("Z3", ["z3-4.5.0 default"]),
    ],
    "SMT-COMP 2018": [
        ("Alt-Ergo", ["Alt-Ergo-SMTComp-2018_default"]),
        ("AProVE", ["AProVE NIA 2014_default"]),
        ("Boolector", ["Boolector_default"]),
        ("COLIBRI", ["COLIBRI 10_06_18 v2038_default"]),
        ("Ctrl-Ergo", ["Ctrl-Ergo-SMTComp-2018_default"]),
        # What is this `master-...` version of CVC4? It appears with solver
        # id "19775" on StarExec.  However, it is not listed as a particiapant,
        # but is listed as 2018 CVC4 in 2019.
        (
            "CVC4",
            [
                "CVC4-experimental-idl-2_default",
                "master-2018-06-10-b19c840-competition-default_default",
            ],
        ),
        ("MathSAT", ["mathsat-5.5.2-linux-x86_64-Main_default"]),
        ("MinkeyRink", ["Minkeyrink MT_mt", "Minkeyrink ST_st"]),
        ("OpenSMT", ["opensmt2_default"]),
        ("Q3B", ["Q3B_default"]),
        ("SMTInterpol", ["SMTInterpol-2.5-19-g0d39cdee_default"]),
        ("SMT-RAT", ["SMTRAT-Rat-final_default", "SMTRAT-MCSAT-final_default"]),
        ("SPASS-SATT", ["SPASS-SATT_default"]),
        (
            "STP",
            [
                "STP-CMS-st-2018_default-no-stderr",
                "STP-CMS-mt-2018_multicore-no-stderr",
                "STP-Riss-st-2018_riss-no-stderr",
            ],
        ),
        ("Vampire", ["vampire-4.3-smt_vampire_smtcomp"]),
        ("veriT", ["veriT_default", "veriT+raSAT+Reduce_default"]),
        ("Yices2", ["Yices 2.6.0_default"]),
        ("Z3", ["z3-4.7.1_default"]),
    ],
    "SMT-COMP 2019": [
        ("Alt-Ergo", ["Alt-Ergo-SMTComp-2019-wrapped-sq_default"]),
        ("AProVE", ["AProVE NIA 2014-wrapped-sq_default"]),
        ("Boolector", ["Boolector-wrapped-sq_default", "Poolector-wrapped-sq_default"]),
        ("Boolector-ReasonLS", ["boolector-ReasonLS-wrapped-sq_default"]),
        ("COLIBRI", ["colibri 2176-fixed-config-file-wrapped-sq_default"]),
        ("Ctrl-Ergo", ["Ctrl-Ergo-2019-wrapped-sq_default"]),
        (
            "CVC4",
            [
                "CVC4-2019-06-03-d350fe1-wrapped-sq_default",
                "CVC4-SymBreak_03_06_2019-wrapped-sq_default",
                "master-2018-06-10-b19c840-competition-default_default",
            ],
        ),
        (
            "MathSAT",
            [
                "mathsat-20190601-wrapped-sq_default",
                "mathsat-na-20190601-wrapped-sq_default",
            ],
        ),
        (
            "MinkeyRink",
            ["MinkeyRink MT-wrapped-sq_default", "MinkeyRink ST-wrapped-sq_default"],
        ),
        ("OpenSMT", ["OpenSMT-wrapped-sq_default"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        ("ProB", ["ProB-wrapped-sq_default"]),
        ("Q3B", ["Q3B-wrapped-sq_default"]),
        ("SMTInterpol", ["smtinterpol-2.5-514-wrapped-sq_default"]),
        (
            "SMT-RAT",
            [
                "SMTRAT-5-wrapped-sq_default",
                "SMTRAT-MCSAT-4-wrapped-sq_default",
                "SMTRAT-Rat-final_default",
            ],
        ),
        ("SPASS-SATT", ["SPASS-SATT-wrapped-sq_default"]),
        (
            "STP",
            [
                "STP-2019-wrapped-sq_default",
                "stp-mergesat-fixed-wrapped-sq_default",
                "stp-minisat-wrapped-sq_default",
                "stp-mt-wrapped-sq_default",
                "stp-portfolio-fixed-wrapped-sq_default",
                "stp-riss-wrapped-sq_default",
            ],
        ),
        (
            "UltimateEliminator",
            [
                "UltimateEliminator+MathSAT-5.5.4-wrapped-sq_default",
                "UltimateEliminator+SMTInterpol-wrapped-sq_default",
                "UltimateEliminator+Yices-2.6.1-wrapped-sq_default",
            ],
        ),
        (
            "Vampire",
            [
                "vampire-4.4-smtcomp-wrapped-sq_default",
                "vampire-4.3-smt_vampire_smtcomp",
            ],
        ),
        (
            "veriT",
            ["veriT-wrapped-sq_default", "veriT+raSAT+Redlog-wrapped-sq_default"],
        ),
        (
            "Yices2",
            [
                "Yices 2.6.0_default",
                "Yices 2.6.2-wrapped-sq_default",
                "Yices 2.6.2 Cadical-wrapped-sq_default",
                "Yices 2.6.2 Cryptominisat-wrapped-sq_default",
                "Yices 2.6.2 MCSAT BV-wrapped-sq_default",
                "Yices 2.6.2 new bvsolver-wrapped-sq_default",
            ],
        ),
        ("Z3", ["z3-4.8.4-d6df51951f4c-wrapped-sq_default", "z3-4.7.1_default"]),
    ],
    "SMT-COMP 2020": [
        ("Alt-Ergo", ["Alt-Ergo-SMTComp-2020_default"]),
        ("AProVE", ["AProVE NIA 2014_default"]),
        ("Bitwuzla", ["Bitwuzla-fixed_default"]),
        ("Boolector", ["Boolector-wrapped-sq_default", "Poolector-wrapped-sq_default"]),
        ("COLIBRI", ["COLIBRI 20.5.25_default"]),
        (
            "CVC4",
            [
                "CVC4-sq-final_default",
                "master-2018-06-10-b19c840-competition-default_default",
                "CVC4-2019-06-03-d350fe1-wrapped-sq_default",
            ],
        ),
        ("LazyBV2Int", ["LazyBV2Int20200523_default.sh"]),
        ("MathSAT", ["MathSAT5_default.sh", "mathsat-20190601-wrapped-sq_default"]),
        (
            "MinkeyRink",
            ["MinkeyRink Solver 2020.3.1_default", "MinkeyRink Solver 2020.3_default"],
        ),
        ("OpenSMT", ["OpenSMT_default"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        ("SMTInterpol", ["smtinterpol-2.5-679-gacfde87a_default"]),
        (
            "SMT-RAT",
            [
                "smtrat-SMTCOMP_default",
                "smtrat-CDCAC_default",
                "smtrat-MCSAT_default",
                "SMTRAT-Rat-final_default",
            ],
        ),
        ("SPASS-SATT", ["SPASS-SATT-wrapped-sq_default"]),
        ("STP", ["STP_default", "STP ++ Mergsat v1_default"]),
        ("UltimateEliminator", ["UltimateEliminator+MathSAT-5.6.3_s_default"]),
        (
            "Vampire",
            [
                "vampire_smt_4.5_vampire_smtcomp",
                "vampire-4.3-smt_vampire_smtcomp",
                "vampire-4.4-smtcomp-wrapped-sq_default",
            ],
        ),
        (
            "veriT",
            ["veriT_default", "veriT+raSAT+Redlog_default", "veriT+vite_default"],
        ),
        ("Yices2", ["Yices 2.6.2 bug fix_default", "Yices 2.6.0_default"]),
        ("Z3string", ["Z3str4 SMTCOMP2020 v1.1_default"]),
        (
            "Z3",
            [
                "z3-4.8.8_default",
                "z3-4.7.1_default",
                "z3-4.8.4-d6df51951f4c-wrapped-sq_default",
            ],
        ),
    ],
    "SMT-COMP 2021": [
        ("AProVE", ["AProVE NIA 2014_2021"]),
        ("Bitwuzla", ["Bitwuzla-fixed_default"]),
        (
            "COLIBRI",
            [
                "COLIBRI_21_06_23_default",
                "COLIBRI 20.5.25_default",
                "COLIBRI_21_05_28_default",
            ],
        ),
        (
            "CVC4",
            [
                "CVC4-2019-06-03-d350fe1-wrapped-sq_default",
                "CVC4-sq-final_default",
                "master-2018-06-10-b19c840-competition-default_default",
            ],
        ),
        ("cvc5", ["cvc5-fixed_default"]),
        ("iProver", ["iProver-v3.5-final-fix2_iProver_SMT"]),
        ("MathSAT", ["mathsat-5.6.6_default", "mathsat-20190601-wrapped-sq_default"]),
        ("mc2", ["mc2 2021-06-07_default.sh"]),
        ("OpenSMT", ["OpenSMT-fixed_default"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        (
            "SMTInterpol",
            [
                "smtinterpol-2.5-823-g881e8631_default",
                "smtinterpol-2.5-514-wrapped-sq_default",
            ],
        ),
        ("SMT-RAT", ["smtrat-SMTCOMP_default", "smtrat-MCSAT_default"]),
        ("STP", ["STP 2021.0_default"]),
        ("UltimateEliminator", ["UltimateEliminator+MathSAT-5.6.6_default"]),
        (
            "Vampire",
            [
                "vampire_smt_4.6-fixed_vampire_smtcomp",
                "vampire_smt_4.5_vampire_smtcomp",
            ],
        ),
        ("veriT", ["veriT_default", "veriT+raSAT+Redlog_default"]),
        (
            "Yices2",
            [
                "Yices 2.6.2 bug fix_default",
                "Yices 2.6.0_default",
                "Yices 2.6.2 for SMTCOMP2020_default",
            ],
        ),
        ("YicesLS", ["YicesLS_0611_1448_default"]),
        ("YicesQS", ["yices-QS-2021-06-13under10_default"]),
        ("Z3string", ["Z3str4 SMTCOMP 2021 v1.1_default"]),
        (
            "Z3",
            [
                "z3-4.8.11_default",
                "z3-4.7.1_default",
                "z3-4.8.4-d6df51951f4c-wrapped-sq_default",
                "z3-4.8.8_default",
            ],
        ),
    ],
    "SMT-COMP 2022": [
        ("Bitwuzla", ["Bitwuzla-fixed_default"]),
        ("COLIBRI", ["COLIBRI 22_06_18_default"]),
        ("CVC4", ["CVC4-sq-final_default"]),
        ("cvc5", ["cvc5_default", "cvc5-default-2022-07-02-b15e116-wrapped_sq"]),
        ("MathSAT", ["MathSAT-5.6.8_default"]),
        ("NRA-LS", ["NRA-LS-FINAL_default"]),
        ("OpenSMT", ["opensmt fixed_default"]),
        ("OSTRICH", ["OSTRICH 1.2_def"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        ("Q3B", ["Q3B_default"]),
        ("Q3B-pBNN", ["Q3B-pBDD SMT-COMP 2022 final_default"]),
        ("SMTInterpol", ["smtinterpol-fixed-2.5-1148-gf2d8e6b0_default"]),
        ("SMT-RAT", ["SMT-RAT-MCSAT_default"]),
        ("solsmt", ["solsmt-5b37426cad388922a-wrapped_default"]),
        ("STP", ["STP 2022.4_default"]),
        (
            "UltimateEliminator",
            ["UltimateEliminator+MathSAT-5.6.7-wrapped_default"],
        ),
        (
            "Vampire",
            [
                "vampire_4.7_smt_fix-wrapped_default",
                "vampire_4.7_smt_fix-wrapped_vampire_smtcomp",
            ],
        ),
        ("veriT", ["veriT_default", "veriT+raSAT+Redlog_default"]),
        ("Yices2", ["Yices 2.6.2 for SMTCOMP 2021_default"]),
        ("Yices-ismt", ["yices-ismt-0721_default"]),
        ("YicesQS", ["yicesQS-2022-07-02-optim-under10_default"]),
        ("Z3++BV", ["z3++bv_0702_default"]),
        ("Z3string", ["Z3str4_default"]),
        ("Z3++", ["z3++0715_default"]),
        ("Z3", ["z3-4.8.17_default", "z3-4.8.11_default"]),
    ],
    "SMT-COMP 2023": [
        ("Bitwuzla", ["Bitwuzla-fixed_default"]),
        ("COLIBRI", ["COLIBRI 2023_05_10_default"]),
        ("CVC4", ["CVC4-sq-final_default"]),
        (
            "cvc5",
            [
                "cvc5-default-2023-05-16-ea045f305_sq",
                "cvc5-default-2022-07-02-b15e116-wrapped_sq",
            ],
        ),
        ("iProver", ["iProver-3.8-fix_iprover_SMT"]),
        ("NRA-LS", ["cvc5-NRA-LS-sq_default"]),
        ("OpenSMT", ["OpenSMT a78dcf01_default"]),
        ("OSTRICH", ["OSTRICH 1.3 SMT-COMP fixed_def"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        ("Q3B", ["Q3B_default"]),
        ("SMTInterpol", ["smtinterpol-2.5-1272-g2d6d356c_default"]),
        ("SMT-RAT", ["SMT-RAT-MCSAT_default"]),
        ("STP", ["STP 2022.4_default"]),
        (
            "UltimateEliminator",
            [
                "UltimateEliminator+MathSAT-5.6.9_default",
                "UltimateIntBlastingWrapper+SMTInterpol_default",
            ],
        ),
        ("Vampire", ["vampire_4.8_smt_pre_vampire_smtcomp"]),
        ("Yaga", ["Yaga_SMT-COMP-2023_presubmition_default"]),
        (
            "Yices2",
            [
                "Yices 2 for SMTCOMP 2023_default",
                "Yices 2.6.2 for SMTCOMP 2021_default",
            ],
        ),
        ("Yices-ismt", ["yices-ismt-sq-0526_default"]),
        ("YicesQS", ["yicesQS-2022-07-02-optim-under10_default"]),
        ("Z3alpha", ["z3alpha_default"]),
        ("Z3-Noodler", ["Z3-Noodler_default"]),
        ("Z3-Owl", ["z3-Owl-Final_default"]),
        ("Z3++", ["z3++0715_default", "Z3++_sq_0526_default"]),
        ("Z3", ["z3-4.8.17_default", "z3-4.8.11_default"]),
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
    for solver, variants in solvers:
        for row in connection.execute(
            "SELECT id FROM Solvers WHERE name=?",
            (solver,),
        ):
            solverId = row[0]
        for variant in variants:
            connection.execute(
                "INSERT INTO SolverVariants(fullName, solver, evaluation) VALUES(?,?,?);",
                (variant, solverId, evaluationId),
            )
