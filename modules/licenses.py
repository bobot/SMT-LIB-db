def setup_licenses(connection):
    create_table(connection)
    populate_table(connection)
    connection.commit()


def create_table(connection):
    connection.execute(
        """CREATE TABLE Licenses(
        id INTNTEGER PRIMARY KEY,
        name TEXT,
        link TEXT,
        spdxIdentifier TEXT);"""
    )


static_data = [
    (
        "Creative Commons Attribution 4.0 International",
        "https://creativecommons.org/licenses/by/4.0/",
        "CC-BY-4.0",
    ),
    (
        "Creative Commons Attribution Share Alike 4.0 International",
        "https://creativecommons.org/licenses/by-sa/4.0/",
        "CC-BY-SA-4.0",
    ),
    (
        "Creative Commons Attribution Non Commercial 4.0 International",
        "https://creativecommons.org/licenses/by-nc/4.0/",
        "CC-BY-NC-4.0",
    ),
    (
        "Creative Commons Zero v1.0 Universal",
        "https://creativecommons.org/publicdomain/zero/1.0/",
        "CC0-1.0",
    ),
    (
        "GNU General Public License v2.0 or later",
        "https://www.gnu.org/licenses/gpl-2.0.html",
        " GPL-2.0-or-later",
    ),
    (
        "GNU General Public License v3.0 or later",
        "https://www.gnu.org/licenses/gpl-3.0.html",
        " GPL-3.0-or-later",
    ),
    ("Apache License 2.0", "https://www.apache.org/licenses/LICENSE-2.0", "Apache-2.0"),
    ("ISC License", "https://www.isc.org/licenses/", "ISC"),
    ("MIT License", "https://opensource.org/license/mit/", "MIT"),
    # Occurs as 'GPL' in some benchmarks
    (
        "GNU General Public License Unknown Version",
        "",
        "",
    ),
    # For the following, the full license text is incldude in the benchmarks.  This affects some of the benchmark in this set.
    (
        "CMU SoSy Lab",
        "https://clc-gitlab.cs.uiowa.edu:2443/SMT-LIB-benchmarks-inc/QF_ABVFP/-/blob/master/20190307-CPAchecker_kInduction-SoSy_Lab/rekcba_aso.1.M1-1_smt-query.0.smt2",
        "",
    ),
]


def populate_table(connetion):
    connetion.executemany(
        "INSERT INTO Licenses(name, link, spdxIdentifier) VALUES(?,?,?);", static_data
    )
