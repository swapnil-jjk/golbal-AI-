const answerInput = document.querySelector('#answer-input');
const checkButton = document.querySelector('#check-button');
const charCount = document.querySelector('#char-count');
const statusPanel = document.querySelector('#status-panel');
const statusText = document.querySelector('#status-text');
const errorPanel = document.querySelector('#error-panel');
const report = document.querySelector('#report');
const claimList = document.querySelector('#claim-list');

const scoreFor = { Verified: 100, 'Potentially outdated': 50, Conflicting: 0, 'Unable to verify': 25 };

answerInput.addEventListener('input', () => {
  charCount.textContent = `${answerInput.value.length.toLocaleString()} characters`;
});

function statusClass(status) {
  if (status === 'Verified') return 'status-good';
  if (status === 'Potentially outdated' || status === 'Conflicting') return 'status-warn';
  return 'status-neutral';
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

function renderClaims(results) {
  claimList.innerHTML = results.map((item, index) => {
    const status = item.status || 'Unable to verify';
    const sources = item.sources || [];
    const sourceHtml = sources.length ? sources.map((source) => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">↗ ${escapeHtml(source.title || 'Open source')}</a>`).join('') : '<span class="source-count">No current source evidence found</span>';
    return `<article class="claim-card"><div class="claim-top"><p class="claim-text"><span class="source-count">${String(index + 1).padStart(2, '0')} · CLAIM</span><br>${escapeHtml(item.claim)}</p><span class="status ${statusClass(status)}">${escapeHtml(status)}</span></div><div class="claim-score">${item.freshness_score ?? scoreFor[status] ?? 25}<small> / 100 freshness</small></div><p class="claim-detail"><strong>Why this result:</strong> ${escapeHtml(item.explanation || '')}<br><strong>Freshness note:</strong> ${escapeHtml(item.freshness_note || '')}</p><div class="source-list"><span class="source-count">${sources.length} evidence source${sources.length === 1 ? '' : 's'}</span>${sourceHtml}</div></article>`;
  }).join('');
}

function showError(message) {
  errorPanel.textContent = message;
  errorPanel.classList.remove('hidden');
}

checkButton.addEventListener('click', async () => {
  const answer = answerInput.value.trim();
  if (!answer) { showError('Please enter an answer first.'); return; }
  checkButton.disabled = true;
  report.classList.add('hidden'); errorPanel.classList.add('hidden'); statusPanel.classList.remove('hidden');
  statusText.textContent = 'Extracting claims, researching sources, and verifying evidence...';
  try {
    const response = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ answer }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Verification failed.');
    const results = payload.results || [];
    const verified = results.filter((item) => item.status === 'Verified').length;
    const needsReview = results.filter((item) => item.status === 'Potentially outdated' || item.status === 'Conflicting').length;
    document.querySelector('#score-value').textContent = `${payload.score} / 100`;
    document.querySelector('#claims-value').textContent = payload.claims_checked;
    document.querySelector('#verified-value').textContent = verified;
    document.querySelector('#review-value').textContent = needsReview;
    document.querySelector('#progress-bar').style.width = `${payload.score}%`;
    renderClaims(results); report.classList.remove('hidden'); statusPanel.classList.add('hidden'); report.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) { statusPanel.classList.add('hidden'); showError(error.message); }
  finally { checkButton.disabled = false; }
});

