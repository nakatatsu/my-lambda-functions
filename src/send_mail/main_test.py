import pytest
from cerberus import Validator

import main


def test_is_email():
    v = Validator({"email": {"check_with": main.is_email}})
    assert v.validate({"email": "test@example.com"})
    assert not v.validate({"email": "testexample.com"})


def test_validate_inquiry_request():
    main.validate_inquiry_request(
        {"name": "田中太郎" * 10, "email": "test@example.com", "title": "タイトル" * 20, "message": "内容内容内容内容内容" * 1000}
    )

    with pytest.raises(TypeError, match=r".*max length is 40.*"):
        main.validate_inquiry_request(
            {"name": "田中太郎" * 11, "email": "test@example.com", "title": "タイトル" * 20, "message": "内容内容内容内容内容" * 1000}
        )
