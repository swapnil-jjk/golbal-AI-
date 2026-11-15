import time
from openai import APIStatusError, OpenAIError
from bifrost_client import ModelResponseError, create_bifrost_client, parse_json_object, response_text

MAX_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (1, 2)
RETRYABLE_STATUS_CODES = {429, 503}


class ClaimExtractionError(RuntimeError):
    """Raised when claim extraction cannot complete safely."""


def extract_claims(answer: str) -> list[str]:
    client, model = create_bifrost_client()
    prompt = f"""Extract clear, independent, verifiable factual claims from the following answer. Split compound statements into separate claims. Exclude opinions, recommendations, questions, speculation, and rhetorical statements. Do not repeat the same claim.

Return ONLY valid JSON in this format:
{{"claims": ["First factual claim", "Second factual claim"]}}

Answer:
{answer}"""
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0)
            break
        except APIStatusError as error:
            if error.status_code not in RETRYABLE_STATUS_CODES:
                raise ClaimExtractionError("Claim extraction failed. Check Bifrost availability and model access, then try again.") from error
            if attempt == MAX_ATTEMPTS - 1:
                raise ClaimExtractionError("Claim extraction is temporarily unavailable after 3 attempts. Please wait a moment and try again.") from error
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
        except OpenAIError as error:
            raise ClaimExtractionError("Claim extraction failed. Check Bifrost availability and model access, then try again.") from error
    data = parse_json_object(response_text(response, "Claim extraction"), "Claim extraction")
    claims = data.get("claims")
    if not isinstance(claims, list):
        raise ModelResponseError("Claim extraction returned an invalid response: 'claims' must be a list.")
    unique_claims, seen = [], set()
    for claim in claims:
        if isinstance(claim, str):
            normalized = " ".join(claim.split())
            if normalized and normalized.casefold() not in seen:
                seen.add(normalized.casefold())
                unique_claims.append(normalized)
    return unique_claims

