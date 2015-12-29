#coding=utf8

__author__ = 'Vincent@Home'


class TapApiError(Exception):
    pass


class TapNotAllowWrite(TapApiError):
    pass


class TapParameterMissing(TapApiError):
    pass


class TapAuthFail(TapApiError):
    pass


class ApiError(Exception):
    pass


class ApiAuthFail(ApiError):
    pass


class UserNotAvailable(Exception):
    pass


class CFNSyntaxError(Exception):
    pass


class BracketNotEnd(CFNSyntaxError):
    """括号没有结束"""
    pass
