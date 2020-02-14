import re

class _RegExLib:
    intregex = '[-+]?[0-9]+'

    """Set up regular expressions"""
    # use https://regexper.com to visualise these if required
    _reg_openparam = re.compile(r'^(\S+)\n')
    _reg_table = re.compile(r'^table=('+intregex+') parameter=('+intregex+').*')
    _reg_typelevel = re.compile(r'.*typeLevel=('+intregex+').*')
    _reg_timeRange = re.compile(r'.*timeRangeType=('+intregex+').*')
    _reg_comment = re.compile(r'^\!(.*)')
    _reg_preamble = re.compile(r'\bDICTIONARY_NAME.*\b|\bMODEL_TYPE.*\b|\bPRODUCT_CATEGORY\b|\bGRIB2_MASTER_TABLE_VERSION\b|\bGRIB2_LOCAL_TABLE_VERSION\b')

    def __init__(self, line):
        # check whether line has a positive match with all of the regular expressions
        self.openparam = self._reg_openparam.match(line)
        self.table = self._reg_table.match(line)
        self.typelevel = self._reg_typelevel.match(line)
        self.timeRange = self._reg_timeRange.match(line)
        self.comment = self._reg_comment.match(line)
        self.preamble = self._reg_preamble.match(line)

class typeOfLevelRegex:
    intregex = '[-+]?[0-9]+'

    _reg_param  = re.compile(r'^\'(.*)\'.*indicatorOfTypeOfLevel=('+intregex+').*')

    def __init__(self, line):
        self.param = self._reg_param.match(line)

def parseTypeLevel():
    filename = "../resources/typeOfLevel.def"
    paramdict={}
    with open(filename, 'r') as file:
        line = next(file)
        while line:
            reg_match = typeOfLevelRegex(line)
            if reg_match.param:
                paramdict[reg_match.param.group(1)] = int(reg_match.param.group(2))
            line = next(file, None)

    return paramdict

def parseGrib():
    parseTypeLevel()
    filename = "../resources/dictionary_cosmo.txt"
    paramdict={}
    with open(filename, 'r') as file:
        line = next(file)
        openb=False
        name = None
        while line:
            reg_match = _RegExLib(line)
            if reg_match.comment or reg_match.preamble:
                line = next(file, None)
                continue
            if reg_match.openparam:
                #check the previous entry has a table and parameter key
                if name:
                    if not ("table" in paramdict[name] and "parameter" in paramdict[name]):
                        print("Error, grib parameters not found in dictionary:", name, paramdict[name])
                        sys.exit(1)
                name = reg_match.openparam.group(1)
                paramdict[name] = {}

            if reg_match.table:
                paramdict[name]["table"] = int(reg_match.table.group(1))
                paramdict[name]["parameter"] = int(reg_match.table.group(2))

            if reg_match.typelevel:
                paramdict[name]["typeLevel"] = int(reg_match.typelevel.group(1))
            if reg_match.timeRange:
                paramdict[name]["timeRangeType"] = int(reg_match.timeRange.group(1))

            line = next(file, None)

    return paramdict

gribParams = parseGrib()
typeLevelParams = parseTypeLevel()