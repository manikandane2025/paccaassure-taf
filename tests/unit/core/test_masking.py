import json
from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated

import pytest
from pydantic import BaseModel, SecretStr

from paccaassure_taf.core.masking import (
    MASK,
    Masker,
    Sensitive,
    SensitiveCategory,
    SensitiveMarker,
    default_masker,
    is_sensitive_field,
)


class Status(StrEnum):
    ACTIVE = "Active"


class Address(BaseModel):
    city: str
    street: Sensitive[str]


class Member(BaseModel):
    member_id: str
    first_name: Sensitive[str]
    dob: Annotated[date, SensitiveMarker(SensitiveCategory.PHI)]
    status: Status
    balance: Decimal
    address: Address
    nicknames: list[str]
    password: SecretStr


@pytest.fixture
def member() -> Member:
    return Member(
        member_id="NWH-M000001",
        first_name="Avery",
        dob=date(1990, 4, 17),
        status=Status.ACTIVE,
        balance=Decimal("12.50"),
        address=Address(city="Springfield", street="742 Evergreen Terrace"),
        nicknames=["Ave"],
        password=SecretStr("pw-Northwind-1"),
    )


def test_sensitive_keeps_the_value_type(member: Member) -> None:
    assert member.first_name == "Avery"
    assert member.dob == date(1990, 4, 17)


def test_masks_sensitive_fields_recursively(member: Member) -> None:
    masked = Masker().mask(member)
    assert masked == {
        "member_id": "NWH-M000001",
        "first_name": MASK,
        "dob": MASK,
        "status": "Active",
        "balance": "12.50",
        "address": {"city": "Springfield", "street": MASK},
        "nicknames": ["Ave"],
        "password": MASK,
    }


def test_masked_output_never_contains_raw_values(member: Member) -> None:
    rendered = json.dumps(Masker().mask(member))
    for raw in ("Avery", "1990-04-17", "742 Evergreen", "pw-Northwind-1"):
        assert raw not in rendered


def test_masking_learns_values_and_scrubs_them_from_free_text(member: Member) -> None:
    masker = Masker()
    masker.mask(member)
    text = "Expected Avery (born 1990-04-17) at 742 Evergreen Terrace, token pw-Northwind-1"
    assert masker.scrub(text) == "Expected *** (born ***) at ***, token ***"


def test_learning_can_be_disabled(member: Member) -> None:
    masker = Masker()
    masker.mask(member, learn=False)
    assert masker.scrub("Avery") == "Avery"


def test_is_sensitive_field() -> None:
    assert is_sensitive_field(Member, "first_name")
    assert is_sensitive_field(Member, "dob")
    assert not is_sensitive_field(Member, "member_id")
    assert not is_sensitive_field(Member, "no_such_field")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ssn 900-12-3456", "ssn ***"),
        ("Authorization: Bearer abcdefgh12345678", "Authorization: ***"),
        ("password=hunter22&user=x", "*** &user=x".replace(" ", "")),
        ("api_key: abc123", "***"),
        ("card 4111-1111-1111-1111 ok", "card *** ok"),
        ("amex 378282246310005", "amex ***"),
        ("mc 5555555555554444", "mc ***"),
        ("run 20260924101500 order 1234567890123", "run 20260924101500 order 1234567890123"),
        ("nothing sensitive here", "nothing sensitive here"),
    ],
)
def test_scrub_patterns(text: str, expected: str) -> None:
    assert Masker().scrub(text) == expected


def test_registered_values_longest_first_and_min_length() -> None:
    masker = Masker(min_value_length=4)
    masker.register("abc")  # too short: ignored
    masker.register("secret")
    masker.register("secret-long")
    assert masker.scrub("abc secret-long secret") == "abc *** ***"


def test_registering_same_value_twice_is_harmless() -> None:
    masker = Masker()
    masker.register("value-1")
    masker.register("value-1")
    assert masker.scrub("value-1") == MASK


def test_mapping_keys_are_masked_case_insensitively() -> None:
    masked = Masker().mask({"Authorization": "Basic xyz", "Cookie": "a=b", "user": "x"})
    assert masked == {"Authorization": MASK, "Cookie": MASK, "user": "x"}


def test_mask_handles_json_edge_types() -> None:
    masker = Masker()
    assert masker.mask(None) is None
    assert masker.mask(True) is True
    assert masker.mask(3.5) == 3.5
    assert masker.mask((1, "a")) == [1, "a"]
    assert masker.mask(frozenset({"x"})) == ["x"]
    assert masker.mask(PurePosixPath("results/run-1")) == "results/run-1"
    rendered = masker.mask(object())
    assert isinstance(rendered, str)
    assert rendered.startswith("<object object")


def test_custom_mask_and_patterns() -> None:
    masker = Masker(patterns=[r"NWH-M\d+"], mask="[redacted]")
    assert masker.scrub("member NWH-M000001") == "member [redacted]"


def test_learns_secret_str_and_numbers() -> None:
    class Payload(BaseModel):
        token: Sensitive[SecretStr]
        pin: Sensitive[int]
        note: Sensitive[str | None] = None

    masker = Masker()
    masker.mask(Payload(token=SecretStr("tok-abcdef"), pin=123456))
    assert masker.scrub("tok-abcdef 123456") == "*** ***"


def test_default_masker_is_shared() -> None:
    assert default_masker() is default_masker()


def test_learned_values_are_bounded_oldest_first() -> None:
    masker = Masker(max_learned_values=2)
    for value in ("value-one", "value-two", "value-three"):
        masker.register(value, pinned=False)
    assert masker.learned_count == 2
    assert masker.scrub("value-one value-two value-three") == "value-one *** ***"


def test_reseeing_a_learned_value_refreshes_it() -> None:
    masker = Masker(max_learned_values=2)
    masker.register("value-one", pinned=False)
    masker.register("value-two", pinned=False)
    masker.register("value-one", pinned=False)  # refresh: value-two is now the oldest
    masker.register("value-three", pinned=False)
    assert masker.scrub("value-one value-two value-three") == "*** value-two ***"


def test_pinned_secrets_are_never_evicted() -> None:
    masker = Masker(max_learned_values=1)
    masker.register("pw-Northwind-pinned")
    for index in range(50):
        masker.register(f"learned-{index:03d}", pinned=False)
    masker.register("pw-Northwind-pinned", pinned=False)  # already pinned: stays pinned
    assert masker.learned_count == 1
    assert masker.scrub("pw-Northwind-pinned learned-049 learned-000") == "*** *** learned-000"


def test_pinning_a_learned_value_moves_it_out_of_the_bounded_set() -> None:
    masker = Masker(max_learned_values=5)
    masker.register("value-one", pinned=False)
    masker.register("value-one")
    assert masker.learned_count == 0
    assert masker.scrub("value-one") == "***"


def test_sensitive_fields_are_learned_evictable_but_secret_str_is_pinned(member: Member) -> None:
    masker = Masker(max_learned_values=1)
    masker.mask(member)  # learns first_name, dob, street (bounded to 1); pins the SecretStr password
    assert masker.learned_count == 1
    assert masker.scrub("pw-Northwind-1") == "***"


def test_configure_can_shrink_the_bound() -> None:
    masker = Masker()
    for index in range(10):
        masker.register(f"learned-{index:03d}", pinned=False)
    masker.configure(max_learned_values=3)
    assert masker.learned_count == 3
    assert masker.scrub("learned-006 learned-007") == "learned-006 ***"
    masker.configure(max_learned_values=0)
    assert masker.scrub("learned-009") == "learned-009"
