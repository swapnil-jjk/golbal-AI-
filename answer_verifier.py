import json
import time
from openai import APIStatusError, OpenAIError
from bifrost_client import create_bifrost_client, parse_json_object, response_text

ALLOWED_STATUSES = {"Verified", "Potentially outdated", "Conflicting", "Unable to verify"}
MAX_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (1, 2)
RETRYABLE_STATUS_CODES = {429, 503}


class ClaimVerificationError(RuntimeError):
    """Raised when claim verification cannot complete safely."""


def verify_claim(claim: str, research: dict) -> dict:
    sources, research_error = research.get("sources", []), research.get("error")
    if research_error or not sources:
        return {"claim": claim, "status": "Unable to verify", "explanation": f"Research could not be completed: {research_error}" if research_error else "No source evidence was found for this claim.", "freshness_note": "No current source evidence was available."}
    client, model = create_bifrost_client()
    prompt = f"""You are a factual claim verification assistant.
Original claim: {claim}
Latest web research sources: {json.dumps(sources, ensure_ascii=False)}
Compare the claim with the evidence only. Do not invent facts, sources, dates, or citations. If sources disagree, explain the disagreement. Choose exactly one status: Verified, Potentially outdated, Conflicting, Unable to verify.
Return ONLY valid JSON: {{"claim":"Original claim","status":"Verified","explanation":"Brief explanation based on evidence","freshness_note":"Explain whether the evidence appears current"}}"""
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0)
            break
        except APIStatusError as error:
            if error.status_code not in RETRYABLE_STATUS_CODES:
                raise ClaimVerificationError("Claim verification failed. Check Bifrost availability and model access, then try again.") from error
            if attempt == MAX_ATTEMPTS - 1:
                raise ClaimVerificationError("Claim verification is temporarily unavailable after 3 attempts. Please wait a moment and try again.") from error
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
        except OpenAIError as error:
            raise ClaimVerificationError("Claim verification failed. Check Bifrost availability and model access, then try again.") from error
    data = parse_json_object(response_text(response, "Claim verification"), "Claim verification")
    status = data.get("status")
    if status not in ALLOWED_STATUSES:
        status = "Unable to verify"
    return {"claim": claim, "status": status, "explanation": str(data.get("explanation") or "Review the linked evidence."), "freshness_note": str(data.get("freshness_note") or "The response did not provide a freshness assessment.")}

