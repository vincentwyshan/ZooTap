#coding=utf8
__author__ = 'Vincent@Home'

import re
import datetime
import decimal

from dateutil import parser

from tap.service.exceptions import (
    TapParameterMissing,
    CFNSyntaxError,
    BracketNotEnd
)


class ParaHandler(object):
    @classmethod
    def prepare(cls, paras, config_paras):
        result = {}
        for para in config_paras:
            if para.absent_type == 'NECESSARY' and para.name not in paras:
                raise TapParameterMissing(para.name.encode('utf8'))
            if para.name not in paras:
                result[para.name] = cls._para_value(para.val_type,
                                                     para.default)
            else:
                result[para.name] = cls._para_value(para.val_type,
                                                     paras[para.name])
        return result

    @classmethod
    def _para_value(cls, type_name, value):
        if value == 'NULL':
            return None
        elif value == 'NOW' and type_name == 'DATE':
            return datetime.datetime.now()

        if type_name == 'TEXT':
            return value
        elif type_name == 'INT':
            return int(value)
        elif type_name == 'DECIMAL':
            return decimal.Decimal(value)
        elif type_name == 'DATE':
            return parser.parse(value)
        return value


class StatementInfo:
    # type      # [BIND, EXPORT, CASE, DBSWITCH, ]
    script = None   # source code
    bind = None
    export = []
    db_name = None
    case_statement = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class CFNInterpreter(object):
    def __init__(self, sources=None, dbtype=None):
        """
        传入代码list
        :param sources: list of source code
        :param dbtype: database type
        :return:
        """
        self.sources = sources
        self.dbtype = dbtype
        self.info = StatementInfo()

    @classmethod
    def function_parse(cls, source):
        """
        检查是否有函数调用，如果有，解析出函数代码
        :return: (functions, sql)
        """
        if u':' not in source:
            return [], source
        if not re.match(ur'cfn', source, re.IGNORECASE):
            return [], source

        source = list(source)
        functions = []
        tmp = []
        string_start = None  # 标记字符串域开始
        # func_start = False  # 标记当前是否开始函数字符串, 不支持嵌套
        bracket_range = []  # 标记括号域
        while source:
            char = source.pop(0)
            if char in (u'"', u"'") and string_start is None:
                # 开始字符串域
                string_start = char
            elif char in (u'"', u"'") and string_start == char:
                # 结束字符串域
                string_start = None
            elif string_start:
                # 正在字符串域中
                pass
            elif char == u'(':
                # 开始括号域
                bracket_range.append(char)
            elif char == u')':
                # 结束一个括号域
                if len(bracket_range) == 0:
                    raise BracketNotEnd
                bracket_range.pop(-1)
            elif char == ':':
                # 结束函数statement
                break

            tmp.append(char)

            if len(bracket_range) == 0 and '(' in tmp:
                # 括号域完全结束, 同时代码中已经有括号, 结束函数域
                function = ''.join(tmp).strip()
                functions.append(function)
                tmp = []
        # 确保 tmp 中无剩余数据
        tmp = (u''.join(tmp)).strip()
        if tmp:
            raise CFNSyntaxError(tmp.encode('utf8'))

        source = u''.join(source)
        if not source or not functions:
            raise CFNSyntaxError
        return functions, u''.join(source)

    @classmethod
    def set_info(cls, functions, info):
        for func in functions:
            func_lower = func.lower()
            if func_lower.startswith(u'cfn_bind'):
                bind = func[9: -1]
                info.bind = bind.strip()
            elif func_lower.startswith(u'cfn_export'):
                export = func[11: -1]
                export = export.split(',')
                export = [p.strip().replace('@', '')
                          for p in export if p.strip()]
                export = [p.encode('utf8') if isinstance(p, unicode) else p
                          for p in export]
                info.export = export
            elif func_lower.startswith(u'cfn_case'):
                # 转换 所有 and or 小写
                case = func[9: -1]
                case = re.sub(ur'\band\b', ' and ', case, flags=re.IGNORECASE)
                case = re.sub(ur'\bor\b', ' or ', case, flags=re.IGNORECASE)
                case = case.replace(u'@', u'')
                if (re.search(ur'\bopen\b', case)
                    or re.search(ur'\bexec\b', case)
                    or re.search(ur'\bimport\b', case)
                    or re.search(ur'\bdir\b', case)
                    or re.search(ur'\bfile\b', case)
                    or re.search(ur'\bremove\b', case)
                    or re.search(ur'\bfile\b', case)
                    or re.search(ur'\bdir\b', case)
                    or re.search(ur'\beval\b', case)):
                    raise Exception("Not safe statement.")
                info.case_statement = case
            elif func_lower.startswith(u'cfn_dbswitch'):
                db_name = func[13: -1]
                info.db_name = db_name.strip()
            else:
                raise CFNSyntaxError(func.encode('utf8'))

    @classmethod
    def parse_one(cls, source):
        if not source:
            return StatementInfo()

        functions, source = cls.function_parse(source)
        # 根据解析结果，设定Statement Info
        info = StatementInfo(script=source)
        cls.set_info(functions, info)

        return info

    def __iter__(self):
        return self

    def next(self):
        """
        :return:
        """
        if not self.sources:
            raise StopIteration
        source = self.sources.pop(0).strip()
        if not source:
            return StatementInfo()

        return self.parse_one(source)
