import copy
import logging
import os
import re
import sys
import traceback
from datetime import datetime
from types import TracebackType
from typing import Any, Literal, Mapping, MutableMapping, TextIO

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 'yes']

# Structured logs with JSON, disabled by default
LOG_JSON = os.getenv('LOG_JSON', 'False').lower() in ['true', '1', 'yes']
LOG_JSON_LEVEL_KEY = os.getenv('LOG_JSON_LEVEL_KEY', 'level')

if DEBUG:
    LOG_LEVEL = 'DEBUG'

LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'False').lower() in ['true', '1', 'yes']
DISABLE_COLOR_PRINTING = False

LOG_ALL_EVENTS = os.getenv('LOG_ALL_EVENTS', 'False').lower() in ['true', '1', 'yes']

ColorType = Literal[
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'light_grey',
    'dark_grey',
    'light_red',
    'light_green',
    'light_yellow',
    'light_blue',
    'light_magenta',
    'light_cyan',
    'white',
]

LOG_COLORS: Mapping[str, ColorType] = {
    'ACTION': 'green',
    'USER_ACTION': 'light_red',
    'OBSERVATION': 'yellow',
    'USER_OBSERVATION': 'light_green',
    'DETAIL': 'cyan',
    'ERROR': 'red',
    'PLAN': 'light_magenta',
}


class StackInfoFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.ERROR:
            # Only add stack trace info if there's an actual exception
            exc_info = sys.exc_info()
            if exc_info and exc_info[0] is not None:
                # Capture the current stack trace as a string
                stack = traceback.format_stack()
                # Remove the last entries which are related to the logging machinery
                stack = stack[:-3]  # Adjust this number if needed
                # Join the stack frames into a single string
                stack_str = ''.join(stack)
                setattr(record, 'stack_info', stack_str)
                setattr(record, 'exc_info', exc_info)
        return True


class NoColorFormatter(logging.Formatter):
    """Formatter for non-colored logging in files."""

    def format(self, record: logging.LogRecord) -> str:
        # Create a deep copy of the record to avoid modifying the original
        new_record = _fix_record(record)

        # Strip ANSI color codes from the message
        new_record.msg = strip_ansi(new_record.msg)

        return super().format(new_record)


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences (terminal color/formatting codes) from string.

    Removes ANSI escape sequences from str, as defined by ECMA-048 in
    http://www.ecma-international.org/publications/files/ECMA-ST/Ecma-048.pdf
    # https://github.com/ewen-lbh/python-strip-ansi/blob/master/strip_ansi/__init__.py
    """
    pattern = re.compile(r'\x1B\[\d+(;\d+){0,2}m')
    stripped = pattern.sub('', s)
    return stripped


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg_type = record.__dict__.get('msg_type', '')
        event_source = record.__dict__.get('event_source', '')
        if event_source:
            new_msg_type = f'{event_source.upper()}_{msg_type}'
            if new_msg_type in LOG_COLORS:
                msg_type = new_msg_type
        if msg_type in LOG_COLORS and not DISABLE_COLOR_PRINTING:
            # Simple colored output without external dependencies
            msg = record.msg
            time_str = self.formatTime(record, self.datefmt)
            name_str = record.name
            level_str = record.levelname
            if msg_type in ['ERROR'] or DEBUG:
                return f'{time_str} - {name_str}:{level_str}: {record.filename}:{record.lineno}\n{msg_type}\n{msg}'
            return f'{time_str} - {msg_type}\n{msg}'
        elif msg_type == 'STEP':
            if LOG_ALL_EVENTS:
                msg = '\n\n==============\n' + record.msg + '\n'
                return f'{msg}'
            else:
                return record.msg

        new_record = _fix_record(record)
        return super().format(new_record)


def _fix_record(record: logging.LogRecord) -> logging.LogRecord:
    new_record = copy.copy(record)
    # The formatter expects non boolean values, and will raise an exception if there is a boolean - so we fix these
    # LogRecord attributes are dynamically typed
    if getattr(new_record, 'exc_info', None) is True:
        setattr(new_record, 'exc_info', sys.exc_info())
        setattr(new_record, 'stack_info', None)
    return new_record


file_formatter = NoColorFormatter(
    '%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s',
    datefmt='%H:%M:%S',
)


def json_formatter():
    """Simple JSON formatter without external dependencies."""
    class SimpleJsonFormatter(logging.Formatter):
        def format(self, record):
            import json
            log_entry = {
                'timestamp': self.formatTime(record),
                'level': record.levelname,
                'message': record.getMessage(),
                'name': record.name,
                'filename': record.filename,
                'lineno': record.lineno,
            }
            return json.dumps(log_entry)
    
    return SimpleJsonFormatter()


def json_log_handler(
    level: int = logging.INFO,
    _out: TextIO = sys.stdout,
) -> logging.Handler:
    """
    Configure logger instance for structured logging as json lines.
    """

    handler = logging.StreamHandler(_out)
    handler.setLevel(level)
    handler.setFormatter(json_formatter())
    return handler


# Set up logging
logging.basicConfig(level=logging.ERROR)


def log_uncaught_exceptions(
    ex_cls: type[BaseException], ex: BaseException, tb: TracebackType | None
) -> Any:
    """Logs uncaught exceptions along with the traceback.

    Args:
        ex_cls: The type of the exception.
        ex: The exception instance.
        tb: The traceback object.

    Returns:
        None
    """
    if tb:  # Add check since tb can be None
        logging.error(''.join(traceback.format_tb(tb)))
    logging.error('{0}: {1}'.format(ex_cls, ex))


sys.excepthook = log_uncaught_exceptions
simplerun_logger = logging.getLogger('simplerun')
current_log_level = logging.INFO

if LOG_LEVEL in logging.getLevelNamesMapping():
    current_log_level = logging.getLevelNamesMapping()[LOG_LEVEL]
simplerun_logger.setLevel(current_log_level)

if DEBUG:
    simplerun_logger.addFilter(StackInfoFilter())

if current_log_level == logging.DEBUG:
    LOG_TO_FILE = True
    simplerun_logger.debug('DEBUG mode enabled.')

if LOG_JSON:
    simplerun_logger.addHandler(json_log_handler(current_log_level))
else:
    # Simple console handler without color dependencies
    console_handler = logging.StreamHandler()
    console_handler.setLevel(current_log_level)
    console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s', datefmt='%H:%M:%S'))
    simplerun_logger.addHandler(console_handler)

simplerun_logger.propagate = False
simplerun_logger.debug('Logging initialized')

LOG_DIR = os.path.join(
    # parent dir of simplerun/core (i.e., root of the repo)
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'logs',
)

if LOG_TO_FILE:
    def get_file_handler(log_dir: str, log_level: int = logging.INFO) -> logging.FileHandler:
        """Returns a file handler for logging."""
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d')
        file_name = f'simplerun_{timestamp}.log'
        file_handler = logging.FileHandler(os.path.join(log_dir, file_name))
        file_handler.setLevel(log_level)
        if LOG_JSON:
            file_handler.setFormatter(json_formatter())
        else:
            file_handler.setFormatter(file_formatter)
        return file_handler
    
    simplerun_logger.addHandler(get_file_handler(LOG_DIR, current_log_level))
    simplerun_logger.debug(f'Logging to file in: {LOG_DIR}')


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Gather sensitive values which should not ever appear in the logs.
        sensitive_values = []
        for key, value in os.environ.items():
            key_upper = key.upper()
            if (
                len(value) > 2
                and value != 'default'
                and any(s in key_upper for s in ('SECRET', '_KEY', '_CODE', '_TOKEN'))
            ):
                sensitive_values.append(value)

        # Replace sensitive values from env!
        msg = record.getMessage()
        for sensitive_value in sensitive_values:
            msg = msg.replace(sensitive_value, '******')

        # Replace obvious sensitive values from log itself...
        sensitive_patterns = [
            'api_key',
            'aws_access_key_id',
            'aws_secret_access_key',
            'e2b_api_key',
            'github_token',
            'jwt_secret',
            'llm_api_key',
        ]

        # add env var names
        env_vars = [attr.upper() for attr in sensitive_patterns]
        sensitive_patterns.extend(env_vars)

        for attr in sensitive_patterns:
            pattern = rf"{attr}='?([\w-]+)'?"
            msg = re.sub(pattern, f"{attr}='******'", msg)

        # Update the record
        record.msg = msg
        record.args = ()

        return True


simplerun_logger.addFilter(SensitiveDataFilter(simplerun_logger.name))


class SimplerunLoggerAdapter(logging.LoggerAdapter):
    extra: dict

    def __init__(
        self, logger: logging.Logger = simplerun_logger, extra: dict | None = None
    ) -> None:
        self.logger = logger
        self.extra = extra or {}

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """
        If 'extra' is supplied in kwargs, merge it with the adapters 'extra' dict
        Starting in Python 3.13, LoggerAdapter's merge_extra option will do this.
        """
        if 'extra' in kwargs and isinstance(kwargs['extra'], dict):
            kwargs['extra'] = {**self.extra, **kwargs['extra']}
        else:
            kwargs['extra'] = self.extra
        return msg, kwargs


# Export the main logger and adapter
logger = simplerun_logger
LoggerAdapter = SimplerunLoggerAdapter
