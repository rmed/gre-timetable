# gre-timetable

Simple script to parse a timetable from the University of Greenwich portal into
an iCalendar file.

## Usage

```
$ virtualenv -p python3 venv && . venv/bin/activate
$ pip install -r requirements.txt
```

The script uses [PhantomJS](http://phantomjs.org/) as a driver, so either
download a static build and place it in the same directory or set the
`PHANTOMJS` environment variable indicating the path to the executable:

```
$ python gre-timetable.py
```

Or

```
$ PHANTOMJS=path/to/phantom python gre-timetable.py
```

You will be asked for your username and password and the term for which to fetch
the timetable (1, 2 or 3).
