from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from fpl.client import FPLClient


def make_response(status: int, payload: object = None) -> requests.Response:
    response = MagicMock(spec=requests.Response)
    response.status_code = status
    response.json.return_value = payload
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


def make_client(*responses: requests.Response, delay: float = 0) -> tuple[FPLClient, MagicMock]:
    session = MagicMock()
    session.headers = {}
    session.get.side_effect = list(responses)
    sleeps: list[float] = []
    client = FPLClient(
        base_url="https://fantasy.premierleague.com/api",
        user_agent="test-agent",
        delay=delay,
        max_attempts=3,
        session=session,
        sleep=sleeps.append,
    )
    client.sleeps = sleeps  # type: ignore[attr-defined]
    return client, session


def test_url_adds_trailing_slash() -> None:
    client, _ = make_client()
    assert (
        client.url("bootstrap-static") == "https://fantasy.premierleague.com/api/bootstrap-static/"
    )
    assert client.url("/event/3/live/") == "https://fantasy.premierleague.com/api/event/3/live/"


def test_sets_user_agent() -> None:
    _, session = make_client()
    assert session.headers["User-Agent"] == "test-agent"


def test_retries_on_503_then_succeeds() -> None:
    client, session = make_client(make_response(503), make_response(200, {"ok": True}))
    assert client.get("fixtures/") == {"ok": True}
    assert session.get.call_count == 2


def test_gives_up_after_max_attempts() -> None:
    client, session = make_client(*(make_response(503) for _ in range(3)))
    with pytest.raises(Exception, match="503"):
        client.get("fixtures/")
    assert session.get.call_count == 3


def test_does_not_retry_404() -> None:
    client, session = make_client(make_response(404))
    with pytest.raises(requests.HTTPError):
        client.get("entry/1/event/1/picks/")
    assert session.get.call_count == 1


def test_throttles_between_calls() -> None:
    client, _ = make_client(make_response(200, {}), make_response(200, {}), delay=0.5)
    client.get("a/")
    client.get("b/")
    # First call has nothing to wait for; the second waits out (most of) the delay.
    assert len(client.sleeps) == 1  # type: ignore[attr-defined]
    assert 0 < client.sleeps[0] <= 0.5  # type: ignore[attr-defined]
