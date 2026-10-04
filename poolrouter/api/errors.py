from fastapi.responses import JSONResponse

from poolrouter.runtime.errors import ProviderFailure


def error_response(failure: ProviderFailure, *, exhausted: bool = False) -> JSONResponse:
    if exhausted:
        return JSONResponse(status_code=503, content={"error": {
            "code": "FREE_POOL_EXHAUSTED",
            "message": "No eligible zero-cost deployment is currently available.",
        }})
    return JSONResponse(status_code=failure.http_status or 502,
                         content={"error": failure.as_dict()})
