import httpx


class LLMUnavailableError(Exception):
    """The local model endpoint could not complete a request."""


class MemoryStoreError(Exception):
    """The local memory database could not complete a request."""


class ConsentRequired(Exception):
    """Personal information was not stored because the user did not consent."""


class AuthorizationRequired(Exception):
    """A separate OAuth grant is required and was not started automatically."""


class ConfirmationRequired(Exception):
    """An external change was refused because the user did not confirm it."""


def is_llm_unavailable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.HTTPError, OSError, TimeoutError, ConnectionError)):
        return True
    return exc.__class__.__name__ in {
        "ResponseError",
        "ConnectError",
        "ConnectTimeout",
        "ReadTimeout",
        "WriteTimeout",
        "RemoteProtocolError",
    }
