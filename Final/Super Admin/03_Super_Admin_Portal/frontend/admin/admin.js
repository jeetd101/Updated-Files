const adminState = { data: null, students: [], preview: null, materials: [], questions: [], localLoginText: null };
const formatLabels = {
  mcq: 'Multiple choice', multiple_select: 'Multiple select', true_false: 'True / False',
  fill_blank: 'Fill in the blank', one_word: 'One-word answer', very_short: 'Very short answer',
  short_answer: 'Short answer', who_said: 'Who said that?', match: 'Match the following',
  sequence: 'Correct sequence', identify_chapter: 'Identify chapter', rapid_fire: 'Rapid fire', general: 'General'
};


function enhanceResponsiveAdminTables(root = document) {
  root.querySelectorAll('table').forEach(table => {
    table.classList.add('admin-responsive-table');
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
    table.querySelectorAll('tbody tr').forEach(row => {
      Array.from(row.children).forEach((cell, index) => {
        if (cell.tagName === 'TD' && !cell.hasAttribute('data-label')) {
          cell.setAttribute('data-label', headers[index] || '');
        }
      });
    });
  });
}

function watchResponsiveAdminTables() {
  const main = document.querySelector('.main');
  if (!main || typeof MutationObserver === 'undefined') return;
  let frame = 0;
  const observer = new MutationObserver(() => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => enhanceResponsiveAdminTables(main));
  });
  observer.observe(main, { childList: true, subtree: true });
}

function showAdminSection(name) {
  document.querySelectorAll('.admin-section').forEach(section => section.classList.add('hidden'));
  const target = byId(`${name}Section`);
  if (target) target.classList.remove('hidden');
  document.querySelectorAll('#adminNav button').forEach(button => button.classList.toggle('active', button.dataset.section === name));
  if (name === 'students') loadStudents();
  if (name === 'materials') loadMaterials();
  if (name === 'loginPage') loadLocalLoginText();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function init() {
  try {
    const me = await api('/api/me');
    if (me.user.role === 'student') { location.href = '/dashboard'; return; }
    byId('userName').textContent = me.user.name;
    byId('avatar').textContent = me.user.name.slice(0, 1).toUpperCase();
    bindEvents();
    watchResponsiveAdminTables();
    await loadAdmin();
    await loadStudents();
    await loadMaterials();
    await loadLocalLoginText();
    await loadAdminNotifications();
    enhanceResponsiveAdminTables(document);
  } catch (_) { location.href = '/admin-access'; }
}

async function loadAdminNotifications() {
  try {
    const data = await api('/api/admin/notifications');
    (data.notifications || []).forEach(note => toast(`${note.title}: ${note.message}`, note.kind === 'success' ? 'success' : note.kind === 'error' ? 'error' : ''));
  } catch (_) {}
}

function bindEvents() {
  document.querySelectorAll('#adminNav button').forEach(button => button.addEventListener('click', () => showAdminSection(button.dataset.section)));
  byId('subjectForm').addEventListener('submit', createSubject);
  byId('chapterForm').addEventListener('submit', createChapter);
  byId('uploadForm').addEventListener('submit', previewQuestionBank);
  byId('importButton').addEventListener('click', importDetected);
  byId('materialForm').addEventListener('submit', saveMaterial);
  byId('localLoginTextForm').addEventListener('submit', saveLocalLoginText);
  byId('questionFile').addEventListener('change', () => {
    if (byId('questionFile').files.length) { byId('pastedText').value = ''; setUploadStatus(`Selected: ${byId('questionFile').files[0].name}`); }
  });
  byId('pastedText').addEventListener('input', () => {
    if (byId('pastedText').value.trim()) byId('questionFile').value = '';
  });
  byId('materialFile').addEventListener('change', () => {
    if (byId('materialFile').files.length) byId('materialText').value = '';
  });
  byId('materialText').addEventListener('input', () => {
    if (byId('materialText').value.trim()) byId('materialFile').value = '';
  });
  byId('chapterSelect').addEventListener('change', () => loadChapterQuestions());
  byId('refreshQuestionsButton').addEventListener('click', () => loadChapterQuestions());
  byId('adminModalClose').addEventListener('click', closeAdminModal);
  byId('adminModalBackdrop').addEventListener('click', event => { if (event.target === byId('adminModalBackdrop')) closeAdminModal(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeAdminModal(); });
}

async function loadLocalLoginText() {
  const status = byId('loginTextStatus');
  if (status) status.textContent = 'Loading…';
  try {
    const data = await api('/api/admin/local-login-text');
    adminState.localLoginText = data.content || {};
    const fields = {
      brand_title: 'loginTextBrandTitle', brand_subtitle: 'loginTextBrandSubtitle', kicker: 'loginTextKicker',
      hero_title: 'loginTextHeroTitle', hero_description: 'loginTextHeroDescription',
      feature1_title: 'loginTextFeature1Title', feature1_description: 'loginTextFeature1Description',
      feature2_title: 'loginTextFeature2Title', feature2_description: 'loginTextFeature2Description',
      feature3_title: 'loginTextFeature3Title', feature3_description: 'loginTextFeature3Description'
    };
    Object.entries(fields).forEach(([key, id]) => {
      const field = byId(id);
      if (field) field.value = adminState.localLoginText[key] || '';
    });
    if (status) status.textContent = '';
  } catch (err) {
    if (status) status.textContent = err.message;
  }
}

async function saveLocalLoginText(event) {
  event.preventDefault();
  const button = byId('saveLoginTextButton');
  const status = byId('loginTextStatus');
  const payload = Object.fromEntries(new FormData(event.target));
  button.disabled = true;
  button.textContent = 'Saving…';
  if (status) status.textContent = 'Publishing to the Local User login page…';
  try {
    const data = await api('/api/admin/local-login-text', { method: 'PUT', body: JSON.stringify(payload) });
    adminState.localLoginText = data.content || payload;
    if (status) status.textContent = 'Saved. All Local Users will see this text on the login page.';
    toast('Local User login page text updated.', 'success');
  } catch (err) {
    if (status) status.textContent = err.message;
    toast(err.message, 'error');
  } finally {
    button.disabled = false;
    button.textContent = 'Save login page text';
  }
}

async function loadAdmin(preferredChapterId = null) {
  adminState.data = await api('/api/admin/dashboard');
  const stats = adminState.data.stats;
  byId('adminStudents').textContent = stats.students;
  byId('adminSubjects').textContent = stats.subjects;
  byId('adminChapters').textContent = stats.chapters;
  byId('adminQuestions').textContent = stats.questions;

  byId('platformSummary').innerHTML = `
    <div><span>Active students</span><strong>${stats.active_students}</strong></div>
    <div><span>Course materials</span><strong>${stats.materials}</strong></div>
    <div><span>Total quiz attempts</span><strong>${stats.attempts}</strong></div>`;

  byId('recentStudents').innerHTML = adminState.data.recent_students.length ? adminState.data.recent_students.map(student => `
    <tr><td>${escapeHtml(student.name)}</td><td>${escapeHtml(student.o_number || '—')}</td><td>${escapeHtml(student.email)}</td><td>${escapeHtml(student.city || '—')}</td><td>${escapeHtml(student.gurukul_name || '—')}</td><td>${formatDate(student.created_at)}</td></tr>`).join('') : '<tr><td colspan="6" class="muted">No students yet.</td></tr>';

  renderStructure();
  populateSubjectSelects();
  populateChapterSelects(preferredChapterId);
}

function groupedStructure() {
  return adminState.data.subjects.map(subject => ({ ...subject, chapters: adminState.data.chapters.filter(chapter => chapter.subject_id === subject.id) }));
}

function renderStructure() {
  const groups = groupedStructure();
  byId('adminStructureSummary').innerHTML = groups.length ? groups.map(subject => `
    <div class="structure-summary-row"><div><strong>${escapeHtml(subject.title)}</strong><span>${subject.chapter_count} chapters</span></div><span class="badge badge-neutral">${subject.question_count} questions</span></div>`).join('') : '<div class="empty-state">No subject folders yet.</div>';

  byId('structureList').innerHTML = groups.length ? groups.map(subject => `
    <section class="subject-folder">
      <div class="subject-folder-head">
        <div><div class="folder-icon">▤</div><div><h3>${escapeHtml(subject.title)}</h3><span>${escapeHtml(subject.description || 'Subject folder')}</span></div></div>
        <div class="admin-folder-actions"><span class="badge badge-neutral">${subject.question_count} questions</span><button class="btn btn-secondary btn-sm" type="button" onclick="openSubjectEdit(${subject.id})">Edit subject</button></div>
      </div>
      <div class="chapter-list">${subject.chapters.length ? subject.chapters.map(chapter => `
        <article class="card chapter-card admin-chapter-card">
          <div class="chapter-title-row"><div><div class="chapter-no">Chapter ${chapter.chapter_number || '•'}</div><h3>${escapeHtml(chapter.title)}</h3></div><button class="btn btn-secondary btn-sm" type="button" onclick="openChapterEdit(${chapter.id})">Edit</button></div>
          <div class="chapter-meta"><span>${chapter.question_count} questions</span><span>${chapter.material_count} materials</span></div>
          ${chapter.remark ? `<div class="chapter-remark"><strong>Remark:</strong> ${escapeHtml(chapter.remark)}</div>` : ''}
          <div class="chapter-admin-actions">
            <button class="btn btn-primary btn-sm" type="button" onclick="openChapterQuestions(${chapter.id})">Question bank</button>
            <button class="btn btn-secondary btn-sm" type="button" onclick="openChapterMaterial(${chapter.id})">Course material</button>
            <button class="btn btn-secondary btn-sm" type="button" onclick="openChapterRemark(${chapter.id})">Remark</button>
          </div>
        </article>`).join('') : '<div class="card empty-state">No chapters in this folder.</div>'}</div>
    </section>`).join('') : '<div class="card empty-state">Create a subject folder to begin.</div>';
}
function populateSubjectSelects() {
  const options = adminState.data.subjects.map(subject => `<option value="${subject.id}">${escapeHtml(subject.title)}</option>`).join('');
  byId('chapterSubjectSelect').innerHTML = options || '<option value="">Create a subject first</option>';
}

function groupedChapterOptions() {
  return groupedStructure().map(subject => `<optgroup label="${escapeHtml(subject.title)}">${subject.chapters.map(chapter => `<option value="${chapter.id}">Chapter ${chapter.chapter_number || '•'} — ${escapeHtml(chapter.title)}</option>`).join('')}</optgroup>`).join('');
}

function populateChapterSelects(preferredChapterId = null) {
  const options = groupedChapterOptions();
  for (const id of ['chapterSelect', 'materialChapterSelect']) {
    byId(id).innerHTML = `<option value="">Select chapter</option>${options}`;
    if (preferredChapterId) byId(id).value = String(preferredChapterId);
  }
  if (preferredChapterId) loadChapterQuestions();
}

async function createSubject(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  try {
    await api('/api/admin/subjects', { method: 'POST', body: JSON.stringify(data) });
    event.target.reset();
    toast('Subject folder created.', 'success');
    await loadAdmin();
  } catch (err) { toast(err.message, 'error'); }
}

async function createChapter(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  data.subject_id = Number(data.subject_id);
  if (data.chapter_number) data.chapter_number = Number(data.chapter_number); else delete data.chapter_number;
  try {
    const result = await api('/api/admin/chapters', { method: 'POST', body: JSON.stringify(data) });
    event.target.reset();
    toast('Chapter created.', 'success');
    await loadAdmin(result.chapter.id);
  } catch (err) { toast(err.message, 'error'); }
}

function setUploadStatus(message, type = '') {
  const element = byId('uploadStatus');
  element.textContent = message || '';
  element.className = `inline-status small ${type}`.trim();
}

async function previewQuestionBank(event) {
  event.preventDefault();
  const file = byId('questionFile');
  const text = byId('pastedText').value.trim();
  const chapterId = Number(byId('chapterSelect').value);
  if (!chapterId) { toast('Select a destination chapter first.'); return; }
  if (!file.files.length && !text) { toast('Choose a Word file or paste question-bank text.'); return; }
  const form = new FormData();
  if (file.files.length) form.append('file', file.files[0]);
  if (text) form.append('pasted_text', text);
  form.append('chapter_id', String(chapterId));
  const button = byId('detectButton');
  button.disabled = true; button.textContent = 'Detecting…';
  setUploadStatus('Reading question types and matching answers…', 'status-working');
  try {
    adminState.preview = await api('/api/admin/question-banks/preview', { method: 'POST', body: form });
    renderPreview();
    setUploadStatus(`${adminState.preview.summary.detected} questions detected.`, 'status-success');
  } catch (err) {
    setUploadStatus(err.message, 'status-error');
    toast(err.message, 'error');
  } finally {
    button.disabled = false; button.textContent = 'Detect questions and answers';
  }
}

function renderPreview() {
  const preview = adminState.preview;
  byId('previewSection').classList.remove('hidden');
  byId('previewSummary').textContent = `${preview.summary.detected} detected · ${preview.summary.needs_review} need review · ${preview.summary.total} total`;
  byId('previewWarnings').innerHTML = preview.warnings.length ? `<div class="notice notice-warning"><strong>Review notes</strong>${preview.warnings.slice(0, 10).map(warning => `<span>${escapeHtml(warning)}</span>`).join('')}</div>` : '';
  byId('previewList').innerHTML = preview.questions.length ? preview.questions.map((question, index) => `
    <article class="preview-item">
      <div class="preview-heading"><strong>Question ${index + 1}</strong><div><span class="badge badge-purple">${escapeHtml(formatLabels[question.question_format] || question.question_format)}</span><span class="badge ${question.status === 'detected' ? 'badge-success' : 'badge-warning'}">${escapeHtml(question.status.replace('_', ' '))}</span></div></div>
      <div class="format-preview">Student form: ${question.question_type === 'objective' ? (question.question_format === 'multiple_select' ? 'checkbox options' : 'radio options') : ['fill_blank','one_word','rapid_fire'].includes(question.question_format) ? 'single-line written answer + View Answer' : 'written answer box + View Answer'}</div>
      <div class="field"><label>Question</label><textarea class="input preview-question" data-index="${index}">${escapeHtml(question.question_text)}</textarea></div>
      ${question.options.length ? `<div class="detected-options">${question.options.map(option => `<span>${escapeHtml(option.key)}. ${escapeHtml(option.text)}</span>`).join('')}</div>` : ''}
      <div class="field"><label>Detected answer</label><textarea class="input preview-answer" data-index="${index}">${escapeHtml(question.correct_answer)}</textarea></div>
    </article>`).join('') : '<div class="card empty-state">No questions were detected.</div>';
  byId('previewSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function importDetected() {
  const chapterId = Number(byId('chapterSelect').value);
  if (!chapterId) { toast('Select a destination chapter before importing.'); return; }
  if (!adminState.preview || !adminState.preview.questions.length) { toast('Detect questions first.'); return; }
  document.querySelectorAll('.preview-question').forEach(element => { adminState.preview.questions[Number(element.dataset.index)].question_text = element.value.trim(); });
  document.querySelectorAll('.preview-answer').forEach(element => {
    const question = adminState.preview.questions[Number(element.dataset.index)];
    question.correct_answer = element.value.trim();
    question.status = question.correct_answer ? 'detected' : 'needs_review';
  });
  const button = byId('importButton');
  button.disabled = true; button.textContent = 'Importing…';
  try {
    const result = await api('/api/admin/question-banks/import', { method: 'POST', body: JSON.stringify({ chapter_id: chapterId, source_file: adminState.preview.source_file, source_hash: adminState.preview.source_hash || null, questions: adminState.preview.questions }) });
    toast(`${result.imported} questions imported. ${result.skipped} skipped.`, 'success');
    byId('previewSection').classList.add('hidden');
    byId('questionFile').value = '';
    byId('pastedText').value = '';
    adminState.preview = null;
    await loadAdmin(chapterId);
    await loadChapterQuestions();
  } catch (err) { toast(err.message, 'error'); }
  finally { button.disabled = false; button.textContent = 'Import detected questions'; }
}

async function saveMaterial(event) {
  event.preventDefault();
  const formData = new FormData();
  const chapterId = byId('materialChapterSelect').value;
  const title = event.target.elements.title.value.trim();
  const file = byId('materialFile');
  const text = byId('materialText').value.trim();
  if (!chapterId) { toast('Select a chapter.'); return; }
  if (!title) { toast('Enter a material title.'); return; }
  if (!file.files.length && !text) { toast('Choose a file or paste course material.'); return; }
  formData.append('chapter_id', chapterId);
  formData.append('title', title);
  if (file.files.length) formData.append('file', file.files[0]);
  if (text) formData.append('pasted_text', text);
  const button = byId('saveMaterialButton');
  button.disabled = true; button.textContent = 'Saving…';
  byId('materialStatus').textContent = 'Preparing material for students…';
  try {
    await api('/api/admin/materials', { method: 'POST', body: formData });
    event.target.reset();
    byId('materialStatus').textContent = 'Material saved.';
    toast('Course material published.', 'success');
    await loadAdmin();
    await loadMaterials();
  } catch (err) { byId('materialStatus').textContent = err.message; toast(err.message, 'error'); }
  finally { button.disabled = false; button.textContent = 'Save course material'; }
}

async function loadMaterials() {
  try {
    const data = await api('/api/admin/materials');
    adminState.materials = data.materials;
    byId('materialsList').innerHTML = data.materials.length ? `<table><thead><tr><th>Title</th><th>Subject</th><th>Chapter</th><th>Source</th><th>Published</th></tr></thead><tbody>${data.materials.map(material => `<tr><td><strong>${escapeHtml(material.title)}</strong></td><td>${escapeHtml(material.subject_title)}</td><td>${escapeHtml(material.chapter_title)}</td><td>${escapeHtml(material.source_file || 'Pasted text')}</td><td>${formatDate(material.created_at)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty-state">No course material published yet.</div>';
  } catch (err) { toast(err.message, 'error'); }
}

async function loadStudents() {
  try {
    const data = await api('/api/admin/students');
    adminState.students = data.students;
    byId('studentsBody').innerHTML = data.students.length ? data.students.map(student => `
      <tr>
        <td><strong>${escapeHtml(student.name)}</strong><br><span class="badge ${student.status === 'active' ? 'badge-success' : 'badge-danger'}">${escapeHtml(student.status)}</span></td>
        <td>${escapeHtml(student.o_number || '—')}</td><td>${escapeHtml(student.email)}</td>
        <td>${escapeHtml(student.age || '—')}<br><span class="muted small">${escapeHtml(student.dob || '—')}</span></td>
        <td>${escapeHtml(student.city || '—')}</td><td>${escapeHtml(student.gurukul_name || '—')}</td><td>${escapeHtml(student.mobile || '—')}</td>
        <td>${student.attempts}</td>
        <td><div class="table-actions"><button class="btn btn-secondary btn-sm" type="button" onclick="openStudentEdit(${student.id})">Edit</button><button class="btn btn-danger btn-sm" type="button" onclick="deleteStudent(${student.id})">Delete</button></div></td>
      </tr>`).join('') : '<tr><td colspan="9" class="muted">No student profiles available.</td></tr>';
  } catch (err) { toast(err.message, 'error'); }
}

function openAdminModal(title, html) {
  byId('adminModalTitle').textContent = title;
  byId('adminModalBody').innerHTML = html;
  byId('adminModalBackdrop').classList.remove('hidden');
  byId('adminModalBackdrop').setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
}

function closeAdminModal() {
  const backdrop = byId('adminModalBackdrop');
  if (!backdrop) return;
  backdrop.classList.add('hidden');
  backdrop.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('modal-open');
}

function subjectById(id) { return adminState.data.subjects.find(item => item.id === Number(id)); }
function chapterById(id) { return adminState.data.chapters.find(item => item.id === Number(id)); }

function openSubjectEdit(subjectId) {
  const subject = subjectById(subjectId); if (!subject) return;
  openAdminModal('Edit subject', `<form id="modalForm">
    <div class="field"><label>Subject name</label><input class="input" name="title" required value="${escapeHtml(subject.title)}"></div>
    <div class="field"><label>Description</label><textarea class="input small-textarea" name="description">${escapeHtml(subject.description || '')}</textarea></div>
    <div class="modal-actions"><button type="button" class="btn btn-secondary" onclick="closeAdminModal()">Cancel</button><button class="btn btn-primary">Save subject</button></div></form>`);
  byId('modalForm').addEventListener('submit', async event => {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.target));
    try { await api(`/api/admin/subjects/${subjectId}`, { method:'PUT', body:JSON.stringify(data) }); closeAdminModal(); toast('Subject updated.','success'); await loadAdmin(); }
    catch(err){ toast(err.message,'error'); }
  });
}

function openChapterEdit(chapterId) {
  const chapter = chapterById(chapterId); if (!chapter) return;
  const options = adminState.data.subjects.map(s => `<option value="${s.id}" ${s.id === chapter.subject_id ? 'selected' : ''}>${escapeHtml(s.title)}</option>`).join('');
  openAdminModal('Edit chapter', `<form id="modalForm">
    <div class="field"><label>Subject folder</label><select class="input" name="subject_id" required>${options}</select></div>
    <div class="field"><label>Chapter title</label><input class="input" name="title" required value="${escapeHtml(chapter.title)}"></div>
    <div class="field"><label>Chapter number</label><input class="input" name="chapter_number" type="number" min="1" value="${chapter.chapter_number || ''}"></div>
    <div class="field"><label>Remark</label><textarea class="input small-textarea" name="remark">${escapeHtml(chapter.remark || '')}</textarea></div>
    <div class="modal-actions"><button type="button" class="btn btn-secondary" onclick="closeAdminModal()">Cancel</button><button class="btn btn-primary">Save chapter</button></div></form>`);
  byId('modalForm').addEventListener('submit', async event => {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.target)); data.subject_id=Number(data.subject_id); data.chapter_number=data.chapter_number ? Number(data.chapter_number) : null;
    try { await api(`/api/admin/chapters/${chapterId}`, { method:'PUT', body:JSON.stringify(data) }); closeAdminModal(); toast('Chapter updated.','success'); await loadAdmin(chapterId); }
    catch(err){ toast(err.message,'error'); }
  });
}

function openChapterRemark(chapterId) {
  const chapter = chapterById(chapterId); if (!chapter) return;
  openAdminModal(`Remark · ${chapter.title}`, `<form id="modalForm"><div class="field"><label>Chapter remark</label><textarea class="input" name="remark" rows="6" placeholder="Add an admin remark for this chapter...">${escapeHtml(chapter.remark || '')}</textarea></div><div class="modal-actions"><button type="button" class="btn btn-secondary" onclick="closeAdminModal()">Cancel</button><button class="btn btn-primary">Save remark</button></div></form>`);
  byId('modalForm').addEventListener('submit', async event => {
    event.preventDefault(); const remark = new FormData(event.target).get('remark');
    try { await api(`/api/admin/chapters/${chapterId}/remark`, { method:'PUT', body:JSON.stringify({remark}) }); closeAdminModal(); toast('Remark saved.','success'); await loadAdmin(chapterId); }
    catch(err){ toast(err.message,'error'); }
  });
}

function openChapterQuestions(chapterId) {
  showAdminSection('questionBank'); byId('chapterSelect').value=String(chapterId); loadChapterQuestions();
}

function openChapterMaterial(chapterId) {
  showAdminSection('materials'); byId('materialChapterSelect').value=String(chapterId); byId('materialForm').scrollIntoView({behavior:'smooth',block:'start'});
}

async function loadChapterQuestions() {
  const chapterId = Number(byId('chapterSelect').value);
  if (!chapterId) { adminState.questions=[]; byId('chapterQuestionsList').innerHTML='<div class="empty-state">Select a chapter to view its questions.</div>'; return; }
  byId('chapterQuestionsList').innerHTML='<div class="empty-state">Loading questions…</div>';
  try {
    const data = await api(`/api/admin/questions?chapter_id=${chapterId}`); adminState.questions=data.questions;
    byId('chapterQuestionsList').innerHTML = data.questions.length ? `<table class="managed-question-table admin-responsive-table"><colgroup><col class="mq-col-number"><col class="mq-col-question"><col class="mq-col-type"><col class="mq-col-answer"><col class="mq-col-action"></colgroup><thead><tr><th>#</th><th>Question</th><th>Type</th><th>Answer</th><th>Action</th></tr></thead><tbody>${data.questions.map((q,i)=>`<tr><td data-label="#">${i+1}</td><td data-label="Question"><strong>${escapeHtml(q.question_text)}</strong><div class="muted small question-source">${escapeHtml(q.source_file || '')}</div></td><td data-label="Type"><span class="badge badge-purple question-type-badge">${escapeHtml(formatLabels[q.question_format] || q.question_format)}</span></td><td data-label="Answer" class="question-answer-cell">${escapeHtml(q.correct_answer)}</td><td data-label="Action"><div class="table-actions question-actions"><button class="btn btn-secondary btn-sm" type="button" onclick="openQuestionEdit(${q.id})">Edit</button><button class="btn btn-danger btn-sm" type="button" onclick="deleteQuestion(${q.id})">Delete</button></div></td></tr>`).join('')}</tbody></table>` : '<div class="empty-state">No imported questions in this chapter.</div>';
    enhanceResponsiveAdminTables(byId('chapterQuestionsList'));
  } catch(err){ byId('chapterQuestionsList').innerHTML=`<div class="empty-state">${escapeHtml(err.message)}</div>`; }
}

function openQuestionEdit(questionId) {
  const q = adminState.questions.find(item=>item.id===Number(questionId)); if(!q) return;
  const optionsText = (q.options || []).map(o=>`${o.key}. ${o.text}`).join('\n');
  openAdminModal('Edit question & answer', `<form id="modalForm">
    <div class="field"><label>Question</label><textarea class="input" rows="5" name="question_text" required>${escapeHtml(q.question_text)}</textarea></div>
    <div class="field"><label>Options <span class="muted small">(optional, one per line: A. Option)</span></label><textarea class="input" rows="5" name="options_text">${escapeHtml(optionsText)}</textarea></div>
    <div class="field"><label>Correct answer</label><textarea class="input" rows="4" name="correct_answer" required>${escapeHtml(q.correct_answer)}</textarea></div>
    <div class="modal-actions"><button type="button" class="btn btn-secondary" onclick="closeAdminModal()">Cancel</button><button class="btn btn-primary">Save changes</button></div></form>`);
  byId('modalForm').addEventListener('submit', async event=>{
    event.preventDefault(); const fd=new FormData(event.target); const lines=String(fd.get('options_text')||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
    const options=lines.map((line,i)=>{const m=line.match(/^([A-Za-z0-9]+)[\).:\-]\s*(.+)$/); return {key:(m?m[1]:String.fromCharCode(65+i)).toUpperCase(),text:m?m[2]:line};});
    const payload={question_text:String(fd.get('question_text')).trim(),correct_answer:String(fd.get('correct_answer')).trim(),options};
    try { await api(`/api/admin/questions/${questionId}`,{method:'PUT',body:JSON.stringify(payload)}); closeAdminModal(); toast('Question updated.','success'); await loadChapterQuestions(); await loadAdmin(Number(byId('chapterSelect').value)); }
    catch(err){toast(err.message,'error');}
  });
}

async function deleteQuestion(questionId) {
  if(!confirm('Delete this question from future quizzes? Existing quiz history will remain available.')) return;
  try { await api(`/api/admin/questions/${questionId}`,{method:'DELETE'}); toast('Question deleted.','success'); await loadChapterQuestions(); await loadAdmin(Number(byId('chapterSelect').value)); }
  catch(err){toast(err.message,'error');}
}

function openStudentEdit(studentId) {
  const st=adminState.students.find(item=>item.id===Number(studentId)); if(!st) return;
  openAdminModal(`Edit student · ${st.name}`, `<form id="modalForm" class="student-edit-grid">
    <div class="field"><label>Full name</label><input class="input" name="name" required value="${escapeHtml(st.name||'')}"></div>
    <div class="field"><label>O. Number</label><input class="input" name="o_number" value="${escapeHtml(st.o_number||'')}"></div>
    <div class="field"><label>Email</label><input class="input" type="email" name="email" required value="${escapeHtml(st.email||'')}"></div>
    <div class="field"><label>Login ID</label><input class="input" name="login_id" required value="${escapeHtml(st.login_id||'')}"></div>
    <div class="field"><label>Age</label><input class="input" type="number" min="1" max="120" name="age" value="${st.age||''}"></div>
    <div class="field"><label>Date of birth</label><input class="input" type="date" name="dob" value="${escapeHtml(st.dob||'')}"></div>
    <div class="field"><label>City</label><input class="input" name="city" value="${escapeHtml(st.city||'')}"></div>
    <div class="field"><label>Gurukul name</label><input class="input" name="gurukul_name" value="${escapeHtml(st.gurukul_name||'')}"></div>
    <div class="field"><label>Mobile</label><input class="input" name="mobile" value="${escapeHtml(st.mobile||'')}"></div>
    <div class="field"><label>Status</label><select class="input" name="status"><option value="active" ${st.status==='active'?'selected':''}>Active</option><option value="inactive" ${st.status==='inactive'?'selected':''}>Inactive</option></select></div>
    <div class="field full-span"><label>New password <span class="muted small">(optional)</span></label><input class="input" type="password" name="new_password" minlength="8" placeholder="Leave blank to keep current password"></div>
    <div class="modal-actions full-span"><button type="button" class="btn btn-secondary" onclick="closeAdminModal()">Cancel</button><button class="btn btn-primary">Save student profile</button></div></form>`);
  byId('modalForm').addEventListener('submit', async event=>{
    event.preventDefault(); const data=Object.fromEntries(new FormData(event.target)); data.age=data.age?Number(data.age):null; if(!data.new_password) data.new_password=null;
    try { await api(`/api/admin/students/${studentId}`,{method:'PUT',body:JSON.stringify(data)}); closeAdminModal(); toast('Student profile updated.','success'); await loadStudents(); await loadAdmin(); }
    catch(err){toast(err.message,'error');}
  });
}

async function deleteStudent(studentId) {
  const st=adminState.students.find(item=>item.id===Number(studentId));
  if(!confirm(`Permanently delete ${st ? st.name : 'this student'} and all quiz attempts, results and revision data?`)) return;
  try { await api(`/api/admin/students/${studentId}`,{method:'DELETE'}); toast('Student deleted.','success'); await loadStudents(); await loadAdmin(); }
  catch(err){toast(err.message,'error');}
}

init();
