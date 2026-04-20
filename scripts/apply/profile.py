"""Profile loader and validator for GAJ ATS autofill.

Mirrors scripts/lib/profile-schema.ts (the canonical spec) and
scripts/lib/profile-path.ts (precedence resolver). The TypeScript side
is the source of truth; this Python side parses the YAML the TS migrator
writes.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


WorkAuthStatus = Literal[
    "us_citizen",
    "permanent_resident",
    "visa_holder",
    "needs_sponsorship",
]

EmploymentStatus = Literal["employed", "unemployed", "freelance"]

LocationPreference = Literal["remote", "hybrid", "onsite"]

EeocGender = Literal["male", "female", "non_binary", "decline_to_state"]

EeocEthnicity = Literal[
    "white",
    "black_or_african_american",
    "hispanic_or_latino",
    "asian",
    "native_american",
    "pacific_islander",
    "two_or_more",
    "decline_to_state",
]

EeocVeteranStatus = Literal[
    "protected_veteran",
    "not_a_veteran",
    "decline_to_state",
]

EeocDisabilityStatus = Literal["yes", "no", "decline_to_state"]


WORK_AUTH_VALUES: tuple[str, ...] = (
    "us_citizen",
    "permanent_resident",
    "visa_holder",
    "needs_sponsorship",
)

EMPLOYMENT_VALUES: tuple[str, ...] = ("employed", "unemployed", "freelance")


@dataclass
class Identity:
    full_name: str = ""
    preferred_name: str = ""
    email: str = ""
    phone: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    pronouns: str | None = None


@dataclass
class Address:
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


@dataclass
class WorkAuth:
    status: WorkAuthStatus = "us_citizen"
    sponsorship_required_now: bool = False
    sponsorship_required_future: bool = False


@dataclass
class Relocation:
    willing_to_relocate: bool = False
    preferred_locations: list[str] = field(default_factory=list)
    current_location_preference: LocationPreference = "remote"


@dataclass
class Employment:
    current_status: EmploymentStatus = "employed"
    notice_period_days: int = 14
    earliest_start_date: str = ""


@dataclass
class ResumeVariant:
    key: str
    label: str
    path: str
    use_when: str


@dataclass
class Resume:
    variants: list[ResumeVariant] = field(default_factory=list)


@dataclass
class EeocVoluntary:
    gender: EeocGender = "decline_to_state"
    ethnicity: EeocEthnicity = "decline_to_state"
    veteran_status: EeocVeteranStatus = "decline_to_state"
    disability_status: EeocDisabilityStatus = "decline_to_state"


@dataclass
class Profile:
    identity: Identity = field(default_factory=Identity)
    address: Address = field(default_factory=Address)
    work_auth: WorkAuth = field(default_factory=WorkAuth)
    relocation: Relocation = field(default_factory=Relocation)
    employment: Employment = field(default_factory=Employment)
    resume: Resume = field(default_factory=Resume)
    eeoc_voluntary: EeocVoluntary = field(default_factory=EeocVoluntary)
    target_roles: list[str] = field(default_factory=list)
    employment_types: list[str] = field(default_factory=list)


class ProfileValidationError(Exception):
    """Raised by load_profile when the on-disk YAML fails validation."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


DEFAULT_GAJ_DIR = Path.home() / "gaj"
DEFAULT_CONTEXT_DIR = DEFAULT_GAJ_DIR / "context"
DEFAULT_PROFILE_PATH = DEFAULT_CONTEXT_DIR / "profile.yaml"
CONFIG_PATH = DEFAULT_GAJ_DIR / "config.yaml"


def resolve_profile_path() -> str:
    """Resolve profile.yaml path: env > config.yaml > default.

    Mirrors scripts/lib/profile-path.ts::resolveProfilePath.
    """
    env = os.environ.get("GAJ_PROFILE_PATH", "").strip()
    if env:
        return env

    if CONFIG_PATH.exists():
        try:
            parsed = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                configured = parsed.get("profile_path")
                if isinstance(configured, str) and configured.strip():
                    return configured.strip()
        except yaml.YAMLError:
            pass

    return str(DEFAULT_PROFILE_PATH)


def validate_profile(obj: object) -> tuple[bool, list[str]]:
    """Return (ok, errors). Mirrors validateProfile() in profile-schema.ts.

    Required fields enforced:
      identity.full_name, identity.email (must include @), identity.phone
      work_auth.status in WORK_AUTH_VALUES
      address.country
      resume.variants length >= 1
      employment.current_status in EMPLOYMENT_VALUES (only checked when
      employment is present, matching the TS branch)
    """
    errors: list[str] = []
    if not isinstance(obj, dict):
        return False, ["root: not an object"]

    identity = obj.get("identity") if isinstance(obj.get("identity"), dict) else None
    if not identity:
        errors.append("identity: missing")
    else:
        full_name = identity.get("full_name")
        if not isinstance(full_name, str) or full_name.strip() == "":
            errors.append("identity.full_name: missing")
        email = identity.get("email")
        if not isinstance(email, str) or email.strip() == "":
            errors.append("identity.email: missing")
        elif "@" not in email:
            errors.append("identity.email: invalid shape (no @)")
        phone = identity.get("phone")
        if not isinstance(phone, str) or phone.strip() == "":
            errors.append("identity.phone: missing")

    work_auth = obj.get("work_auth") if isinstance(obj.get("work_auth"), dict) else None
    if not work_auth:
        errors.append("work_auth: missing")
    else:
        status = work_auth.get("status")
        if not isinstance(status, str) or status not in WORK_AUTH_VALUES:
            errors.append(f'work_auth.status: invalid enum value "{status}"')

    address = obj.get("address") if isinstance(obj.get("address"), dict) else None
    if not address:
        errors.append("address: missing")
    else:
        country = address.get("country")
        if not isinstance(country, str) or country.strip() == "":
            errors.append("address.country: missing")

    resume = obj.get("resume") if isinstance(obj.get("resume"), dict) else None
    if not resume:
        errors.append("resume: missing")
    else:
        variants = resume.get("variants")
        if not isinstance(variants, list) or len(variants) == 0:
            errors.append("resume.variants: must contain at least one variant")

    employment = obj.get("employment") if isinstance(obj.get("employment"), dict) else None
    if employment:
        current = employment.get("current_status")
        if not isinstance(current, str) or current not in EMPLOYMENT_VALUES:
            errors.append(
                f'employment.current_status: invalid enum value "{current}"'
            )

    return (len(errors) == 0), errors


def _dataclass_from_dict(obj: dict) -> Profile:
    """Build a Profile dataclass from a validated dict."""

    def _dict(key: str) -> dict:
        v = obj.get(key)
        return v if isinstance(v, dict) else {}

    def _list(v: object) -> list:
        return v if isinstance(v, list) else []

    identity_d = _dict("identity")
    address_d = _dict("address")
    work_auth_d = _dict("work_auth")
    relocation_d = _dict("relocation")
    employment_d = _dict("employment")
    resume_d = _dict("resume")
    eeoc_d = _dict("eeoc_voluntary")

    identity = Identity(
        full_name=str(identity_d.get("full_name", "")),
        preferred_name=str(identity_d.get("preferred_name", "")),
        email=str(identity_d.get("email", "")),
        phone=str(identity_d.get("phone", "")),
        linkedin_url=str(identity_d.get("linkedin_url", "")),
        github_url=str(identity_d.get("github_url", "")),
        portfolio_url=str(identity_d.get("portfolio_url", "")),
        pronouns=identity_d.get("pronouns"),
    )
    address = Address(
        city=str(address_d.get("city", "")),
        state=str(address_d.get("state", "")),
        postal_code=str(address_d.get("postal_code", "")),
        country=str(address_d.get("country", "US")),
    )
    work_auth = WorkAuth(
        status=work_auth_d.get("status", "us_citizen"),
        sponsorship_required_now=bool(work_auth_d.get("sponsorship_required_now", False)),
        sponsorship_required_future=bool(work_auth_d.get("sponsorship_required_future", False)),
    )
    relocation = Relocation(
        willing_to_relocate=bool(relocation_d.get("willing_to_relocate", False)),
        preferred_locations=[str(x) for x in _list(relocation_d.get("preferred_locations"))],
        current_location_preference=relocation_d.get("current_location_preference", "remote"),
    )
    employment = Employment(
        current_status=employment_d.get("current_status", "employed"),
        notice_period_days=int(employment_d.get("notice_period_days", 14)),
        earliest_start_date=str(employment_d.get("earliest_start_date", "")),
    )
    variants = [
        ResumeVariant(
            key=str(v.get("key", "")),
            label=str(v.get("label", "")),
            path=str(v.get("path", "")),
            use_when=str(v.get("use_when", "")),
        )
        for v in _list(resume_d.get("variants"))
        if isinstance(v, dict)
    ]
    resume = Resume(variants=variants)
    eeoc = EeocVoluntary(
        gender=eeoc_d.get("gender", "decline_to_state"),
        ethnicity=eeoc_d.get("ethnicity", "decline_to_state"),
        veteran_status=eeoc_d.get("veteran_status", "decline_to_state"),
        disability_status=eeoc_d.get("disability_status", "decline_to_state"),
    )
    return Profile(
        identity=identity,
        address=address,
        work_auth=work_auth,
        relocation=relocation,
        employment=employment,
        resume=resume,
        eeoc_voluntary=eeoc,
        target_roles=[str(x) for x in _list(obj.get("target_roles"))],
        employment_types=[str(x) for x in _list(obj.get("employment_types"))],
    )


def load_profile(path: str | None = None) -> Profile:
    """Load and validate a profile from YAML. Raises ProfileValidationError on failure."""
    resolved = path if path else resolve_profile_path()
    raw = Path(resolved).read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    ok, errors = validate_profile(data)
    if not ok:
        raise ProfileValidationError(errors)
    return _dataclass_from_dict(data)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.apply.profile",
        description="Validate a GAJ profile.yaml against the canonical schema.",
    )
    parser.add_argument("--validate", action="store_true", help="Validate the resolved profile.")
    parser.add_argument("--path", type=str, default=None, help="Override resolved profile path.")
    args = parser.parse_args(argv)

    if not args.validate:
        parser.print_help()
        return 0

    resolved = args.path if args.path else resolve_profile_path()
    try:
        raw = Path(resolved).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"profile not found: {resolved}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"profile read failed: {exc}", file=sys.stderr)
        return 1

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        print(f"profile YAML parse error: {exc}", file=sys.stderr)
        return 1

    ok, errors = validate_profile(data)
    if ok:
        print("ok")
        return 0
    for err in errors:
        print(err, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(_main())
