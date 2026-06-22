from __future__ import annotations

import re

from rapidfuzz import fuzz

from app.verification.models import ApplicationData, ExtractedLabel, FieldResult, VerificationResult


FUZZY_THRESHOLD = 90.0
ML_PER_FLUID_OUNCE = 29.5735295625

_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]", re.ASCII)
_WHITESPACE_PATTERN = re.compile(r"\s+")
_NUMBER_PATTERN = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)")

_COUNTRY_SYNONYMS = {
    "usa": "united states",
    "us": "united states",
    "u s a": "united states",
    "u s": "united states",
    "united states": "united states",
    "united states of america": "united states",
    "uk": "united kingdom",
    "u k": "united kingdom",
    "great britain": "united kingdom",
    "united kingdom": "united kingdom",
}

_UNIT_TO_ML = {
    "ml": 1.0,
    "milliliter": 1.0,
    "milliliters": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "liters": 1000.0,
    "cl": 10.0,
    "centiliter": 10.0,
    "centiliters": 10.0,
    "fl oz": ML_PER_FLUID_OUNCE,
    "fluid ounce": ML_PER_FLUID_OUNCE,
    "fluid ounces": ML_PER_FLUID_OUNCE,
}


def _collapse_whitespace(value: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", value.strip())


def _normalize_fuzzy(value: str) -> str:
    without_punctuation = _PUNCTUATION_PATTERN.sub(" ", value)
    normalized = _collapse_whitespace(without_punctuation).lower()
    return (
        normalized.replace("l l c", "llc")
        .replace("l t d", "ltd")
        .replace("i n c", "inc")
    )


def _normalize_country(value: str) -> str:
    normalized = _normalize_fuzzy(value)
    return _COUNTRY_SYNONYMS.get(normalized, normalized)


def _token_sort_ratio(application: str, extracted: str) -> float:
    return float(fuzz.token_sort_ratio(application, extracted))


def _missing_result(field: str, application: str, strategy: str) -> FieldResult:
    return FieldResult(
        field=field,
        status="FAIL",
        application_value=application,
        extracted_value=None,
        strategy=strategy,
        message="Extracted value is missing.",
    )


def _compare_fuzzy(field: str, application: str, extracted: str | None) -> FieldResult:
    strategy = "fuzzy_token_sort_ratio"
    if extracted is None:
        return _missing_result(field, application, strategy)

    normalized_application = _normalize_fuzzy(application)
    normalized_extracted = _normalize_fuzzy(extracted)
    score = _token_sort_ratio(normalized_application, normalized_extracted)
    status = "PASS" if score >= FUZZY_THRESHOLD else "FAIL"

    return FieldResult(
        field=field,
        status=status,
        application_value=application,
        extracted_value=extracted,
        strategy=strategy,
        score=score,
        normalized_application_value=normalized_application,
        normalized_extracted_value=normalized_extracted,
        message="Fuzzy match passed." if status == "PASS" else "Fuzzy match failed.",
    )


def compare_brand_name(application: str, extracted: str | None) -> FieldResult:
    return _compare_fuzzy("brand_name", application, extracted)


def compare_product_class(application: str, extracted: str | None) -> FieldResult:
    return _compare_fuzzy("product_class", application, extracted)


def compare_producer(application: str, extracted: str | None) -> FieldResult:
    return _compare_fuzzy("producer", application, extracted)


def compare_country_of_origin(application: str, extracted: str | None) -> FieldResult:
    strategy = "country_synonym_exact"
    if extracted is None:
        return _missing_result("country_of_origin", application, strategy)

    normalized_application = _normalize_country(application)
    normalized_extracted = _normalize_country(extracted)
    status = "PASS" if normalized_application == normalized_extracted else "FAIL"

    return FieldResult(
        field="country_of_origin",
        status=status,
        application_value=application,
        extracted_value=extracted,
        strategy=strategy,
        normalized_application_value=normalized_application,
        normalized_extracted_value=normalized_extracted,
        message="Country matched." if status == "PASS" else "Country did not match.",
    )


def _parse_abv(value: str) -> float | None:
    normalized = value.lower()
    matches = list(_NUMBER_PATTERN.finditer(normalized))
    if not matches:
        return None

    percent_candidates: list[float] = []
    proof_candidates: list[float] = []
    plain_candidates: list[float] = []

    for match in matches:
        number = float(match.group(1))
        before = normalized[max(0, match.start() - 12) : match.start()]
        after = normalized[match.end() : match.end() + 18]
        context = f"{before} {after}"

        if "proof" in after[:10]:
            proof_candidates.append(number / 2)
        elif "%" in after[:4] or "alc" in context or "vol" in context or "abv" in context:
            percent_candidates.append(number)
        else:
            plain_candidates.append(number)

    if percent_candidates:
        return percent_candidates[0]
    if proof_candidates:
        return proof_candidates[0]
    return plain_candidates[0]


def compare_abv(application: str, extracted: str | None) -> FieldResult:
    strategy = "abv_numeric_tolerance"
    if extracted is None:
        return _missing_result("abv", application, strategy)

    application_abv = _parse_abv(application)
    extracted_abv = _parse_abv(extracted)

    if application_abv is None or extracted_abv is None:
        status = "FAIL"
    else:
        status = "PASS" if abs(application_abv - extracted_abv) <= 0.1 else "FAIL"

    return FieldResult(
        field="abv",
        status=status,
        application_value=application,
        extracted_value=extracted,
        strategy=strategy,
        normalized_application_value=None if application_abv is None else str(application_abv),
        normalized_extracted_value=None if extracted_abv is None else str(extracted_abv),
        message="ABV matched within tolerance." if status == "PASS" else "ABV did not match.",
    )


def _parse_net_contents(value: str) -> float | None:
    normalized = _collapse_whitespace(value.lower().replace(".", " "))
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", ".", normalized)
    unit_pattern = "|".join(
        sorted((re.escape(unit) for unit in _UNIT_TO_ML), key=len, reverse=True)
    )
    match = re.search(rf"(\d+(?:\.\d+)?)\s*({unit_pattern})\b", normalized)
    if not match:
        return None

    amount = float(match.group(1))
    unit = match.group(2)
    return amount * _UNIT_TO_ML[unit]


def compare_net_contents(application: str, extracted: str | None) -> FieldResult:
    strategy = "net_contents_ml_tolerance"
    if extracted is None:
        return _missing_result("net_contents", application, strategy)

    application_ml = _parse_net_contents(application)
    extracted_ml = _parse_net_contents(extracted)

    if application_ml is None or extracted_ml is None:
        status = "FAIL"
    else:
        status = "PASS" if abs(application_ml - extracted_ml) <= 1.0 else "FAIL"

    return FieldResult(
        field="net_contents",
        status=status,
        application_value=application,
        extracted_value=extracted,
        strategy=strategy,
        normalized_application_value=None if application_ml is None else str(application_ml),
        normalized_extracted_value=None if extracted_ml is None else str(extracted_ml),
        message=(
            "Net contents matched within tolerance."
            if status == "PASS"
            else "Net contents did not match."
        ),
    )


def compare_government_warning(application: str, extracted: str | None) -> FieldResult:
    strategy = "exact_case_sensitive"
    if extracted is None:
        return _missing_result("government_warning", application, strategy)

    status = "PASS" if application == extracted else "FAIL"

    return FieldResult(
        field="government_warning",
        status=status,
        application_value=application,
        extracted_value=extracted,
        strategy=strategy,
        message=(
            "Government warning matched exactly."
            if status == "PASS"
            else "Government warning must match exactly."
        ),
    )


def verify_label(application: ApplicationData, extracted: ExtractedLabel) -> VerificationResult:
    fields = [
        compare_brand_name(application.brand_name, extracted.brand_name),
        compare_product_class(application.product_class, extracted.product_class),
        compare_producer(application.producer, extracted.producer),
        compare_country_of_origin(application.country_of_origin, extracted.country_of_origin),
        compare_abv(application.abv, extracted.abv),
        compare_net_contents(application.net_contents, extracted.net_contents),
        compare_government_warning(application.government_warning, extracted.government_warning),
    ]
    verdict = "NEEDS_REVIEW" if any(field.status == "FAIL" for field in fields) else "PASS"
    return VerificationResult(verdict=verdict, fields=fields)
