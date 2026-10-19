import sys
import pytest

def test_python_version():
    """Verify Python runtime version is at least 3.11."""
    assert sys.version_info >= (3, 11), f"Python 3.11+ required, current is {sys.version}"

def test_package_imports():
    """Verify that all core ReqVerify dependencies can be imported cleanly."""
    import anthropic
    import langgraph
    import playwright
    import pydantic
    import pytest
    import jinja2
    import yaml
    import pypdf
    import numpy
    import pandas
    import scipy
    import sklearn

    assert hasattr(anthropic, "Anthropic")
    assert hasattr(pydantic, "BaseModel")
