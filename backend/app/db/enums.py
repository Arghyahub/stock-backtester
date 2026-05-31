from enum import Enum


class UserType(str, Enum):
    ADMIN = "admin"
    GENERAL = "general"


class EquityType(str, Enum):
    INDEX = "INDEX"
    STOCK = "STOCK"
    ETF = "ETF"
    SECTOR = "SECTOR"

class IntervalType(str, Enum):
    MINUTE = "MINUTE"
    FIVE_MINUTE = "FIVE_MINUTE"
    FIFTEEN_MINUTE = "FIFTEEN_MINUTE"
    THIRTY_MINUTE = "THIRTY_MINUTE"
    ONE_HOUR = "ONE_HOUR"
    ONE_DAY = "ONE_DAY"
    ONE_WEEK = "ONE_WEEK"
    ONE_MONTH = "ONE_MONTH"
    ONE_YEAR = "ONE_YEAR"