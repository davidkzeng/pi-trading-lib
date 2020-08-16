import datetime


STANDARD_DATE_FORMAT = '%Y%m%d'


def from_date_str(date_str: str) -> datetime.date:
    return datetime.datetime.strptime(date_str, STANDARD_DATE_FORMAT).date()


def to_date_str(date: datetime.date) -> str:
    return date.strftime(STANDARD_DATE_FORMAT)
