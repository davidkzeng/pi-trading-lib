import typing as t
import datetime

STANDARD_DATE_FORMAT = '%Y%m%d'


def from_date_str(date_str: str) -> datetime.date:
    return datetime.datetime.strptime(date_str, STANDARD_DATE_FORMAT).date()


def to_date_str(date: datetime.date) -> str:
    return date.strftime(STANDARD_DATE_FORMAT)


def date_range(start_date: datetime.date, end_date: datetime.date) -> t.Generator[datetime.date, None, None]:
    num_dates = (end_date - start_date).days + 1
    for i in range(num_dates):
        yield start_date + datetime.timedelta(days=i)
