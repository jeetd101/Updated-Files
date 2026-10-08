const state = {
  user: null,
  dashboard: null,
  currentAttempt: null,
  currentIndex: 0,
  revisionItems: [],
  autosaveTimer: null,
  structuredOrders: {},
  dragIndex: null,
  pointerDrag: null,
};

const formatLabels = {
  mcq: 'Multiple choice', multiple_select: 'Multiple select', true_false: 'True / False',
  fill_blank: 'Fill in the blank', one_word: 'One-word answer', very_short: 'Very short answer',
  short_answer: 'Short answer', who_said: 'Who said that?', match: 'Match the following',
  sequence: 'Correct sequence', identify_chapter: 'Identify chapter', rapid_fire: 'Rapid fire', general: 'Written answer'
};

const quizQuestionFormats = ['mcq','multiple_select','true_false','fill_blank','one_word','very_short','short_answer','who_said','match','sequence','identify_chapter','rapid_fire','general'];

function selectedQuestionFormats() {
  return [...document.querySelectorAll('.question-type-check:checked')].map(input => input.value);
}

function renderQuestionTypeFilter() {
  const root = byId('questionTypeFilter');
  if (!root) return;
  root.innerHTML = `<div class="question-filter-head"><div><strong>Question types</strong><div class="muted small">Select one or multiple types for this quiz.</div></div><button class="text-button" type="button" id="toggleAllQuestionTypes">Clear all</button></div><div class="question-type-options">${quizQuestionFormats.map(format => `<label class="question-type-option"><input class="question-type-check" type="checkbox" value="${format}"><span>${escapeHtml(formatLabels[format] || format)}</span></label>`).join('')}</div>`;
  root.querySelectorAll('.question-type-check').forEach(input => input.addEventListener('change', updateQuestionTypeSummary));
  byId('toggleAllQuestionTypes')?.addEventListener('click', () => {
    const checks = [...document.querySelectorAll('.question-type-check')];
    const allSelected = checks.every(input => input.checked);
    checks.forEach(input => { input.checked = !allSelected; });
    updateQuestionTypeSummary();
  });
  updateQuestionTypeSummary();
}

function updateQuestionTypeSummary() {
  const selected = selectedQuestionFormats();
  const button = byId('toggleAllQuestionTypes');
  if (button) button.textContent = selected.length === quizQuestionFormats.length ? 'Clear all' : 'Select all';
}

function showStudentView(name) {
  document.querySelectorAll('.student-view').forEach(section => section.classList.add('hidden'));
  const target = byId(`${name}View`);
  if (target) target.classList.remove('hidden');
  document.querySelectorAll('#studentNav button').forEach(button => button.classList.toggle('active', button.dataset.view === name));
  if (name === 'revision') loadRevision();
  if (name === 'results') renderResultsView();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function init() {
  try {
    const me = await api('/api/me');
    if (me.user.role !== 'student') { location.href = '/admin'; return; }
    state.user = me.user;
    byId('welcome').textContent = `Welcome, ${me.user.name.split(' ')[0]}`;
    byId('userName').textContent = me.user.name;
    byId('userEmail').textContent = me.user.email;
    byId('avatar').textContent = me.user.name.slice(0, 1).toUpperCase();
    bindEvents();
    await loadDashboard();
  } catch (_) {
    location.href = '/';
  }
}

function bindEvents() {
  document.querySelectorAll('#studentNav button[data-view]').forEach(button => button.addEventListener('click', () => showStudentView(button.dataset.view)));
  document.querySelectorAll('[data-open-view]').forEach(button => button.addEventListener('click', () => showStudentView(button.dataset.openView)));
  byId('startQuizBtn').addEventListener('click', startQuiz);
  byId('studySelectedBtn').addEventListener('click', reviewSelectedMaterials);
  byId('startRevisionBtn').addEventListener('click', startRevision);
  byId('analyticsFilter').addEventListener('change', renderFilteredAnalytics);
  byId('closeQuizBtn').addEventListener('click', closeQuiz);
  byId('prevBtn').addEventListener('click', () => moveQuestion(-1));
  byId('nextBtn').addEventListener('click', () => moveQuestion(1));
  byId('finishQuizBtn').addEventListener('click', finishQuiz);
  byId('closeMaterialBtn').addEventListener('click', () => byId('materialModal').classList.add('hidden'));
  byId('closeResultBtn').addEventListener('click', () => byId('resultModal').classList.add('hidden'));
}

async function loadDashboard() {
  state.dashboard = await api('/api/dashboard');
  const summary = state.dashboard.summary;
  byId('statAttempts').textContent = summary.total_attempts;
  byId('statAccuracy').textContent = `${summary.accuracy}%`;
  byId('statCorrect').textContent = summary.correct;
  byId('statRevision').textContent = summary.revision_pending;
  byId('revisionNavCount').textContent = summary.revision_pending;
  renderOverviewAnalytics();
  renderCourses();
  renderQuestionTypeFilter();
  renderHistory();
  renderAnalyticsFilter();
  renderFilteredAnalytics();
  renderProfile();
}

function renderOverviewAnalytics() {
  const analytics = state.dashboard.analytics;
  const overall = analytics.overall;
  const donut = byId('overallDonut');
  donut.style.setProperty('--pct', clampPercent(overall.completion_percentage));
  donut.querySelector('span').textContent = `${overall.completion_percentage}%`;
  byId('overallAttempted').textContent = overall.attempted_questions;
  byId('overallRemaining').textContent = overall.remaining_questions;
  byId('overallTotal').textContent = overall.total_questions;

  byId('subjectAnalytics').innerHTML = analytics.subjects.length ? analytics.subjects.map(subject => `
    <div class="analytics-row">
      <div class="analytics-row-head"><strong>${escapeHtml(subject.subject_title)}</strong><span>${subject.completion_percentage}% complete</span></div>
      <div class="dual-progress"><span style="width:${clampPercent(subject.completion_percentage)}%"></span></div>
      <div class="analytics-row-foot"><span>${subject.attempted_questions}/${subject.total_questions} practised</span><span>${subject.accuracy}% accuracy</span></div>
    </div>`).join('') : '<div class="empty-state">No subjects available yet.</div>';

  byId('overviewChapterAnalytics').innerHTML = analytics.chapters.length ? `
    <div class="analytics-table-row analytics-table-head"><span>Subject / Chapter</span><span>Completion</span><span>Accuracy</span><span>Correct / Wrong</span></div>
    ${analytics.chapters.map(chapter => `
      <div class="analytics-table-row">
        <span><small>${escapeHtml(chapter.subject_title)}</small><strong>${escapeHtml(chapter.chapter_title)}</strong></span>
        <span><div class="mini-progress"><i style="width:${clampPercent(chapter.completion_percentage)}%"></i></div><b>${chapter.completion_percentage}%</b></span>
        <span>${chapter.accuracy}%</span>
        <span><em class="success-text">${chapter.correct} ✓</em> <em class="danger-text">${chapter.wrong} ✕</em></span>
      </div>`).join('')}` : '<div class="empty-state">Chapter analytics will appear after questions are published.</div>';
}

function groupChapters() {
  const groups = new Map();
  for (const chapter of state.dashboard.chapters) {
    if (!groups.has(chapter.subject_id)) groups.set(chapter.subject_id, { id: chapter.subject_id, title: chapter.subject_title, chapters: [] });
    groups.get(chapter.subject_id).chapters.push(chapter);
  }
  return [...groups.values()];
}

function renderCourses() {
  const groups = groupChapters();
  byId('courseList').innerHTML = groups.length ? groups.map(subject => `
    <section class="subject-folder">
      <div class="subject-folder-head">
        <div><div class="folder-icon">▤</div><div><h3>${escapeHtml(subject.title)}</h3><span>${subject.chapters.length} chapters</span></div></div>
        <button class="btn btn-secondary btn-small" type="button" onclick="toggleSubject(${subject.id})">Select all</button>
      </div>
      <div class="chapter-list">
        ${subject.chapters.map(chapter => `
          <label class="card chapter-card">
            <input type="checkbox" value="${chapter.id}" data-subject="${subject.id}" class="chapter-check">
            <div class="chapter-no">Chapter ${chapter.chapter_number || '•'}</div>
            <h3>${escapeHtml(chapter.title)}</h3>
            <div class="chapter-meta"><span>${chapter.total_questions} questions</span><span>${chapter.material_count} materials</span></div>
            <button class="text-button" type="button" onclick="event.preventDefault();event.stopPropagation();openMaterials([${chapter.id}])">Study material</button>
          </label>`).join('')}
      </div>
    </section>`).join('') : '<div class="card empty-state">No subjects or chapters have been published yet.</div>';
  document.querySelectorAll('.chapter-check').forEach(input => input.addEventListener('change', updateSelectionSummary));
  updateSelectionSummary();
}

function selectedChapterIds() {
  return [...document.querySelectorAll('.chapter-check:checked')].map(input => Number(input.value));
}

function updateSelectionSummary() {
  const ids = selectedChapterIds();
  const chapters = state.dashboard.chapters.filter(chapter => ids.includes(chapter.id));
  const subjects = new Set(chapters.map(chapter => chapter.subject_title));
  byId('selectedSummary').textContent = ids.length ? `${ids.length} chapter${ids.length > 1 ? 's' : ''} selected from ${subjects.size} subject${subjects.size > 1 ? 's' : ''}` : 'No chapters selected';
  document.querySelectorAll('.chapter-check').forEach(input => {
    input.closest('.chapter-card')?.classList.toggle('selected-card', input.checked);
  });
}

function toggleSubject(subjectId) {
  const inputs = [...document.querySelectorAll(`.chapter-check[data-subject="${subjectId}"]`)];
  const shouldSelect = inputs.some(input => !input.checked);
  inputs.forEach(input => { input.checked = shouldSelect; });
  updateSelectionSummary();
}

async function startQuiz() {
  const ids = selectedChapterIds();
  if (!ids.length) { toast('Select at least one chapter.'); return; }
  const count = Number(byId('questionCount').value) || null;
  const selectedFormats = selectedQuestionFormats();
  if (!selectedFormats.length) { toast('Select at least one question type.'); return; }
  const questionFormats = selectedFormats.length === quizQuestionFormats.length ? [] : selectedFormats;
  const button = byId('startQuizBtn');
  button.disabled = true; button.textContent = 'Starting…';
  try {
    const data = await api('/api/attempts/start', { method: 'POST', body: JSON.stringify({ chapter_ids: ids, question_count: count, question_formats: questionFormats }) });
    if (data.resumed_existing) toast('Your existing pending quiz for these chapters has been resumed.', 'success');
    openAttempt(data.attempt);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    button.disabled = false; button.textContent = 'Start quiz';
  }
}

async function resumeQuiz(id) {
  try {
    const data = await api(`/api/attempts/${id}`);
    openAttempt(data.attempt);
  } catch (err) { toast(err.message, 'error'); }
}

async function startRevision() {
  if (!state.revisionItems.length) { toast('There are no pending revision questions.'); return; }
  const button = byId('startRevisionBtn');
  button.disabled = true; button.textContent = 'Starting…';
  try {
    const data = await api('/api/revision/start', { method: 'POST', body: JSON.stringify({ chapter_ids: [], question_count: null }) });
    openAttempt(data.attempt);
  } catch (err) { toast(err.message, 'error'); }
  finally { button.disabled = false; button.textContent = 'Start revision quiz'; }
}

function openAttempt(attempt) {
  state.currentAttempt = attempt;
  state.currentIndex = 0;
  const firstIncomplete = attempt.questions.findIndex(question => !question.response.completed);
  if (firstIncomplete >= 0) state.currentIndex = firstIncomplete;
  byId('quizModeLabel').textContent = attempt.mode === 'revision' ? 'REVISION QUIZ' : 'ACTIVE QUIZ';
  byId('quizTitle').textContent = attempt.mode === 'revision' ? 'Wrong-answer revision' : 'Chapter practice';
  byId('quizModal').classList.remove('hidden');
  renderQuestion();
}

async function closeQuiz() {
  await flushWrittenAutosave(true);
  byId('quizModal').classList.add('hidden');
  state.currentAttempt = null;
  await loadDashboard();
}

async function moveQuestion(delta) {
  if (!state.currentAttempt) return;
  await flushWrittenAutosave(true);
  state.currentIndex = Math.max(0, Math.min(state.currentAttempt.questions.length - 1, state.currentIndex + delta));
  renderQuestion();
}

function inputForWritten(question, response) {
  const value = escapeHtml(response.user_answer || '');
  const singleLine = ['fill_blank', 'one_word', 'rapid_fire'].includes(question.question_format);
  const control = singleLine
    ? `<input id="writtenAnswer" class="input written-control" value="${value}" placeholder="Write your answer…" oninput="scheduleWrittenAutosave()" onblur="flushWrittenAutosave(false)">`
    : `<textarea id="writtenAnswer" class="input written-control" placeholder="Write your answer here…" oninput="scheduleWrittenAutosave()" onblur="flushWrittenAutosave(false)">${value}</textarea>`;
  return `<div class="written-input-wrap">${control}<button class="mic-btn" type="button" onclick="startDictation()" title="Voice typing"><span>🎙</span><b>Mic</b></button></div><div id="autosaveStatus" class="autosave-status">Auto save is on</div>`;
}

function updateQuizProgress() {
  const attempt = state.currentAttempt;
  if (!attempt) return;
  const completed = attempt.questions.filter(item => item.response.completed).length;
  const correct = attempt.questions.filter(item => item.response.is_correct === true).length;
  const wrong = attempt.questions.filter(item => item.response.is_correct === false).length;
  const percent = Math.round(completed / attempt.questions.length * 100);
  byId('quizProgress').style.width = `${percent}%`;
  byId('quizStats').textContent = `${completed} attempted · ${attempt.questions.length - completed} remaining · ${correct} correct · ${wrong} wrong · ${percent}% complete`;
}

function sequenceItemsFromQuestion(question) {
  const lines = String(question.question_text || '').split(/\n+/).map(v => v.trim()).filter(Boolean);
  const tableItems = lines.map(line => line.split('|').map(v => v.trim())).filter(parts => parts.length >= 2 && /^[0-9૦-૯]+$/.test(parts[0])).map(parts => parts[1]);
  if (tableItems.length >= 2) return tableItems;
  let items = lines.filter(line => /^\s*[•·▪◦-]?\s*\(?(?:\d+|[૦-૯]+|[A-Za-z])\)?\s*[.)\-:–—]/.test(line));
  if (items.length < 2) items = lines.filter(line => !/arrange|sequence|ક્રમ/i.test(line));
  return items.map(line => line.replace(/^\s*[•·▪◦-]?\s*\(?(?:\d+|[૦-૯]+|[A-Za-z])\)?\s*[.)\-:–—]\s*/, '').trim()).filter(Boolean);
}

function structuredPromptText(question) {
  const lines = String(question.question_text || '').split(/\n+/).map(v => v.trim()).filter(Boolean);
  if (question.question_format === 'match') {
    const prompt = lines.filter(line => !line.includes('|') && !/^match the following items[.]?$/i.test(line));
    return prompt.join('\n') || 'Match the following';
  }
  if (question.question_format === 'sequence') {
    const prompt = lines.filter(line => {
      if (line.includes('|')) return false;
      if (/^\s*[•·▪◦-]?\s*\(?(?:\d+|[૦-૯]+|[A-Za-z])\)?\s*[.)\-:–—]/.test(line)) return false;
      return true;
    });
    return prompt.join('\n') || 'Arrange the following items in the correct sequence';
  }
  return question.question_text || '';
}

function matchRowsFromQuestion(question) {
  const rows = [];
  const lines = String(question.question_text || '').split(/\n+/).map(v => v.trim()).filter(Boolean);
  const isHeader = (left, right) => {
    const value = `${left} ${right}`.toLowerCase();
    return /ભાગ\s*a|part\s*a|column\s*a|ભાગ\s*b|part\s*b|column\s*b/.test(value);
  };
  for (const line of lines) {
    let parts = line.includes('|')
      ? line.split('|').map(v => v.trim()).filter(v => v.length)
      : line.includes('\t')
        ? line.split('\t').map(v => v.trim()).filter(v => v.length)
        : [];
    if (parts.length < 2) {
      const m = line.match(/^\s*([0-9૦-૯]+)\s*[.)\-:]?\s*(.*?)\s+[-–—]\s*([A-Za-z])\s*[.)\-:]?\s*(.+)$/);
      if (m) parts = [`${m[1]}. ${m[2]}`, `${m[3]}. ${m[4]}`];
    }
    if (parts.length < 2 || isHeader(parts[0], parts[1])) continue;

    const left = parts[0].match(/^\s*([0-9૦-૯]+)\s*[.)\-:]?\s*(.*)$/);
    const right = parts[1].match(/^\s*([A-Za-z])\s*[.)\-:]\s*(.*)$/);
    const index = rows.length;
    const leftKey = left ? left[1] : String(index + 1);
    const leftText = (left ? left[2] : parts[0]).trim();
    const rightKey = right ? right[1].toUpperCase() : String.fromCharCode(65 + index);
    const rightText = (right ? right[2] : parts[1]).trim();
    if (leftText && rightText) rows.push({ leftKey, leftText, rightKey, rightText });
  }
  return rows;
}

function shuffledStructured(items) {
  const copy = items.map(item => typeof item === 'object' ? { ...item } : item);
  if (copy.length < 2) return copy;
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  const same = copy.every((item, i) => {
    const original = items[i];
    return typeof item === 'object' ? item.key === original.key : item === original;
  });
  if (same) copy.push(copy.shift());
  return copy;
}

function initStructuredOrder(question) {
  if (state.structuredOrders[question.id]) return state.structuredOrders[question.id];
  if (question.response?.user_answer) {
    try {
      const parsed = JSON.parse(question.response.user_answer);
      if (Array.isArray(parsed)) {
        if (question.question_format === 'match') {
          const rows = matchRowsFromQuestion(question);
          const rights = rows.map(row => ({ key: row.rightKey, text: row.rightText }));
          state.structuredOrders[question.id] = parsed.map(key => rights.find(r => r.key === key)).filter(Boolean);
        } else {
          state.structuredOrders[question.id] = parsed.map(String);
        }
        return state.structuredOrders[question.id];
      }
    } catch (_) {}
  }
  if (question.question_format === 'match') {
    state.structuredOrders[question.id] = shuffledStructured(matchRowsFromQuestion(question).map(row => ({ key: row.rightKey, text: row.rightText })));
  } else {
    state.structuredOrders[question.id] = shuffledStructured(sequenceItemsFromQuestion(question));
  }
  return state.structuredOrders[question.id];
}

function structuredMove(index, delta) {
  const question = state.currentAttempt.questions[state.currentIndex];
  if (question.response.is_correct !== null) return;
  const order = initStructuredOrder(question);
  const target = index + delta;
  if (target < 0 || target >= order.length) return;
  [order[index], order[target]] = [order[target], order[index]];
  renderQuestion();
}

function structuredDragStart(index) { state.dragIndex = index; }
function structuredAllowDrop(event) { event.preventDefault(); }
function structuredDrop(event, index) {
  event.preventDefault();
  const question = state.currentAttempt.questions[state.currentIndex];
  if (question.response.is_correct !== null || state.dragIndex === null || state.dragIndex === index) return;
  const order = initStructuredOrder(question);
  const [item] = order.splice(state.dragIndex, 1);
  order.splice(index, 0, item);
  state.dragIndex = null;
  renderQuestion();
}

function structuredPointerStart(event, index) {
  const question = state.currentAttempt?.questions[state.currentIndex];
  if (!question || question.response.is_correct !== null) return;
  state.pointerDrag = { index, pointerId: event.pointerId };
  event.currentTarget.closest('[data-structured-index]')?.classList.add('dragging');
  try { event.currentTarget.setPointerCapture(event.pointerId); } catch (_) {}
  event.preventDefault();
}

function structuredPointerEnd(event, fallbackIndex) {
  if (!state.pointerDrag) return;
  const question = state.currentAttempt?.questions[state.currentIndex];
  const source = state.pointerDrag.index;
  const targetNode = document.elementFromPoint(event.clientX, event.clientY)?.closest('[data-structured-index]');
  const target = targetNode ? Number(targetNode.dataset.structuredIndex) : fallbackIndex;
  document.querySelectorAll('.structured-card.dragging').forEach(el => el.classList.remove('dragging'));
  state.pointerDrag = null;
  if (!question || question.response.is_correct !== null || !Number.isInteger(target) || target === source) return;
  const order = initStructuredOrder(question);
  if (target < 0 || target >= order.length) return;
  const [item] = order.splice(source, 1);
  order.splice(target, 0, item);
  renderQuestion();
}

function renderStructuredQuestion(question, response) {
  const order = initStructuredOrder(question);
  const locked = response.is_correct !== null;
  if (question.question_format === 'sequence') {
    if (order.length < 2) return `<div class="feedback error">Sequence items could not be detected from this question format. Please ask the admin to review this question.</div>`;
    return `<div class="structured-help"><strong>Arrange in Correct Sequence</strong><span>Drag every box, or use ↑ ↓, until the order is correct.</span></div>
      <div class="sequence-board">${order.map((item, index) => `<div class="structured-card sequence-card sequence-color-${index % 4}" data-structured-index="${index}" draggable="${locked ? 'false' : 'true'}" ondragstart="structuredDragStart(${index})" ondragover="structuredAllowDrop(event)" ondrop="structuredDrop(event,${index})"><div class="sequence-card-top"><span class="sequence-number">${index + 1}</span><button class="drag-handle" type="button" aria-label="Drag item" onpointerdown="structuredPointerStart(event,${index})" onpointerup="structuredPointerEnd(event,${index})" ${locked ? 'disabled' : ''}>⋮⋮</button></div><strong>${escapeHtml(item)}</strong><div class="sort-actions"><button type="button" onclick="structuredMove(${index},-1)" ${locked || index === 0 ? 'disabled' : ''}>↑</button><button type="button" onclick="structuredMove(${index},1)" ${locked || index === order.length - 1 ? 'disabled' : ''}>↓</button></div></div>`).join('')}</div>
      ${locked ? `<div class="feedback ${response.is_correct ? 'success' : 'error'}">${response.is_correct ? '✓ Correct sequence' : '✕ Wrong sequence. Added to Revision.'}</div><div class="answer-box"><strong>Correct answer from question bank:</strong><br>${escapeHtml(question.correct_answer || '')}</div>` : '<button class="btn btn-primary structured-verify" type="button" onclick="verifyStructuredAnswer()">Verify sequence</button>'}`;
  }

  const rows = matchRowsFromQuestion(question);
  if (rows.length < 2 || order.length !== rows.length) return `<div class="feedback error">Matching columns could not be detected. Keep Part A and Part B in a two-column Word table.</div>`;
  return `<div class="structured-help"><strong>Match the Following</strong><span>Part A stays fixed. Move only Part B up or down to place the correct answer beside each question.</span></div>
    <div class="match-board">
      <div class="match-board-head"><div>Part A</div><div>Part B <span>move this side</span></div></div>
      ${rows.map((row, index) => {
        const item = order[index];
        return `<div class="match-board-row"><div class="match-a-card"><span class="match-row-number">${index + 1}</span><strong>${escapeHtml(row.leftText)}</strong></div><div class="structured-card match-b-card" data-structured-index="${index}" draggable="${locked ? 'false' : 'true'}" ondragstart="structuredDragStart(${index})" ondragover="structuredAllowDrop(event)" ondrop="structuredDrop(event,${index})"><button class="drag-handle" type="button" aria-label="Drag Part B answer" onpointerdown="structuredPointerStart(event,${index})" onpointerup="structuredPointerEnd(event,${index})" ${locked ? 'disabled' : ''}>⋮⋮</button><strong>${escapeHtml(item.text)}</strong><div class="sort-actions"><button type="button" onclick="structuredMove(${index},-1)" ${locked || index === 0 ? 'disabled' : ''}>↑</button><button type="button" onclick="structuredMove(${index},1)" ${locked || index === order.length - 1 ? 'disabled' : ''}>↓</button></div></div></div>`;
      }).join('')}
    </div>
    ${locked ? `<div class="feedback ${response.is_correct ? 'success' : 'error'}">${response.is_correct ? '✓ Correct matching' : '✕ Wrong matching. Added to Revision.'}</div><div class="answer-box"><strong>Correct answer from question bank:</strong><br>${escapeHtml(question.correct_answer || '')}</div>` : '<button class="btn btn-primary structured-verify" type="button" onclick="verifyStructuredAnswer()">Verify matching</button>'}`;
}

function renderQuestion() {
  const attempt = state.currentAttempt;
  if (!attempt || !attempt.questions.length) return;
  const question = attempt.questions[state.currentIndex];
  updateQuizProgress();
  byId('prevBtn').disabled = state.currentIndex === 0;
  byId('nextBtn').disabled = state.currentIndex === attempt.questions.length - 1;

  const response = question.response || { user_answer: '', is_correct: null, answer_viewed: false, completed: false };
  const statusClass = response.is_correct === true ? 'correct' : response.is_correct === false ? 'wrong' : '';
  const displayedQuestionText = ['match', 'sequence'].includes(question.question_format) ? structuredPromptText(question) : question.question_text;
  let body = `<div class="question-card ${statusClass}"><div class="question-topline"><div class="question-meta">${escapeHtml(question.subject_title)} / ${escapeHtml(question.chapter_title)} · Question ${state.currentIndex + 1} of ${attempt.questions.length}</div><span class="badge badge-neutral">${escapeHtml(formatLabels[question.question_format] || question.question_format)}</span></div><div class="question-text">${escapeHtml(displayedQuestionText)}</div>`;

  if (['match', 'sequence'].includes(question.question_format)) {
    body += renderStructuredQuestion(question, response);
  } else if (question.question_type === 'objective') {
    const isMultiple = question.question_format === 'multiple_select';
    const selectedValues = new Set(String(response.user_answer || '').split(',').map(value => value.trim()).filter(Boolean));
    body += `<div class="options-list">${question.options.map(option => {
      const optionValue = String(option.value || option.key);
      const selected = selectedValues.has(optionValue);
      const optionClass = response.is_correct === false && selected ? 'selected-wrong' : response.is_correct === true && selected ? 'selected-correct' : '';
      return `<label class="option ${optionClass}"><input type="${isMultiple ? 'checkbox' : 'radio'}" name="objective" value="${escapeHtml(optionValue)}" ${selected ? 'checked' : ''} ${response.is_correct !== null ? 'disabled' : ''} onchange="objectiveChanged()"><strong>${escapeHtml(option.key)}.</strong><span>${escapeHtml(option.text)}</span>${optionClass === 'selected-correct' ? '<b class="option-sign">✓</b>' : optionClass === 'selected-wrong' ? '<b class="option-sign">✕</b>' : ''}</label>`;
    }).join('')}</div>`;
    if (response.is_correct !== null) {
      body += `<div class="feedback ${response.is_correct ? 'success' : 'error'}">${response.is_correct ? '✓ Correct answer' : '✕ Your answer is wrong and has been added to Revision.'}</div><div class="answer-box"><strong>Correct answer from question bank:</strong><br>${escapeHtml(question.correct_answer || '')}</div>`;
    } else if (isMultiple) {
      body += `<button class="btn btn-primary" type="button" onclick="checkObjective()">Check selected answers</button>`;
    } else {
      body += `<div class="auto-check-note">Select an option. It will be checked automatically.</div>`;
    }
  } else {
    body += inputForWritten(question, response);
    if (response.is_correct !== null) {
      const matchText = Number.isFinite(Number(response.match_percentage)) ? ` · ${response.match_percentage}% word match` : '';
      body += `<div class="feedback ${response.is_correct ? 'success' : 'error'}">${response.is_correct ? '✓ Correct answer' : '✕ Answer is below the 70% word-match level and was added to Revision.'}${matchText}</div>`;
    }
    body += `<div class="written-language-note">Gujarati and English text are supported. Written answers are marked correct at 70% or higher word match with the approved answer.</div><div class="quiz-actions"><button class="btn btn-primary" type="button" onclick="viewWrittenAnswer()">View answer</button></div>`;
    if (response.answer_viewed) {
      body += `<div class="answer-box"><strong>Answer from uploaded question bank</strong><br>${escapeHtml(question.correct_answer || '')}</div><div class="self-review"><span>Compare your answer:</span><button class="btn btn-success" type="button" onclick="markWrittenRevision(false)">I knew this</button><button class="btn btn-danger" type="button" onclick="markWrittenRevision(true)">Keep in revision</button></div>`;
    }
  }
  body += `</div>`;
  byId('questionArea').innerHTML = body;
}

function objectiveChanged() {
  const question = state.currentAttempt.questions[state.currentIndex];
  if (question.question_format !== 'multiple_select') checkObjective();
}

async function checkObjective() {
  const question = state.currentAttempt.questions[state.currentIndex];
  if (question.response.is_correct !== null) return;
  const selected = [...document.querySelectorAll('input[name="objective"]:checked')];
  if (!selected.length) { toast('Please select an answer.'); return; }
  const answer = selected.map(input => input.value).join(',');
  try {
    const data = await api(`/api/attempts/${state.currentAttempt.id}/check`, { method: 'POST', body: JSON.stringify({ question_id: question.id, answer }) });
    question.response.user_answer = answer;
    question.response.is_correct = data.is_correct;
    question.response.completed = true;
    question.correct_answer = data.correct_answer;
    renderQuestion();
    if (!data.is_correct) {
      toast('Wrong answer. It was added to your Revision section.', 'error');
      byId('revisionNavCount').textContent = Number(byId('revisionNavCount').textContent || 0) + 1;
    } else if (state.currentAttempt.mode === 'revision') toast('Correct. This question is now marked as mastered.', 'success');
  } catch (err) { toast(err.message, 'error'); }
}

function scheduleWrittenAutosave() {
  const question = state.currentAttempt?.questions[state.currentIndex];
  const input = byId('writtenAnswer');
  if (!question || !input) return;
  question.response.user_answer = input.value;
  question.response.completed = Boolean(input.value.trim());
  question.response.is_correct = null;
  updateQuizProgress();
  const status = byId('autosaveStatus');
  if (status) status.textContent = 'Saving…';
  clearTimeout(state.autosaveTimer);
  state.autosaveTimer = setTimeout(() => flushWrittenAutosave(false), 650);
}

async function flushWrittenAutosave(finalize = false) {
  clearTimeout(state.autosaveTimer);
  state.autosaveTimer = null;
  const question = state.currentAttempt?.questions[state.currentIndex];
  const input = byId('writtenAnswer');
  if (!question || !input || question.question_type !== 'written' || ['match','sequence'].includes(question.question_format)) return;
  const answer = input.value;
  question.response.user_answer = answer;
  question.response.completed = Boolean(answer.trim());
  try {
    const data = await api(`/api/attempts/${state.currentAttempt.id}/save-written`, { method: 'POST', body: JSON.stringify({ question_id: question.id, answer, finalize }) });
    question.response.completed = data.completed;
    if (finalize && data.is_correct !== null) {
      const previouslyWrong = question.response.is_correct === false;
      question.response.is_correct = data.is_correct;
      question.response.match_percentage = data.match_percentage;
      if (data.added_to_revision && !previouslyWrong) byId('revisionNavCount').textContent = Number(byId('revisionNavCount').textContent || 0) + 1;
    }
    const status = byId('autosaveStatus');
    if (status) status.textContent = 'Saved automatically';
    updateQuizProgress();
  } catch (err) {
    const status = byId('autosaveStatus');
    if (status) status.textContent = 'Auto save failed';
    if (finalize) toast(err.message, 'error');
  }
}

async function viewWrittenAnswer() {
  const question = state.currentAttempt.questions[state.currentIndex];
  const input = byId('writtenAnswer');
  const answer = input ? input.value : (question.response.user_answer || '');
  await flushWrittenAutosave(true);
  try {
    const data = await api(`/api/attempts/${state.currentAttempt.id}/view-answer`, { method: 'POST', body: JSON.stringify({ question_id: question.id, answer }) });
    const wasWrong = question.response.is_correct === false;
    question.response.user_answer = answer;
    question.response.answer_viewed = true;
    question.response.completed = true;
    question.response.is_correct = data.is_correct;
    question.response.match_percentage = data.match_percentage;
    question.correct_answer = data.correct_answer;
    if (data.added_to_revision && !wasWrong) byId('revisionNavCount').textContent = Number(byId('revisionNavCount').textContent || 0) + 1;
    renderQuestion();
  } catch (err) { toast(err.message, 'error'); }
}

async function verifyStructuredAnswer() {
  const question = state.currentAttempt.questions[state.currentIndex];
  const order = initStructuredOrder(question);
  const answer = JSON.stringify(question.question_format === 'match' ? order.map(item => item.key) : order);
  try {
    const data = await api(`/api/attempts/${state.currentAttempt.id}/check-structured`, { method: 'POST', body: JSON.stringify({ question_id: question.id, answer }) });
    question.response.user_answer = answer;
    question.response.is_correct = data.is_correct;
    question.response.completed = true;
    question.correct_answer = data.correct_answer;
    if (!data.is_correct) {
      byId('revisionNavCount').textContent = Number(byId('revisionNavCount').textContent || 0) + 1;
      toast('Wrong answer. It was added to Revision.', 'error');
    } else toast('Correct answer.', 'success');
    renderQuestion();
  } catch (err) { toast(err.message, 'error'); }
}

function startDictation() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) { toast('Voice typing is not supported in this browser. Use Chrome or Edge.', 'error'); return; }
  const input = byId('writtenAnswer');
  if (!input) return;
  const recognition = new SpeechRecognition();
  recognition.lang = /[A-Za-z]/.test(input.value) && !/[\u0A80-\u0AFF]/.test(input.value) ? 'en-IN' : 'gu-IN';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  const mic = document.querySelector('.mic-btn');
  if (mic) mic.classList.add('listening');
  recognition.onresult = event => {
    const spoken = event.results[0][0].transcript || '';
    input.value = `${input.value}${input.value.trim() ? ' ' : ''}${spoken}`;
    scheduleWrittenAutosave();
    input.focus();
  };
  recognition.onerror = () => toast('Voice typing could not start. Check microphone permission.', 'error');
  recognition.onend = () => { if (mic) mic.classList.remove('listening'); };
  recognition.start();
}

async function markWrittenRevision(needsRevision) {
  const question = state.currentAttempt.questions[state.currentIndex];
  try {
    await api('/api/revision/mark', { method: 'POST', body: JSON.stringify({ question_id: question.id, needs_revision: needsRevision }) });
    toast(needsRevision ? 'Question kept in Revision.' : 'Question marked as understood.', needsRevision ? 'error' : 'success');
    if (needsRevision) byId('revisionNavCount').textContent = Number(byId('revisionNavCount').textContent || 0) + 1;
  } catch (err) { toast(err.message, 'error'); }
}

async function finishQuiz() {
  if (!state.currentAttempt) return;
  await flushWrittenAutosave(true);
  try {
    const data = await api(`/api/attempts/${state.currentAttempt.id}/finish`, { method: 'POST' });
    byId('quizModal').classList.add('hidden');
    state.currentAttempt = null;
    renderResult(data.result);
    if (data.result.status === 'completed') toast('Quiz completed. All questions are finished.', 'success');
    else toast(`Quiz saved as pending. ${data.result.remaining} question${data.result.remaining === 1 ? '' : 's'} remaining.`, 'error');
    await loadDashboard();
  } catch (err) { toast(err.message, 'error'); }
}

function renderHistory() {
  const attempts = state.dashboard.attempts;
  byId('historyBody').innerHTML = attempts.length ? attempts.map(attempt => `
    <tr>
      <td data-label="Chapter"><strong>${escapeHtml(attempt.scope_label || 'Quiz')}</strong></td>
      <td data-label="Mode"><span class="badge ${attempt.mode === 'revision' ? 'badge-purple' : 'badge-neutral'}">${escapeHtml(attempt.mode)}</span></td>
      <td data-label="Status"><span class="badge ${attempt.status === 'completed' ? 'badge-success' : 'badge-warning'}">${escapeHtml(attempt.status.replace('_', ' '))}</span></td>
      <td data-label="Complete">${attempt.completion_percentage}%</td>
      <td data-label="Accuracy">${attempt.objective_accuracy}%</td>
      <td data-label="Date & time">${formatDate(attempt.started_at)}</td>
      <td data-label="Action">${['in_progress', 'pending'].includes(attempt.status) ? `<button class="btn btn-secondary btn-small" onclick="resumeQuiz(${attempt.attempt_id})">Resume</button>` : `<button class="btn btn-secondary btn-small" onclick="viewResult(${attempt.attempt_id})">View</button>`}</td>
    </tr>`).join('') : '<tr><td colspan="7" class="muted">No quiz attempts yet.</td></tr>';
}

function renderAnalyticsFilter() {
  const select = byId('analyticsFilter');
  const current = select.value;
  select.innerHTML = '<option value="all">All course</option>' + state.dashboard.analytics.chapters.map(chapter => `<option value="${chapter.chapter_id}">${escapeHtml(chapter.subject_title)} / ${escapeHtml(chapter.chapter_title)}</option>`).join('');
  if ([...select.options].some(option => option.value === current)) select.value = current;
}

function renderFilteredAnalytics() {
  if (!state.dashboard) return;
  const value = byId('analyticsFilter').value;
  let data;
  let title;
  if (value === 'all') {
    data = state.dashboard.analytics.overall;
    title = 'All course';
  } else {
    data = state.dashboard.analytics.chapters.find(chapter => String(chapter.chapter_id) === value) || state.dashboard.analytics.overall;
    title = data.chapter_title || 'All course';
  }
  byId('filteredAnalytics').innerHTML = `
    <div class="card result-metric"><span>Scope</span><strong>${escapeHtml(title)}</strong><small>${data.attempted_questions || 0} of ${data.total_questions || 0} questions practised</small></div>
    <div class="card result-metric"><span>Completion</span><strong>${data.completion_percentage || 0}%</strong><div class="mini-progress large"><i style="width:${clampPercent(data.completion_percentage)}%"></i></div></div>
    <div class="card result-metric"><span>Objective accuracy</span><strong>${data.accuracy || 0}%</strong><small><em class="success-text">${data.correct || 0} correct</em> · <em class="danger-text">${data.wrong || 0} wrong</em></small></div>`;
}

function renderResultsView() {
  renderFilteredAnalytics();
  renderHistory();
}

async function viewResult(attemptId) {
  try {
    const data = await api(`/api/attempts/${attemptId}/result`);
    renderResult(data.result);
  } catch (err) { toast(err.message, 'error'); }
}

function displayReviewAnswer(question) {
  if (!question.user_answer) return 'Not answered';
  if (['match', 'sequence'].includes(question.question_format)) {
    try {
      const values = JSON.parse(question.user_answer);
      return Array.isArray(values) ? values.join(' → ') : question.user_answer;
    } catch (_) { return question.user_answer; }
  }
  return question.user_answer;
}

function renderResult(result) {
  const attempted = result.completed || 0;
  const performance = result.performance_percentage ?? result.objective_accuracy ?? 0;
  byId('resultContent').innerHTML = `
    <div class="result-hero">
      <div class="donut" style="--pct:${clampPercent(performance)}"><span>${performance}%</span></div>
      <div><span class="badge ${result.mode === 'revision' ? 'badge-purple' : 'badge-neutral'}">${escapeHtml(result.mode)}</span><h3>${result.correct} correct · ${result.wrong} wrong</h3><p>Performance is calculated only from attempted/evaluated questions. ${attempted} question${attempted === 1 ? '' : 's'} attempted.</p></div>
    </div>
    <div class="grid grid-4 result-summary-grid"><div><span>Attempted</span><strong>${attempted}</strong></div><div><span>Remaining</span><strong>${result.remaining}</strong></div><div><span>Correct</span><strong class="success-text">${result.correct}</strong></div><div><span>Wrong</span><strong class="danger-text">${result.wrong}</strong></div></div>
    <div class="section-head compact"><h3>Chapter-wise result</h3></div>
    <div class="result-chapters result-chapter-table"><div class="result-chapter result-chapter-head"><span>Chapter</span><span>Attempted</span><span>Performance</span><span>Correct / Wrong</span></div>${result.chapter_results.map(chapter => `<div class="result-chapter"><div><small>${escapeHtml(chapter.subject_title)}</small><strong>${escapeHtml(chapter.chapter_title)}</strong></div><span>${chapter.attempted ?? chapter.completed} attempted</span><span>${chapter.performance_percentage ?? chapter.accuracy}%</span><span>${chapter.correct} ✓ / ${chapter.wrong} ✕</span></div>`).join('')}</div>
    <div class="section-head compact"><h3>Answer review <span class="muted small">(${result.questions.length} attempted only)</span></h3></div>
    <div class="answer-review">${result.questions.length ? result.questions.map((question, index) => `<article class="review-item ${question.is_correct === true ? 'review-correct' : question.is_correct === false ? 'review-wrong' : ''}"><div class="review-heading"><span>${index + 1}. ${escapeHtml(formatLabels[question.question_format] || question.question_format)}</span>${question.is_correct === true ? '<b class="success-text">✓ Correct</b>' : question.is_correct === false ? '<b class="danger-text">✕ Wrong</b>' : '<b class="muted">Attempted</b>'}</div><p>${escapeHtml(question.question_text)}</p><div><small>Your answer</small><div class="review-answer">${escapeHtml(displayReviewAnswer(question))}</div></div><div><small>Question-bank answer</small><div class="review-answer correct-answer">${escapeHtml(question.correct_answer)}</div></div></article>`).join('') : '<div class="empty-state">No questions were attempted.</div>'}</div>`;
  byId('resultModal').classList.remove('hidden');
}

async function loadRevision() {
  try {
    const data = await api('/api/revision');
    state.revisionItems = data.items;
    byId('revisionNavCount').textContent = data.items.length;
    byId('startRevisionBtn').disabled = !data.items.length;
    byId('revisionList').innerHTML = data.items.length ? data.items.map(item => `
      <article class="card revision-card"><div><span class="badge badge-danger">Needs revision</span><h3>${escapeHtml(item.question_text)}</h3><p>${escapeHtml(item.subject_title)} / ${escapeHtml(item.chapter_title)}</p></div><div class="revision-count"><strong>${item.wrong_count}</strong><span>wrong attempt${item.wrong_count > 1 ? 's' : ''}</span></div></article>`).join('') : '<div class="card empty-state"><strong>Revision queue is clear.</strong><span>Wrong answers will automatically appear here.</span></div>';
  } catch (err) { toast(err.message, 'error'); }
}

async function reviewSelectedMaterials() {
  const ids = selectedChapterIds();
  if (!ids.length) { toast('Select at least one chapter first.'); return; }
  await openMaterials(ids);
}

async function openMaterials(ids) {
  try {
    const data = await api(`/api/materials?chapter_ids=${ids.join(',')}`);
    byId('materialContent').innerHTML = data.materials.length ? data.materials.map(material => `<article class="material-article"><div class="material-meta">${escapeHtml(material.subject_title)} / ${escapeHtml(material.chapter_title)}</div><h3>${escapeHtml(material.title)}</h3><div class="material-body">${escapeHtml(material.content)}</div></article>`).join('') : '<div class="empty-state">No course material has been added for the selected chapters.</div>';
    byId('materialModal').classList.remove('hidden');
  } catch (err) { toast(err.message, 'error'); }
}

function renderProfile() {
  const user = state.user;
  const fields = [
    ['Full name', user.name], ['O. Number', user.o_number || '—'], ['Email', user.email],
    ['Mobile', user.mobile || '—'], ['Age', user.age || '—'], ['Date of birth', user.dob || '—'],
    ['City', user.city || '—'], ['Gurukul', user.gurukul_name || '—'], ['Joined', formatDate(user.created_at)]
  ];
  byId('profileCard').innerHTML = fields.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join('');
}

window.toggleSubject = toggleSubject;
window.openMaterials = openMaterials;
window.resumeQuiz = resumeQuiz;
window.viewResult = viewResult;
window.checkObjective = checkObjective;
window.objectiveChanged = objectiveChanged;
window.scheduleWrittenAutosave = scheduleWrittenAutosave;
window.flushWrittenAutosave = flushWrittenAutosave;
window.viewWrittenAnswer = viewWrittenAnswer;
window.verifyStructuredAnswer = verifyStructuredAnswer;
window.structuredMove = structuredMove;
window.structuredDragStart = structuredDragStart;
window.structuredAllowDrop = structuredAllowDrop;
window.structuredDrop = structuredDrop;
window.structuredPointerStart = structuredPointerStart;
window.structuredPointerEnd = structuredPointerEnd;
window.startDictation = startDictation;
window.markWrittenRevision = markWrittenRevision;

init();
