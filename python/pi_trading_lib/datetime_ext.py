import typing as t
import datetime

STANDARD_DATE_FORMAT = '%Y%m%d'


def from_str(date_str: t.Union[datetime.date, str]) -> datetime.date:
    if isinstance(date_str, datetime.date):
        return date_str
    return datetime.datetime.strptime(date_str, STANDARD_DATE_FORMAT).date()


def to_str(date: t.Union[datetime.date, str]) -> str:
    if isinstance(date, str):
        return date
    return date.strftime(STANDARD_DATE_FORMAT)


def date_range(begin_date: datetime.date, end_date: datetime.date,
               skip_dates: t.List[datetime.date] = []) -> t.Generator[datetime.date, None, None]:
    num_dates = (end_date - begin_date).days + 1
    for i in range(num_dates):
        next_date = begin_date + datetime.timedelta(days=i)
        if next_date in skip_dates:
            continue
        yield next_date


def prev(date: datetime.date) -> datetime.date:
    return date - datetime.timedelta(days=1)
