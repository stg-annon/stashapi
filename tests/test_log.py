from enum import StrEnum
from types import TracebackType
from typing import Callable, TextIO, TypeAlias, cast, final, override
from unittest.mock import Mock, patch

import pytest

import stashapi.log as log

LEVEL_PREFIX_BYTE = "\x01"
MSG_PREFIX_BYTE = "\x02"
MSG_LEN_MAX = 64000
OUTPUT_FORMAT = f"{LEVEL_PREFIX_BYTE}{{}}{MSG_PREFIX_BYTE}{{}}\n"


class Level(StrEnum):
    TRACE = "t"
    DEBUG = "d"
    INFO = "i"
    WARNING = "w"
    ERROR = "e"
    PROGRESS = "p"


FUNC_MAPPING = {
    Level.TRACE: "trace",
    Level.DEBUG: "debug",
    Level.INFO: "info",
    Level.WARNING: "warning",
    Level.ERROR: "error",
    Level.PROGRESS: "progress",
}

LEVEL_MAPPING = {
    Level.TRACE: 5,
    Level.DEBUG: 10,
    Level.INFO: 20,
    Level.WARNING: 30,
    Level.ERROR: 40,
    Level.PROGRESS: 50,
}


class MockStream(TextIO):
    def __init__(self):
        self.written: list[str] = list()

    @override
    def write(self, buf: str) -> int:
        self.written.append(buf)
        return len(buf)

    @override
    def flush(self):
        pass


@final
class MockHandler(log.StashLogHandler):
    def __init__(self, stream: TextIO):
        super().__init__()
        # override the stream to use for testing
        self.stream = stream


@final
class Patches:
    def __init__(self, *patches: Mock):
        self.patches = patches

    def __enter__(self):
        for patch in self.patches:
            _ = patch.__enter__()  #  pyright: ignore[reportAny]

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException,
        traceback: TracebackType,
    ):
        for patch in self.patches:
            patch.__exit__(exc_type, exc_value, traceback)  #  pyright: ignore[reportAny]


PatchedLogger: TypeAlias = tuple[MockStream, Patches]


@pytest.fixture
def patched_logger() -> PatchedLogger:

    mock_stream = MockStream()
    mock_handlers = [MockHandler(mock_stream)]

    # idk how to handle the type of what `patch` returns. Allegedly it's a `Mock`?
    p1 = cast(Mock, patch("stashapi.log.sys.stderr", new=mock_stream))
    p2 = cast(Mock, patch("stashapi.log.sl.handlers", new=mock_handlers))

    return mock_stream, Patches(p1, p2)


def test_meta():
    # try to protect against the underlying implementation changing
    assert len(log.sl.handlers) == 1
    assert isinstance(log.sl.handlers[0], log.StashLogHandler)


testcases = [
    (Level.TRACE, "test trace"),
    (Level.DEBUG, "test debug"),
    (Level.INFO, "test info"),
    (Level.WARNING, "test warning"),
    (Level.ERROR, "test error"),
    (Level.PROGRESS, 0.5),
    (Level.TRACE, "test max length string" + ("a" * (MSG_LEN_MAX + 10))),
]


@pytest.mark.parametrize(
    ["level", "msg"],
    testcases,
    ids=list(range(len(testcases))),
)
def test_logger_outputs(patched_logger: PatchedLogger, level: Level, msg: str | float):
    """
    Test that each of the provided logging functions produces data in the expected format
    """
    # this test isn't testing log levels, max it out so we see everything
    log.sl.setLevel(LEVEL_MAPPING[Level.TRACE])

    stderr, patches = patched_logger
    with patches:
        # call the relevant logging function
        func: Callable[..., None] = getattr(log, FUNC_MAPPING[level])
        assert func
        func(msg)

        # only limit the length of the msg if it is a string
        if isinstance(msg, str):
            msg = msg[:MSG_LEN_MAX]

        assert stderr.written[-1] == OUTPUT_FORMAT.format(level, msg)


@pytest.mark.parametrize(
    ["level"],
    [
        Level.TRACE,
        Level.DEBUG,
        Level.INFO,
        Level.WARNING,
        Level.ERROR,
        Level.PROGRESS,
    ],
)
def test_log_levels(patched_logger: PatchedLogger, level: Level):
    """
    Test that log level is respected for each level
    """
    stderr, patches = patched_logger

    # get levels that we expect to be able to see
    expected_levels = [l for l in Level if LEVEL_MAPPING[l] <= LEVEL_MAPPING[level]]

    func: Callable[..., None] = getattr(log.sl, FUNC_MAPPING[level])
    assert func

    with patches:
        for check_level in Level:
            log.sl.setLevel(LEVEL_MAPPING[check_level])
            count = len(stderr.written)
            func("testmsg")

            # count should increase if this log level is expected to show the message we tried to log
            # if not, should stay the same
            if check_level in expected_levels:
                assert len(stderr.written) > count
            else:
                assert len(stderr.written) == count


@pytest.mark.parametrize(
    ["msg", "expected"],
    [
        (
            "data blob test with blob 'data:image/jpeg;base64,asdfasdfasdf'",
            "data blob test with blob 'data:image/jpeg;base64,<BASE64_DATA(12)>'",
        ),
        (
            'data blob test with blob "data:image/jpeg;base64,asdfasdfasdf"',
            'data blob test with blob "data:image/jpeg;base64,<BASE64_DATA(12)>"',
        ),
    ],
    ids=[0, 1],
)
def test_blob_replacement(patched_logger: PatchedLogger, msg: str, expected: str):
    # this test isn't testing log levels, max it out so we see everything
    log.sl.setLevel(LEVEL_MAPPING[Level.TRACE])

    stderr, patches = patched_logger
    with patches:
        log.info(msg)  # pyright: ignore[reportUnknownMemberType]
        assert stderr.written[-1] == OUTPUT_FORMAT.format(Level.INFO, expected[:MSG_LEN_MAX])


class TestRepr:
    @override
    def __repr__(self):
        return "Test class for serialization to cover anything that has a repr"


@pytest.mark.parametrize(
    ["data", "expected"],
    [
        ("trivial test with string", "trivial test with string"),
        (
            {"testkey": 1, "testkey2": "asdf", "testkey3": [1, 2, 3]},
            '{"testkey": 1, "testkey2": "asdf", "testkey3": [1, 2, 3]}',
        ),
        (TestRepr(), "Test class for serialization to cover anything that has a repr"),
    ],
)
def test_serialization(patched_logger: PatchedLogger, data: object, expected: str):
    """
    Test that anything passed into a log function gets serialized appropriately.
    There are 3 cases to consider:
      - Strings: should be trivially printed
      - Dicts: should be serialized as json
      - Other: anything else should be serialized by calling `str(x)` on it, which effectively
          covers all other cases by calling the `__repr__` method for that object
    """
    # this test isn't testing log levels, max it out so we see everything
    log.sl.setLevel(LEVEL_MAPPING[Level.TRACE])

    stderr, patches = patched_logger
    with patches:
        log.info(data)  #  pyright: ignore[reportUnknownMemberType]
        assert stderr.written[-1] == OUTPUT_FORMAT.format(Level.INFO, expected[:MSG_LEN_MAX])


def test_progress_on_stderr_only():
    # this test isn't testing log levels, max it out so we see everything
    log.sl.setLevel(LEVEL_MAPPING[Level.TRACE])

    # can't use the fixture here because we are specifically testing the case
    # where the stream is not equal to stderr, which the fixture ensures
    mock_stream = MockStream()
    mock_handlers = [MockHandler(mock_stream)]

    patched_handler = patch("stashapi.log.sl.handlers", new=mock_handlers)

    with patched_handler:
        count = len(mock_stream.written)
        log.progress(0.5)  # pyright: ignore[reportUnknownMemberType]
        assert len(mock_stream.written) == count


def test_progress_disabled(patched_logger: PatchedLogger):
    # this test isn't testing log levels, max it out so we see everything
    log.sl.setLevel(LEVEL_MAPPING[Level.TRACE])

    stderr, patches = patched_logger
    with patches:
        # first confirm progress is still working
        assert len(stderr.written) == 0
        log.progress(0.5)  # pyright: ignore[reportUnknownMemberType]

        count = len(stderr.written)
        assert count > 0

        # then ensure no output when progress is disabled
        log.DISABLE_PROGRESS = True
        log.progress(0.5)  # pyright: ignore[reportUnknownMemberType]
        assert len(stderr.written) == count


@pytest.mark.parametrize(
    ["msg", "err", "expected"],
    [
        (None, None, '{"output": "ok", "error": null}'),
        ("test msg", None, '{"output": "test msg", "error": null}'),
        ("test msg", "test error", '{"output": "test msg", "error": "test error"}'),
    ],
    ids=[0, 1, 2],
)
def test_result(msg: str | None, err: str | None, expected: str):
    mock_stdout = MockStream()
    with (
        patch("stashapi.log.sys.stdout", new=mock_stdout),
        patch("stashapi.log.sys.exit"),
    ):
        log.exit(msg, err)  # pyright: ignore[reportUnknownMemberType]
        # note: using index 0 here because I guess the call to `print`
        # prints the newline separately from the actual content? wack
        assert mock_stdout.written[0] == expected


@pytest.mark.parametrize(
    ["data", "expected"],
    [
        (None, "null"),
        (
            {"testkey": 1, "testkey2": "asdf", "testkey3": [1, 2, 3]},
            '{"testkey": 1, "testkey2": "asdf", "testkey3": [1, 2, 3]}',
        ),
    ],
    ids=[0, 1],
)
def test_exit(data: str | None, expected: str):
    mock_stdout = MockStream()
    with (
        patch("stashapi.log.sys.stdout", new=mock_stdout),
        patch("stashapi.log.sys.exit"),
    ):
        log.result(data)  # pyright: ignore[reportUnknownMemberType]
        # note: using index 0 here because I guess the call to `print`
        # prints the newline separately from the actual content? this results in
        # two entries being added to the list, so -1 doesn't work here. wack
        assert mock_stdout.written[0] == expected
