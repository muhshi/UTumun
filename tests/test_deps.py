def test_required_packages_installed():
    import fastapi
    import uvicorn
    import pydantic
    assert fastapi.__name__ == "fastapi"
    assert uvicorn.__name__ == "uvicorn"
    assert pydantic.__name__ == "pydantic"
