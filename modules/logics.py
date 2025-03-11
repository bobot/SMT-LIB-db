def setup_logics(connection):
    connection.execute(
        """CREATE TABLE Logics(
        logic TEXT PRIMARY KEY,
        quantifierFree BOOL,
        arrays BOOL,
        uninterpretedFunctions BOOL,
        bitvectors BOOL,
        floatingPoint BOOL,
        dataTypes BOOL,
        strings BOOL,
        nonLinear BOOL,
        difference BOOL,
        reals BOOL,
        integers BOOL
        );"""
    )


class LogicsCollector:
    def __init__(self, logicString):
        self.logic = logicString
        self.quantifierFree = False
        self.arrays = False
        self.uninterpretedFunctions = False
        self.bitvectors = False
        self.floatingPoint = False
        self.dataTypes = False
        self.strings = False
        self.nonLinear = False
        self.difference = False
        self.reals = False
        self.integers = False
        if logicString[:3] == "QF_":
            self.quantifierFree = True
            logicString = logicString[3:]
        if logicString == "AX":
            self.arrays = True
            return
        if logicString[:1] == "A":
            self.arrays = True
            logicString = logicString[1:]
        if logicString[:2] == "UF":
            self.uninterpretedFunctions = True
            logicString = logicString[2:]
        if logicString[:2] == "BV":
            self.bitvectors = True
            logicString = logicString[2:]
        # BV and DT can occur in either order. Hence, we just try twice.
        if logicString[:2] == "FP":
            self.floatingPoint = True
            logicString = logicString[2:]
        if logicString[:2] == "DT":
            self.dataTypes = True
            logicString = logicString[2:]
        if logicString[:2] == "FP":
            self.floatingPoint = True
            logicString = logicString[2:]
        if logicString[:2] == "DT":
            self.dataTypes = True
            logicString = logicString[2:]
        if logicString[:2] == "DT":
            self.dataTypes = True
            logicString = logicString[2:]
        if logicString[0:] == "S":
            self.string = True
            logicString = logicString[1:]

        if logicString == "IDL":
            self.integers = True
            self.difference = True
        elif logicString == "RDL":
            self.reals = True
            self.difference = True
        elif logicString == "LIA":
            self.integers = True
        elif logicString == "LRA":
            self.reals = True
        elif logicString == "LIRA":
            self.integers = True
            self.reals = True
        elif logicString == "NIA":
            self.integers = True
            self.nonLinear = True
        elif logicString == "NRA":
            self.reals = True
            self.nonLinear = True
        elif logicString == "NIRA":
            self.integers = True
            self.reals = True
            self.nonLinear = True

    def writeToDatabase(self, connection):
        connection.execute(
            """INSERT INTO Logics(
            logic,
            quantifierFree,
            arrays,
            uninterpretedFunctions,
            bitvectors,
            floatingPoint,
            dataTypes,
            strings,
            nonLinear,
            difference,
            reals,
            integers
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?);
            """,
            (
                self.logic,
                self.quantifierFree,
                self.arrays,
                self.uninterpretedFunctions,
                self.bitvectors,
                self.floatingPoint,
                self.dataTypes,
                self.strings,
                self.nonLinear,
                self.difference,
                self.reals,
                self.integers,
            ),
        )


def write_all_logics(connection):
    logics = [
        "ABV",
        "ABVFP",
        "ABVFPLRA",
        "ALIA",
        "ANIA",
        "AUFBV",
        "AUFBVDTLIA",
        "AUFBVDTNIA",
        "AUFBVDTNIRA",
        "AUFBVFP",
        "AUFDTLIA",
        "AUFDTLIRA",
        "AUFDTNIRA",
        "AUFFPDTNIRA",
        "AUFLIA",
        "AUFLIRA",
        "AUFNIA",
        "AUFNIRA",
        "BV",
        "BVFP",
        "BVFPLRA",
        "FP",
        "FPLRA",
        "LIA",
        "LRA",
        "NIA",
        "NRA",
        "QF_ABV",
        "QF_ABVFP",
        "QF_ABVFPLRA",
        "QF_ALIA",
        "QF_ANIA",
        "QF_AUFBV",
        "QF_AUFBVFP",
        "QF_AUFBVLIA",
        "QF_AUFBVNIA",
        "QF_AUFLIA",
        "QF_AUFNIA",
        "QF_AX",
        "QF_BV",
        "QF_BVFP",
        "QF_BVFPLRA",
        "QF_BVLRA",
        "QF_DT",
        "QF_FP",
        "QF_FPLRA",
        "QF_IDL",
        "QF_LIA",
        "QF_LIRA",
        "QF_LRA",
        "QF_NIA",
        "QF_NIRA",
        "QF_NRA",
        "QF_RDL",
        "QF_S",
        "QF_SLIA",
        "QF_SNIA",
        "QF_UF",
        "QF_UFBV",
        "QF_UFBVDT",
        "QF_UFBVLIA",
        "QF_UFDT",
        "QF_UFDTLIA",
        "QF_UFDTLIRA",
        "QF_UFDTNIA",
        "QF_UFFP",
        "QF_UFFPDTNIRA",
        "QF_UFIDL",
        "QF_UFLIA",
        "QF_UFLRA",
        "QF_UFNIA",
        "QF_UFNRA",
        "UF",
        "UFBV",
        "UFBVDT",
        "UFBVFP",
        "UFBVLIA",
        "UFDT",
        "UFDTLIA",
        "UFDTLIRA",
        "UFDTNIA",
        "UFDTNIRA",
        "UFFPDTNIRA",
        "UFIDL",
        "UFLIA",
        "UFLRA",
        "UFNIA",
        "UFNIRA",
        "UFNRA",
    ]
    for logic in logics:
        ll = LogicsCollector(logic)
        ll.writeToDatabase(connection)
    connection.commit()
