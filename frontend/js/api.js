/* Frontend integration boundary. UI code calls this service, never MySQL directly. */
const localApiBaseUrl = 'http://localhost:5000/api';
const productionApiBaseUrl = 'https://smart-pyq-system.onrender.com/api';
const configuredApiBaseUrl = window.PYQ_API_BASE_URL || window.API_CONFIG?.baseUrl;
const isLocalHost = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);

window.API_CONFIG = {
  ...window.API_CONFIG,
  baseUrl: configuredApiBaseUrl || (isLocalHost ? localApiBaseUrl : productionApiBaseUrl),
  useMockData: window.API_CONFIG?.useMockData ?? false
};

async function readApiResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401 && window.location.pathname.endsWith('upload.html')) window.location.href = 'login.html';
  if (!response.ok) throw new Error(payload.error || `API request failed (${response.status})`);
  return payload;
}

window.PYQAuth = {
  csrfToken: null,
  async login(username, password) {
    const payload = await fetch(`${window.API_CONFIG.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password })
    }).then(readApiResponse);
    this.csrfToken = payload.csrf_token || null;
    return payload.admin;
  },
  async logout() {
    const payload = await fetch(`${window.API_CONFIG.baseUrl}/auth/logout`, {
      method: 'POST',
      headers: this.csrfToken ? { 'X-CSRF-Token': this.csrfToken } : {},
      credentials: 'include'
    }).then(readApiResponse);
    this.csrfToken = null;
    return payload;
  },
  async getCurrentAdmin() {
    const response = await fetch(`${window.API_CONFIG.baseUrl}/auth/me`, { credentials: 'include' });
    if (response.status === 401) { this.csrfToken = null; return null; }
    const payload = await readApiResponse(response);
    this.csrfToken = payload.csrf_token || null;
    return payload.admin || null;
  },
  csrfHeaders() { return this.csrfToken ? { 'X-CSRF-Token': this.csrfToken } : {}; }
};

window.PYQApi = {
  async getDashboardSummary() {
    if (window.API_CONFIG.useMockData) throw new Error('Dashboard statistics require the live Flask API.');
    return fetch(`${window.API_CONFIG.baseUrl}/dashboard/summary`, { credentials: 'omit' }).then(readApiResponse);
  },
  async listPapers(filters = {}) {
    if (window.API_CONFIG.useMockData) return window.MOCK_DATA.papers;
    const payload = await fetch(`${window.API_CONFIG.baseUrl}/papers?${new URLSearchParams(filters)}`, { credentials: 'omit' }).then(readApiResponse);
    return (payload.data || payload).map(paper => ({
      ...paper,
      name: paper.name || String(paper.pdf_filename || 'Untitled paper').replace(/\.pdf$/i, ''),
      filename: paper.filename || paper.pdf_filename || 'PDF filename unavailable',
      academicYear: paper.academicYear || paper.academic_year || 'Not provided',
      examYear: paper.examYear || paper.exam_year || 'Not provided',
      semester: paper.semester || 'Not provided',
      paperCode: paper.paperCode || paper.paper_code || 'Not provided',
      term: paper.term || 'Not provided',
      questions: paper.questions ?? '—'
    }));
  },
  async getPaper(paperId) {
    if (window.API_CONFIG.useMockData) throw new Error('Paper details require the live Flask API.');
    const paper = await fetch(`${window.API_CONFIG.baseUrl}/papers/${encodeURIComponent(paperId)}`, { credentials: 'omit' }).then(readApiResponse);
    return {
      ...paper,
      name: paper.name || String(paper.pdf_filename || 'Untitled paper').replace(/\.pdf$/i, ''),
      filename: paper.filename || paper.pdf_filename || 'PDF filename unavailable',
      academicYear: paper.academicYear || paper.academic_year || 'Not provided',
      examYear: paper.examYear || paper.exam_year || 'Not provided',
      semester: paper.semester || 'Not provided',
      paperCode: paper.paperCode || paper.paper_code || 'Not provided',
      term: paper.term || 'Not provided'
    };
  },
  getPdfUrl(paperId) {
    return `${window.API_CONFIG.baseUrl}/papers/${encodeURIComponent(paperId)}/pdf`;
  },
  getDownloadUrl(paperId) {
    return `${window.API_CONFIG.baseUrl}/papers/${encodeURIComponent(paperId)}/download`;
  },
  async checkPdfAvailability(paperId) {
    const response = await fetch(this.getPdfUrl(paperId), { method: 'HEAD', credentials: 'omit' });
    if (!response.ok) throw new Error('The original PDF is unavailable.');
  },
  async listQuestions(filters = {}) {
    if (window.API_CONFIG.useMockData) return window.MOCK_DATA.questions;
    const payload = await fetch(`${window.API_CONFIG.baseUrl}/questions?${new URLSearchParams(filters)}`, { credentials: 'omit' }).then(readApiResponse);
    return (payload.data || []).map(question => ({
      ...question,
      number: question.question_number || '—',
      text: question.question_text || '',
      subject: question.paper_subject || 'Not provided',
      paper: question.paper_filename || 'Paper unavailable',
      year: question.paper_exam_year ?? 'Not provided'
    }));
  },
  async listRepeated(filters = {}) {
    if (window.API_CONFIG.useMockData) throw new Error('Repeated-question analysis requires the live Flask API.');
    const payload = await fetch(`${window.API_CONFIG.baseUrl}/repeated-questions?${new URLSearchParams(filters)}`, { credentials: 'omit' }).then(readApiResponse);
    return (payload.data || []).map(question => ({
      ...question,
      text: `[${question.match_type || 'Exact'} ${Number(question.similarity_percentage || 0).toFixed(2)}%] ${question.question_text || ''} <-> ${question.matching_question_text || ''}`,
      matchingText: question.matching_question_text || '',
      matchType: question.match_type || 'Exact',
      similarityPercentage: Number(question.similarity_percentage || 0),
      firstPaperId: question.first_paper_id,
      secondPaperId: question.second_paper_id,
      frequency: Number(question.frequency || 0),
      distinctPapers: Number(question.distinct_papers || 0),
      years: question.exam_years || [],
      paperFilenames: question.paper_filenames || [],
      subject: question.subject || 'Not provided'
    }));
  },
  async uploadPaper(formData) {
    if (window.API_CONFIG.useMockData) return { queued: true, preview: true };
    return fetch(`${window.API_CONFIG.baseUrl}/papers`, { method: 'POST', body: formData, headers: window.PYQAuth.csrfHeaders(), credentials: 'include' }).then(readApiResponse);
  },
  async updatePaper(paperId, metadata) {
    if (window.API_CONFIG.useMockData) return { updated: true, preview: true, paperId, metadata };
    return fetch(`${window.API_CONFIG.baseUrl}/papers/${paperId}`, { method: 'PATCH', body: JSON.stringify(metadata), headers: { 'Content-Type': 'application/json' }, credentials: 'include' }).then(readApiResponse);
  },
  async deletePaper(paperId) {
    if (window.API_CONFIG.useMockData) throw new Error('Paper deletion requires the live API.');
    return fetch(`${window.API_CONFIG.baseUrl}/papers/${encodeURIComponent(paperId)}`, {
      method: 'DELETE',
      headers: window.PYQAuth.csrfHeaders(),
      credentials: 'include'
    }).then(readApiResponse);
  },
  async _read(response) { return readApiResponse(response); }
};
