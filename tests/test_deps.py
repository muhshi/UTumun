def test_required_packages_installed():
    import fastapi
    import uvicorn
    import pydantic
    import httpx
    import pypdf
    assert fastapi.__name__ == "fastapi"
    assert uvicorn.__name__ == "uvicorn"
    assert pydantic.__name__ == "pydantic"
    assert httpx.__name__ == "httpx"
    assert pypdf.__name__ == "pypdf"
