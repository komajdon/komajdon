const API = {
  token: null,
  async request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    if (method === 'DELETE' && res.status === 204) return null;
    const data = res.headers.get('content-type')?.includes('application/json')
      ? await res.json() : await res.text();
    if (!res.ok) throw new Error(typeof data === 'string' ? data : data.detail || JSON.stringify(data));
    return data;
  },
  get(path) { return this.request('GET', path); },
  post(path, body) { return this.request('POST', path, body); },
  patch(path, body) { return this.request('PATCH', path, body); },
  put(path, body) { return this.request('PUT', path, body); },
  delete(path) { return this.request('DELETE', path); },
};

const store = { user: null, models: [], pipelines: [], playgroundResults: {} };

function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function navigate(view, data = null) {
  history.pushState({ view, data }, '', `#${view}`);
  render(view, data);
}

window.addEventListener('popstate', (e) => {
  const state = e.state || { view: 'auth' };
  render(state.view, state.data);
});

async function init() {
  API.token = localStorage.getItem('komajdon_token');
  if (API.token) {
    try {
      store.user = await API.get('/api/auth/me');
      await loadModels();
      await loadPipelines();
      navigate('dashboard');
      return;
    } catch {
      localStorage.removeItem('komajdon_token');
      API.token = null;
    }
  }
  navigate('auth');
}

async function loadModels() {
  store.models = await API.get('/api/models/');
}

async function loadPipelines() {
  try { store.pipelines = await API.get('/api/pipelines/'); } catch { store.pipelines = []; }
}

function render(view, app) {
  app = app || document.getElementById('app');
  switch (view) {
    case 'auth': renderAuth(app); break;
    case 'dashboard': renderDashboard(app); break;
    case 'model-detail': renderModelDetail(app); break;
    case 'pipelines': renderPipelinesPage(app); break;
    case 'storage': renderStoragePage(app); break;
    default: renderDashboard(app);
  }
}

// ============ AUTH ============
function renderAuth(app) {
  app.innerHTML = `
    <div class="auth-container">
      <div class="auth-box">
        <h1>🌿 Komajdon</h1>
        <p class="subtitle">Visual Backends for MongoDB</p>
        <div class="auth-tabs">
          <button class="auth-tab active" data-tab="login">Login</button>
          <button class="auth-tab" data-tab="register">Register</button>
        </div>
        <div id="auth-form">
          <div class="form-group"><label>Email</label><input type="email" id="auth-email" placeholder="you@example.com"></div>
          <div class="form-group"><label>Password</label><input type="password" id="auth-password" placeholder="••••••••"></div>
          <button class="btn btn-primary btn-block" id="auth-submit">Login</button>
        </div>
      </div>
    </div>`;
  let mode = 'login';
  const emailEl = document.getElementById('auth-email');
  const passEl = document.getElementById('auth-password');
  const submitEl = document.getElementById('auth-submit');
  document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      mode = tab.dataset.tab;
      submitEl.textContent = mode === 'login' ? 'Login' : 'Register';
    });
  });
  submitEl.addEventListener('click', async () => {
    const email = emailEl.value.trim(), password = passEl.value.trim();
    if (!email || !password) return toast('Fill in all fields', 'error');
    submitEl.disabled = true; submitEl.innerHTML = '<span class="spinner"></span>';
    try {
      const data = await API.post(`/api/auth/${mode}`, { email, password });
      API.token = data.access_token;
      localStorage.setItem('komajdon_token', data.access_token);
      store.user = await API.get('/api/auth/me');
      await loadModels(); await loadPipelines();
      navigate('dashboard');
    } catch (e) { toast(e.message, 'error'); submitEl.disabled = false; submitEl.textContent = mode === 'login' ? 'Login' : 'Register'; }
  });
  emailEl.addEventListener('keydown', e => { if (e.key === 'Enter') submitEl.click(); });
  passEl.addEventListener('keydown', e => { if (e.key === 'Enter') submitEl.click(); });
}

// ============ DASHBOARD ============
function renderDashboard(app) {
  app.innerHTML = `
    <div class="header">
      <div class="header-left">
        <div class="logo">        <div class="logo-icon">K</div><h1>Komajdon</h1></div>
        <nav style="margin-left:24px;display:flex;gap:8px;">
          <button class="btn btn-sm btn-secondary nav-btn active" data-view="models">Models</button>
          <button class="btn btn-sm btn-secondary nav-btn" data-view="pipelines">Pipelines</button>
          <button class="btn btn-sm btn-secondary nav-btn" data-view="storage">Storage</button>
        </nav>
      </div>
      <div class="header-right">
        <span class="user-info">${store.user.email}</span>
        <button class="btn btn-primary" id="btn-new-model">+ New Model</button>
        <button class="btn btn-secondary" id="btn-logout">Logout</button>
      </div>
    </div>
    <div id="dashboard-content"><h2 style="margin-bottom:16px;">Your Models</h2><div id="model-list"></div></div>`;

  document.getElementById('btn-logout').addEventListener('click', () => {
    localStorage.removeItem('komajdon_token'); API.token = null; store.user = null; navigate('auth');
  });
  document.getElementById('btn-new-model').addEventListener('click', () => showModelBuilder());
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const view = btn.dataset.view;
      const content = document.getElementById('dashboard-content');
      if (view === 'models') renderModelList(content);
      else if (view === 'pipelines') renderPipelinesView(content);
      else if (view === 'storage') renderStorageView(content);
    });
  });
  renderModelList(document.getElementById('model-list'));
}

function renderModelList(container) {
  if (!store.models.length) {
    container.innerHTML = `<div class="empty-state"><div class="emoji">🌿</div><h3>No models yet</h3><p>Create your first model to generate APIs instantly</p><button class="btn btn-primary" style="margin-top:16px;" onclick="showModelBuilder()">Create Model</button></div>`;
    return;
  }
  container.innerHTML = `<div class="model-grid">${store.models.map(m => `
    <div class="model-card" data-name="${m.name}">
      <h3>${m.name}</h3>
      <div class="model-meta">${m.fields.length} field${m.fields.length !== 1 ? 's' : ''} · ${m.indexes?.length || 0} index${(m.indexes?.length || 0) !== 1 ? 'es' : ''}</div>
      <div>${m.auth_protected ? '<span class="model-badge badge-auth">🔒 Auth</span>' : ''}${m.realtime_enabled ? '<span class="model-badge badge-realtime">⚡ Live</span>' : ''}</div>
    </div>`).join('')}</div>`;
  container.querySelectorAll('.model-card').forEach(el => {
    el.addEventListener('click', () => navigate('model-detail', el.dataset.name));
  });
}

// ============ MODEL BUILDER ============
function showModelBuilder(existingModel = null) {
  const isEdit = !!existingModel;
  const fields = isEdit ? JSON.parse(JSON.stringify(existingModel.fields)) : [];
  const indexes = isEdit ? JSON.parse(JSON.stringify(existingModel.indexes || [])) : [];
  const modelName = isEdit ? existingModel.name : '';
  const authProtected = isEdit ? existingModel.auth_protected : true;
  const realtimeEnabled = isEdit ? existingModel.realtime_enabled : false;
  let currentTab = 'fields';

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal" style="max-width:780px;">
      <h2>${isEdit ? 'Edit' : 'Create'} Model</h2>
      <div class="form-group">
        <label>Model Name</label>
        <input type="text" id="builder-name" value="${modelName}" placeholder="e.g. Task, User, Product" ${isEdit ? 'disabled' : ''}>
      </div>
      <div style="display:flex; gap:16px; margin-bottom:16px;">
        <label class="checkbox-label"><input type="checkbox" id="builder-auth" ${authProtected ? 'checked' : ''}> 🔒 Auth Protected</label>
        <label class="checkbox-label"><input type="checkbox" id="builder-realtime" ${realtimeEnabled ? 'checked' : ''}> ⚡ Real-time</label>
      </div>
      <div class="tabs" style="margin-bottom:12px;">
        <button class="tab active" data-btab="fields">Fields</button>
        <button class="tab" data-btab="indexes">Indexes</button>
        <button class="tab" data-btab="preview">Preview</button>
      </div>
      <div id="builder-tab-content"></div>
      <div style="display:flex; gap:8px; margin-top:20px; justify-content:flex-end;">
        <button class="btn btn-secondary" id="btn-builder-cancel">Cancel</button>
        <button class="btn btn-primary" id="btn-builder-save">${isEdit ? 'Update' : 'Generate API 🚀'}</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  const tabContent = overlay.querySelector('#builder-tab-content');
  const nameInput = overlay.querySelector('#builder-name');
  const authCheck = overlay.querySelector('#builder-auth');
  const realtimeCheck = overlay.querySelector('#builder-realtime');

  function switchBuilderTab(tab) {
    currentTab = tab;
    overlay.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
    overlay.querySelector(`[data-btab="${tab}"]`).classList.add('active');
    if (tab === 'fields') renderFieldEditor();
    else if (tab === 'indexes') renderIndexEditor();
    else renderPreview();
  }

  overlay.querySelectorAll('[data-btab]').forEach(btn => {
    btn.addEventListener('click', () => switchBuilderTab(btn.dataset.btab));
  });

  function getCurrentFields() {
    const result = [];
    tabContent.querySelectorAll('.field-item').forEach(item => {
      const name = item.querySelector('.f-name')?.value?.trim();
      const type = item.querySelector('.f-type')?.value;
      const required = item.querySelector('.f-required')?.checked;
      const unique = item.querySelector('.f-unique')?.checked;
      const indexed = item.querySelector('.f-indexed')?.checked;
      const minLength = item.querySelector('.f-minlen')?.value;
      const maxLength = item.querySelector('.f-maxlen')?.value;
      const minimum = item.querySelector('.f-min')?.value;
      const maximum = item.querySelector('.f-max')?.value;
      const pattern = item.querySelector('.f-pattern')?.value;
      const enumVal = item.querySelector('.f-enum')?.value;
      const relationType = item.querySelector('.f-rel-type')?.value;
      const targetModel = item.querySelector('.f-rel-target')?.value;
      if (name) {
        const field = { name, type, required: !!required, indexed: !!indexed, default: null };
        field.validation = { required: !!required, unique: !!unique };
        if (minLength) field.validation.min_length = parseInt(minLength);
        if (maxLength) field.validation.max_length = parseInt(maxLength);
        if (minimum) field.validation.minimum = parseFloat(minimum);
        if (maximum) field.validation.maximum = parseFloat(maximum);
        if (pattern) field.validation.pattern = pattern;
        if (enumVal) field.validation.enum = enumVal.split(',').map(s => s.trim()).filter(Boolean);
        if (type === 'relation' && relationType && targetModel) {
          field.relation = { type: relationType, target_model: targetModel, foreign_key: `${targetModel}_id` };
        }
        result.push(field);
      }
    });
    return result;
  }

  function renderFieldEditor() {
    tabContent.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-size:0.85rem;color:var(--text-secondary);">Define fields with validation rules</span>
        <button class="btn btn-sm btn-secondary" id="btn-add-field">+ Add Field</button>
      </div>
      <div class="field-list" id="field-list"></div>`;

    function renderFieldsUI() {
      const list = tabContent.querySelector('#field-list');
      list.innerHTML = fields.map((f, i) => `
        <div class="field-item" style="flex-wrap:wrap;">
          <input type="text" class="f-name" value="${f.name}" placeholder="name" style="flex:1;min-width:100px;">
          <select class="f-type" style="width:100px;">
            ${['string','number','boolean','date','array','object','relation'].map(t => `<option value="${t}" ${t === f.type ? 'selected' : ''}>${t}</option>`).join('')}
          </select>
          <div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;width:100%;margin-top:6px;padding-left:4px;">
            <label class="checkbox-label" style="font-size:0.75rem;"><input type="checkbox" class="f-required" ${f.required ? 'checked' : ''}> req</label>
            <label class="checkbox-label" style="font-size:0.75rem;"><input type="checkbox" class="f-unique" ${f.validation?.unique ? 'checked' : ''}> unique</label>
            <label class="checkbox-label" style="font-size:0.75rem;"><input type="checkbox" class="f-indexed" ${f.indexed ? 'checked' : ''}> index</label>
            ${f.type === 'string' ? `
              <input type="number" class="f-minlen" value="${f.validation?.min_length || ''}" placeholder="min len" style="width:70px;font-size:0.75rem;padding:4px 6px;">
              <input type="number" class="f-maxlen" value="${f.validation?.max_length || ''}" placeholder="max len" style="width:70px;font-size:0.75rem;padding:4px 6px;">
              <input type="text" class="f-pattern" value="${f.validation?.pattern || ''}" placeholder="regex" style="width:100px;font-size:0.75rem;padding:4px 6px;">
              <input type="text" class="f-enum" value="${(f.validation?.enum || []).join(',')}" placeholder="a,b,c" style="width:100px;font-size:0.75rem;padding:4px 6px;">
            ` : ''}
            ${f.type === 'number' ? `
              <input type="number" class="f-min" value="${f.validation?.minimum || ''}" placeholder="min" style="width:70px;font-size:0.75rem;padding:4px 6px;">
              <input type="number" class="f-max" value="${f.validation?.maximum || ''}" placeholder="max" style="width:70px;font-size:0.75rem;padding:4px 6px;">
            ` : ''}
            ${f.type === 'relation' ? `
              <select class="f-rel-type" style="width:90px;font-size:0.75rem;padding:4px 6px;">
                ${['belongs_to','has_one','has_many'].map(t => `<option value="${t}" ${t === (f.relation?.type || 'belongs_to') ? 'selected' : ''}>${t}</option>`).join('')}
              </select>
              <input type="text" class="f-rel-target" value="${f.relation?.target_model || ''}" placeholder="target model" style="width:110px;font-size:0.75rem;padding:4px 6px;">
            ` : ''}
            <button class="btn btn-sm btn-danger field-remove" data-idx="${i}" style="margin-left:auto;">✕</button>
          </div>
        </div>`).join('');
      list.querySelectorAll('.field-remove').forEach(el => el.addEventListener('click', () => { fields.splice(parseInt(el.dataset.idx), 1); renderFieldsUI(); }));
      list.querySelectorAll('.f-type').forEach(el => el.addEventListener('change', renderFieldsUI));
    }
    renderFieldsUI();
    tabContent.querySelector('#btn-add-field').addEventListener('click', () => {
      fields.push({ name: '', type: 'string', required: false, indexed: false, validation: {} });
      renderFieldsUI();
    });
  }

  function renderIndexEditor() {
    tabContent.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-size:0.85rem;color:var(--text-secondary);">Database indexes for performance</span>
        <button class="btn btn-sm btn-secondary" id="btn-add-index">+ Add Index</button>
      </div>
      <div id="index-list">${indexes.map((idx, i) => `
        <div class="field-item">
          <input type="text" class="idx-field" value="${idx.field}" placeholder="field name" style="flex:1;">
          <select class="idx-dir" style="width:80px;">
            <option value="1" ${idx.direction === 1 ? 'selected' : ''}>ASC</option>
            <option value="-1" ${idx.direction === -1 ? 'selected' : ''}>DESC</option>
          </select>
          <label class="checkbox-label" style="font-size:0.75rem;"><input type="checkbox" class="idx-unique" ${idx.unique ? 'checked' : ''}> unique</label>
          <button class="btn btn-sm btn-danger idx-remove" data-idx="${i}">✕</button>
        </div>`).join('')}</div>`;
    tabContent.querySelector('#btn-add-index').addEventListener('click', () => {
      indexes.push({ field: '', direction: 1, unique: false });
      renderIndexEditor();
    });
    tabContent.querySelectorAll('.idx-remove').forEach(el => el.addEventListener('click', () => { indexes.splice(parseInt(el.dataset.idx), 1); renderIndexEditor(); }));
  }

  function renderPreview() {
    const currentFields = getCurrentFields();
    const schema = {
      name: nameInput.value || 'ModelName',
      fields: currentFields,
      indexes,
      auth_protected: authCheck.checked,
      realtime_enabled: realtimeCheck.checked,
    };
    const endpoints = [
      `GET    /api/${schema.name}`,
      `POST   /api/${schema.name}`,
      `GET    /api/${schema.name}/:id`,
      `PATCH  /api/${schema.name}/:id`,
      `PUT    /api/${schema.name}/:id`,
      `DELETE /api/${schema.name}/:id`,
    ];
    tabContent.innerHTML = `
      <div style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:8px;">Schema definition with generated endpoints</div>
      <div class="json-preview">${JSON.stringify(schema, null, 2)}\n\n// Generated Endpoints:\n${endpoints.join('\n')}</div>`;
  }

  overlay.querySelector('#btn-builder-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#btn-builder-save').addEventListener('click', async () => {
    const name = nameInput.value.trim();
    if (!name) return toast('Model name is required', 'error');
    const currentFields = getCurrentFields();
    if (!currentFields.length) return toast('Add at least one field', 'error');
    const body = { name, fields: currentFields, indexes, auth_protected: authCheck.checked, realtime_enabled: realtimeCheck.checked };
    try {
      if (!isEdit) {
        await API.post('/api/models/', body);
        toast(`✨ API generated for "${name}"!`, 'success');
      } else {
        toast('Model updated', 'success');
      }
      overlay.remove();
      await loadModels();
      navigate('dashboard');
    } catch (e) { toast(e.message, 'error'); }
  });
  renderFieldEditor();
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
}

// ============ MODEL DETAIL ============
function renderModelDetail(app) {
  const modelName = history.state?.data || window.location.hash.split('/')[1];
  const model = store.models.find(m => m.name === modelName);
  if (!model) { navigate('dashboard'); return; }

  let currentTab = 'schema';
  app.innerHTML = `
    <div class="header">
      <div class="header-left">
        <div class="logo"><div class="logo-icon">M</div><h1>${model.name}</h1></div>
      </div>
      <div class="header-right">
        <span class="user-info">${store.user.email}</span>
        <button class="btn btn-secondary" id="btn-back">← Back</button>
        <button class="btn btn-secondary" id="btn-logout">Logout</button>
      </div>
    </div>
    <div class="tabs">
      <button class="tab active" data-tab="schema">Schema</button>
      <button class="tab" data-tab="playground">Playground</button>
      <button class="tab" data-tab="aggregations">Aggregations</button>
      <button class="tab" data-tab="sdk">SDK</button>
      <button class="tab" data-tab="realtime">Real-time</button>
    </div>
    <div id="tab-content"></div>`;

  document.getElementById('btn-back').addEventListener('click', () => navigate('dashboard'));
  document.getElementById('btn-logout').addEventListener('click', () => {
    localStorage.removeItem('komajdon_token'); API.token = null; store.user = null; navigate('auth');
  });
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentTab = tab.dataset.tab;
      renderModelTab(currentTab, model, document.getElementById('tab-content'));
    });
  });
  renderModelTab('schema', model, document.getElementById('tab-content'));
}

function renderModelTab(tab, model, container) {
  const handlers = { schema: renderSchemaTab, playground: renderPlaygroundTab, aggregations: renderAggsTab, sdk: renderSDKTab, realtime: renderRealtimeTab };
  (handlers[tab] || renderSchemaTab)(model, container);
}

function renderSchemaTab(model, container) {
  container.innerHTML = `
    <div class="card">
      <div class="card-header"><h2>Fields</h2>
        <div style="display:flex;gap:8px;">
          <button class="btn btn-sm btn-secondary" id="btn-edit-model">Edit</button>
          <button class="btn btn-sm btn-secondary" id="btn-export-schema">Export</button>
          <button class="btn btn-sm btn-danger" id="btn-delete-model">Delete</button>
        </div>
      </div>
      ${!model.fields?.length ? '<p style="color:var(--text-muted)">No fields defined</p>' :
        `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px;">
          ${model.fields.map(f => {
            const badges = [];
            if (f.required) badges.push('req');
            if (f.validation?.unique) badges.push('unique');
            if (f.indexed || f.validation?.unique) badges.push('indexed');
            let extras = '';
            if (f.validation?.min_length != null) extras += ` · min:${f.validation.min_length}`;
            if (f.validation?.max_length != null) extras += ` · max:${f.validation.max_length}`;
            if (f.validation?.minimum != null) extras += ` · ≥${f.validation.minimum}`;
            if (f.validation?.maximum != null) extras += ` · ≤${f.validation.maximum}`;
            if (f.validation?.pattern) extras += ` · /${f.validation.pattern}/`;
            if (f.relation) extras += ` → ${f.relation.target_model} (${f.relation.type})`;
            return `<div style="background:var(--bg-input);padding:12px;border-radius:var(--radius);">
              <div style="font-weight:600;font-size:0.9rem;">${f.name} <span style="font-weight:400;color:var(--text-muted);font-size:0.75rem;">${f.type}</span></div>
              <div style="color:var(--text-muted);font-size:0.75rem;margin-top:4px;">${badges.map(b => `<span style="background:rgba(16,170,80,0.15);padding:0 6px;border-radius:4px;margin-right:4px;">${b}</span>`).join('')}${extras}</div>
            </div>`;
          }).join('')}</div>`}
      ${model.indexes?.length ? `<div style="margin-top:16px;"><h3 style="font-size:0.9rem;color:var(--text-secondary);margin-bottom:8px;">Indexes</h3><div style="display:flex;gap:8px;flex-wrap:wrap;">${model.indexes.map(i => `<span style="background:var(--bg-input);padding:4px 10px;border-radius:4px;font-size:0.8rem;">${i.field} (${i.direction === 1 ? 'ASC' : 'DESC'})${i.unique ? ' · unique' : ''}</span>`).join('')}</div></div>` : ''}
    </div>
    <div class="card">
      <div class="card-header"><h2>JSON Schema</h2><button class="btn btn-sm btn-secondary" id="btn-copy-schema">Copy</button></div>
      <div class="json-preview">${JSON.stringify({ name: model.name, fields: model.fields, indexes: model.indexes, auth_protected: model.auth_protected, realtime_enabled: model.realtime_enabled }, null, 2)}</div>
    </div>`;

  container.querySelector('#btn-edit-model')?.addEventListener('click', () => showModelBuilder(model));
  container.querySelector('#btn-export-schema')?.addEventListener('click', () => {
    API.get(`/api/models/${model.name}/export`).then(data => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${model.name}-schema.json`; a.click();
    });
  });
  container.querySelector('#btn-delete-model')?.addEventListener('click', async () => {
    if (!confirm(`Delete model "${model.name}"? Data will be lost.`)) return;
    try { await API.delete(`/api/models/${model.name}`); toast(`Deleted`, 'info'); await loadModels(); navigate('dashboard'); }
    catch (e) { toast(e.message, 'error'); }
  });
  container.querySelector('#btn-copy-schema')?.addEventListener('click', () => {
    navigator.clipboard.writeText(JSON.stringify({ name: model.name, fields: model.fields, indexes: model.indexes, auth_protected: model.auth_protected, realtime_enabled: model.realtime_enabled }, null, 2));
    toast('Schema copied!');
  });
}

// ============ PLAYGROUND ============
function renderPlaygroundTab(model, container) {
  const endpoints = [
    { method: 'GET', path: `/api/${model.name}`, desc: 'List (with filter/sort/populate/project)', hasQuery: true },
    { method: 'POST', path: `/api/${model.name}`, desc: 'Create item', hasBody: true },
    { method: 'GET', path: `/api/${model.name}/:id`, desc: 'Get by ID' },
    { method: 'PATCH', path: `/api/${model.name}/:id`, desc: 'Partial update', hasBody: true },
    { method: 'PUT', path: `/api/${model.name}/:id`, desc: 'Full replace', hasBody: true },
    { method: 'DELETE', path: `/api/${model.name}/:id`, desc: 'Delete item' },
  ];
  container.innerHTML = `<div class="card playground-section"><h2 style="margin-bottom:16px;">API Playground</h2>
    <p style="color:var(--text-muted);margin-bottom:16px;font-size:0.85rem;">
      Test your generated endpoints. Supports <code>filter</code> (<code>field__op=value</code>), <code>sort</code> (<code>-field</code> for desc), <code>populate</code>, <code>fields</code>.
    </p>
    ${endpoints.map((ep, i) => `<div class="endpoint-card">
      <span class="endpoint-method method-${ep.method}">${ep.method}</span>
      <span class="endpoint-path">${ep.path}</span>
      <span style="font-size:0.8rem;color:var(--text-muted);flex:1;margin-left:8px;">${ep.desc}</span>
      <button class="endpoint-test-btn" data-idx="${i}">Test</button>
    </div>`).join('')}
    <div id="playground-result" style="margin-top:16px;"></div></div>`;

  container.querySelectorAll('.endpoint-test-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const ep = endpoints[parseInt(btn.dataset.idx)];
      const resultDiv = document.getElementById('playground-result');

      const exampleBody = {};
      (model.fields || []).forEach(f => {
        if (f.type === 'string') exampleBody[f.name] = 'test';
        else if (f.type === 'number') exampleBody[f.name] = 0;
        else if (f.type === 'boolean') exampleBody[f.name] = false;
        else if (f.type === 'date') exampleBody[f.name] = new Date().toISOString();
        else exampleBody[f.name] = null;
      });

      resultDiv.innerHTML = `<div style="background:var(--bg-input);padding:16px;border-radius:var(--radius);">
        <h3 style="margin-bottom:12px;font-size:1rem;">${ep.method} ${ep.path}</h3>
        ${ep.path.includes(':id') ? `<div class="form-group"><label>ID</label><input type="text" id="pg-id" placeholder="Enter document ID"></div>` : ''}
        ${ep.hasQuery ? `<div class="form-group"><label>Query params (optional)</label><input type="text" id="pg-query" placeholder="filter=status__eq=active&sort=-createdAt&populate=category&fields=title,status" style="font-family:monospace;font-size:0.8rem;"></div>` : ''}
        ${ep.hasBody ? `<div class="form-group"><label>Request Body</label><textarea id="pg-body" rows="6">${JSON.stringify(exampleBody, null, 2)}</textarea></div>` : ''}
        <button class="btn btn-primary btn-sm" id="pg-send">Send</button>
        <button class="btn btn-sm btn-secondary" id="pg-copy-curl" style="margin-left:8px;">Copy cURL</button>
        <div id="pg-response" class="response-box" style="margin-top:12px;">// Response</div>
      </div>`;

      document.getElementById('pg-send').addEventListener('click', async () => {
        const resp = document.getElementById('pg-response');
        resp.textContent = '⏳ Loading...';
        let path = `/api/${model.name}`;
        if (ep.path.includes(':id')) {
          const id = document.getElementById('pg-id')?.value.trim();
          if (!id) { resp.textContent = 'Error: ID required'; return; }
          path += `/${id}`;
        }
        const queryStr = document.getElementById('pg-query')?.value.trim();
        if (queryStr) path += `?${queryStr}`;
        let body = null;
        if (ep.hasBody) {
          try { body = JSON.parse(document.getElementById('pg-body').value); }
          catch { resp.textContent = 'Error: Invalid JSON'; return; }
        }
        try {
          const data = await API.request(ep.method, path, body);
          resp.textContent = JSON.stringify(data, null, 2);
        } catch (e) { resp.textContent = `Error: ${e.message}`; }
      });

      document.getElementById('pg-copy-curl')?.addEventListener('click', () => {
        let path = `/api/${model.name}`;
        if (ep.path.includes(':id')) path += '/:id';
        const q = document.getElementById('pg-query')?.value.trim();
        let curl = `curl -X ${ep.method} http://localhost:8000${path}${q ? '?' + q : ''}`;
        if (API.token) curl += ` -H "Authorization: Bearer ${API.token}"`;
        if (ep.hasBody) {
          const body = document.getElementById('pg-body')?.value || '{}';
          curl += ` -H "Content-Type: application/json" -d '${body}'`;
        }
        navigator.clipboard.writeText(curl);
        toast('cURL copied!');
      });
    });
  });
}

// ============ AGGREGATIONS ============
function renderAggsTab(model, container) {
  container.innerHTML = `<div class="card">
    <h2 style="margin-bottom:16px;">Aggregation Templates</h2>
    <p style="color:var(--text-muted);margin-bottom:16px;">Run predefined aggregation pipelines against <strong>${model.name}</strong>.</p>
    <div class="agg-grid" id="agg-grid"></div>
    <div id="agg-result" style="margin-top:16px;"></div>
  </div>`;

  API.get('/api/aggregations/templates').then(templates => {
    const grid = document.getElementById('agg-grid');
    grid.innerHTML = templates.map(t => `<div class="agg-card" data-template="${t.id}"><h4>${t.name}</h4></div>`).join('');
    grid.querySelectorAll('.agg-card').forEach(card => {
      card.addEventListener('click', () => runAggTemplate(model, card.dataset.template));
    });
  });
}

function runAggTemplate(model, templateId) {
  const resultDiv = document.getElementById('agg-result');
  const extraInputs = ['count_by_field', 'average_by_field'].includes(templateId)
    ? `<div class="form-group"><label>Field Name</label><input type="text" id="agg-field" placeholder="e.g. status"></div>` : '';
  const valueInput = templateId === 'average_by_field'
    ? `<div class="form-group"><label>Value Field</label><input type="text" id="agg-value" placeholder="e.g. price"></div>` : '';

  resultDiv.innerHTML = `<div style="background:var(--bg-input);padding:16px;border-radius:var(--radius);">
    <h3 style="margin-bottom:12px;">${templateId}</h3>${extraInputs}${valueInput}
    <button class="btn btn-primary btn-sm" id="agg-run">Run</button>
    <div id="agg-response" class="response-box" style="margin-top:12px;">// Results</div></div>`;

  document.getElementById('agg-run').addEventListener('click', async () => {
    const resp = document.getElementById('agg-response');
    resp.textContent = '⏳ Running...';
    const fieldName = document.getElementById('agg-field')?.value || '';
    const valueField = document.getElementById('agg-value')?.value || '';
    let path = `/api/aggregations/run/${model.name}?template=${templateId}`;
    if (fieldName) path += `&field_name=${encodeURIComponent(fieldName)}`;
    if (valueField) path += `&value_field=${encodeURIComponent(valueField)}`;
    try { resp.textContent = JSON.stringify(await API.get(path), null, 2); }
    catch (e) { resp.textContent = `Error: ${e.message}`; }
  });
}

// ============ SDK ============
function renderSDKTab(model, container) {
  container.innerHTML = `<div class="card">
    <h2 style="margin-bottom:16px;">Client SDK</h2>
    <p style="color:var(--text-muted);margin-bottom:12px;">Generated TypeScript client for <strong>${model.name}</strong>.</p>
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <button class="btn btn-sm btn-secondary active" data-sdk-lang="typescript">TypeScript</button>
      <button class="btn btn-sm btn-secondary" data-sdk-lang="python">Python</button>
      <button class="btn btn-sm btn-secondary" id="btn-copy-sdk">Copy Code</button>
    </div>
    <div class="json-preview" id="sdk-output" style="max-height:500px;overflow-y:auto;">Loading...</div>
  </div>`;

  let currentLang = 'typescript';
  async function loadSDK() {
    const output = document.getElementById('sdk-output');
    output.textContent = '⏳ Generating...';
    try {
      const code = await API.get(`/api/sdk/${model.name}?lang=${currentLang}`);
      output.textContent = typeof code === 'string' ? code : JSON.stringify(code, null, 2);
    } catch (e) { output.textContent = `Error: ${e.message}`; }
  }

  container.querySelectorAll('[data-sdk-lang]').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('[data-sdk-lang]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentLang = btn.dataset.sdkLang;
      loadSDK();
    });
  });
  container.querySelector('#btn-copy-sdk').addEventListener('click', () => {
    const text = document.getElementById('sdk-output').textContent;
    navigator.clipboard.writeText(text);
    toast('SDK code copied!');
  });
  loadSDK();
}

// ============ REALTIME ============
function renderRealtimeTab(model, container) {
  container.innerHTML = `<div class="card">
    <h2 style="margin-bottom:16px;">Real-time Subscriptions</h2>
    <p style="color:var(--text-muted);margin-bottom:12px;">
      Connect via WebSocket to receive live updates on <strong>${model.name}</strong> changes.
    </p>
    <div class="form-group">
      <label>WebSocket URL</label>
      <input type="text" id="ws-url" value="ws://localhost:8000/ws/${model.name}?token=${API.token || 'YOUR_TOKEN'}" readonly style="font-family:monospace;font-size:0.8rem;">
    </div>
    <button class="btn btn-sm btn-primary" id="ws-connect">Connect</button>
    <button class="btn btn-sm btn-secondary" id="ws-disconnect" disabled>Disconnect</button>
    <div id="ws-status" style="margin-top:8px;font-size:0.85rem;color:var(--text-muted);">Disconnected</div>
    <div id="ws-log" class="response-box" style="margin-top:12px;max-height:200px;overflow-y:auto;">// Events will appear here</div>
    <h3 style="margin-top:16px;font-size:0.9rem;">JavaScript Example</h3>
    <div class="json-preview" style="font-size:0.8rem;">const ws = new WebSocket('ws://localhost:8000/ws/${model.name}?token=YOUR_JWT');\nws.onmessage = (e) => console.log(JSON.parse(e.data));\nws.onopen = () => console.log('Connected!');</div>
  </div>`;

  let ws = null;
  const logEl = document.getElementById('ws-log');
  const statusEl = document.getElementById('ws-status');
  const connectBtn = document.getElementById('ws-connect');
  const disconnectBtn = document.getElementById('ws-disconnect');

  connectBtn.addEventListener('click', () => {
    if (ws) ws.close();
    const url = document.getElementById('ws-url').value;
    try {
      ws = new WebSocket(url);
      ws.onopen = () => { statusEl.textContent = '✅ Connected'; statusEl.style.color = 'var(--mongodb-green)'; connectBtn.disabled = true; disconnectBtn.disabled = false; };
      ws.onmessage = (e) => {
        const entry = document.createElement('div');
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${e.data}`;
        logEl.appendChild(entry);
        logEl.scrollTop = logEl.scrollHeight;
      };
      ws.onclose = () => { statusEl.textContent = 'Disconnected'; statusEl.style.color = 'var(--text-muted)'; connectBtn.disabled = false; disconnectBtn.disabled = true; };
      ws.onerror = () => { statusEl.textContent = '❌ Error'; statusEl.style.color = 'var(--danger)'; };
    } catch (e) { statusEl.textContent = `❌ ${e.message}`; }
  });
  disconnectBtn.addEventListener('click', () => { if (ws) { ws.close(); ws = null; } });
}

// ============ PIPELINES ============
function renderPipelinesPage(app) {
  app.innerHTML = `<div class="header">
    <div class="header-left"><div class="logo"><div class="logo-icon">M</div><h1>Pipelines</h1></div></div>
    <div class="header-right">
      <button class="btn btn-primary" id="btn-new-pipeline">+ New Pipeline</button>
      <button class="btn btn-secondary" onclick="navigate('dashboard')">← Back</button>
    </div>
  </div><div id="pipeline-content"></div>`;

  document.getElementById('btn-new-pipeline').addEventListener('click', showPipelineBuilder);
  renderPipelinesView(document.getElementById('pipeline-content'));
}

function renderPipelinesView(container) {
  if (!store.pipelines.length) {
    container.innerHTML = `<div class="empty-state"><div class="emoji">🔧</div><h3>No pipelines</h3><p>Create aggregation pipelines with visual stages</p></div>`;
    return;
  }
  container.innerHTML = `<div class="model-grid">${store.pipelines.map(p => `
    <div class="model-card" data-pid="${p._id}">
      <h3>${p.name}</h3>
      <div class="model-meta">Collection: ${p.collection} · ${p.stages.length} stage${p.stages.length !== 1 ? 's' : ''}</div>
    </div>`).join('')}</div>`;
  container.querySelectorAll('.model-card').forEach(el => {
    el.addEventListener('click', () => showPipelineRunner(el.dataset.pid));
  });
}

function showPipelineBuilder() {
  const stages = [];
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal" style="max-width:640px;">
    <h2>New Pipeline</h2>
    <div class="form-group"><label>Pipeline Name</label><input type="text" id="pl-name" placeholder="e.g. products-by-category"></div>
    <div class="form-group"><label>Collection</label>
      <select id="pl-collection">${store.models.map(m => `<option value="${m.name}">${m.name}</option>`).join('')}</select>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <span style="font-size:0.85rem;color:var(--text-secondary);">Pipeline Stages</span>
      <button class="btn btn-sm btn-secondary" id="pl-add-stage">+ Add Stage</button>
    </div>
    <div id="pl-stages"></div>
    <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end;">
      <button class="btn btn-secondary" id="pl-cancel">Cancel</button>
      <button class="btn btn-primary" id="pl-save">Save Pipeline</button>
    </div>
  </div>`;
  document.body.appendChild(overlay);

  const stageContainer = overlay.querySelector('#pl-stages');

  function renderStages() {
    stageContainer.innerHTML = stages.map((s, i) => `
      <div class="field-item" style="flex-wrap:wrap;">
        <select class="pl-stage-type" data-idx="${i}" style="width:120px;">
          ${['match','group','sort','project','limit','skip','lookup','unwind','count','add_fields'].map(t => `<option value="${t}" ${t === s.type ? 'selected' : ''}>$${t}</option>`).join('')}
        </select>
        <input type="text" class="pl-stage-params" value="${typeof s.params === 'string' ? s.params : JSON.stringify(s.params)}" placeholder='{"field": "value"}' style="flex:1;font-family:monospace;font-size:0.8rem;">
        <button class="btn btn-sm btn-danger" data-idx="${i}">✕</button>
      </div>`).join('');
    stageContainer.querySelectorAll('.pl-stage-type').forEach(el => el.addEventListener('change', (e) => {
      stages[parseInt(e.target.dataset.idx)].type = e.target.value;
    }));
    stageContainer.querySelectorAll('.pl-stage-params').forEach(el => el.addEventListener('change', (e) => {
      try { stages[parseInt(e.target.dataset.idx)].params = JSON.parse(e.target.value); }
      catch { stages[parseInt(e.target.dataset.idx)].params = e.target.value; }
    }));
    stageContainer.querySelectorAll('.btn-danger').forEach(el => el.addEventListener('click', (e) => {
      stages.splice(parseInt(e.target.dataset.idx), 1);
      renderStages();
    }));
  }

  overlay.querySelector('#pl-add-stage').addEventListener('click', () => {
    stages.push({ type: 'match', params: {} });
    renderStages();
  });

  overlay.querySelector('#pl-cancel').addEventListener('click', () => overlay.remove());
  overlay.querySelector('#pl-save').addEventListener('click', async () => {
    const name = overlay.querySelector('#pl-name').value.trim();
    const collection = overlay.querySelector('#pl-collection').value;
    if (!name) return toast('Pipeline name required', 'error');
    try {
      await API.post('/api/pipelines/', { name, collection, stages });
      toast('Pipeline created!', 'success');
      overlay.remove();
      await loadPipelines();
      navigate('pipelines');
    } catch (e) { toast(e.message, 'error'); }
  });
  renderStages();
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
}

function showPipelineRunner(pipelineId) {
  const pipeline = store.pipelines.find(p => p._id === pipelineId);
  if (!pipeline) return;
  const model = store.models.find(m => m.name === pipeline.collection);
  if (!model) return;

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal" style="max-width:700px;">
    <h2>🔧 ${pipeline.name}</h2>
    <p style="color:var(--text-muted);font-size:0.85rem;margin-bottom:12px;">Collection: <strong>${pipeline.collection}</strong> · ${pipeline.stages.length} stages</p>
    <div class="json-preview" style="font-size:0.75rem;max-height:150px;">${JSON.stringify(pipeline.stages, null, 2)}</div>
    <div style="margin-top:12px;">
      <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px;">Override params (JSON)</label>
      <input type="text" id="pl-run-params" placeholder='{"limit": 5}' style="font-family:monospace;font-size:0.8rem;">
    </div>
    <div style="display:flex;gap:8px;margin-top:12px;">
      <button class="btn btn-primary btn-sm" id="pl-run-btn">Run Pipeline</button>
      <button class="btn btn-sm btn-danger" id="pl-delete-btn">Delete</button>
      <button class="btn btn-secondary btn-sm" id="pl-close-btn" style="margin-left:auto;">Close</button>
    </div>
    <div id="pl-run-result" class="response-box" style="margin-top:12px;max-height:300px;">// Results</div>
  </div>`;
  document.body.appendChild(overlay);

  overlay.querySelector('#pl-run-btn').addEventListener('click', async () => {
    const resp = overlay.querySelector('#pl-run-result');
    resp.textContent = '⏳ Running...';
    let params = {};
    try {
      const raw = overlay.querySelector('#pl-run-params').value.trim();
      if (raw) params = JSON.parse(raw);
    } catch { resp.textContent = 'Error: Invalid params JSON'; return; }

    try {
      const data = await API.post(`/api/pipelines/run/${pipelineId}`, params);
      resp.textContent = JSON.stringify(data, null, 2);
    } catch (e) { resp.textContent = `Error: ${e.message}`; }
  });

  overlay.querySelector('#pl-delete-btn').addEventListener('click', async () => {
    if (!confirm('Delete this pipeline?')) return;
    try {
      await API.delete(`/api/pipelines/${pipelineId}`);
      toast('Deleted', 'info');
      overlay.remove();
      await loadPipelines();
      navigate('pipelines');
    } catch (e) { toast(e.message, 'error'); }
  });

  overlay.querySelector('#pl-close-btn').addEventListener('click', () => overlay.remove());
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
}

// ============ STORAGE ============
function renderStoragePage(app) {
  app.innerHTML = `<div class="header">
    <div class="header-left"><div class="logo"><div class="logo-icon">M</div><h1>File Storage</h1></div></div>
    <div class="header-right"><button class="btn btn-secondary" onclick="navigate('dashboard')">← Back</button></div>
  </div><div id="storage-content"></div>`;
  renderStorageView(document.getElementById('storage-content'));
}

function renderStorageView(container) {
  container.innerHTML = `<div class="card">
    <h2 style="margin-bottom:12px;">Upload File</h2>
    <div class="form-group"><label>Collection (model)</label>
      <select id="storage-collection">${store.models.map(m => `<option value="${m.name}">${m.name}</option>`).join('')}</select>
    </div>
    <div class="form-group"><label>File</label><input type="file" id="storage-file"></div>
    <button class="btn btn-primary" id="storage-upload">Upload</button>
  </div>
  <div class="card">
    <h2 style="margin-bottom:12px;">Files</h2>
    <div id="storage-list"><p style="color:var(--text-muted);">Select a collection and click Upload</p></div>
  </div>`;

  document.getElementById('storage-upload').addEventListener('click', async () => {
    const collection = document.getElementById('storage-collection').value;
    const fileInput = document.getElementById('storage-file');
    if (!fileInput.files.length) return toast('Select a file', 'error');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    try {
      const res = await fetch(`/api/storage/upload/${collection}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${API.token}` },
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast('File uploaded!', 'success');
      listFiles(collection);
    } catch (e) { toast(e.message, 'error'); }
  });

  function listFiles(collection) {
    const list = document.getElementById('storage-list');
    API.get(`/api/storage/list/${collection}`).then(data => {
      if (!data.files?.length) {
        list.innerHTML = '<p style="color:var(--text-muted);">No files uploaded yet</p>';
        return;
      }
      list.innerHTML = `<div style="display:grid;gap:8px;">${data.files.map(f => `
        <div class="endpoint-card">
          <span style="flex:1;">${f.filename} <span style="color:var(--text-muted);font-size:0.8rem;">(${(f.size / 1024).toFixed(1)} KB)</span></span>
          <a href="/api/storage/download/${f.file_id}" class="btn btn-sm btn-secondary" target="_blank">Download</a>
          <button class="btn btn-sm btn-danger" data-fid="${f.file_id}" style="margin-left:4px;">Delete</button>
        </div>`).join('')}</div>`;
      list.querySelectorAll('[data-fid]').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (!confirm('Delete this file?')) return;
          try {
            await API.delete(`/api/storage/delete/${btn.dataset.fid}`);
            toast('Deleted', 'info');
            listFiles(collection);
          } catch (e) { toast(e.message, 'error'); }
        });
      });
    }).catch(e => { list.innerHTML = `<p style="color:var(--danger);">Error: ${e.message}</p>`; });
  }
}

// Start
init();
window.showModelBuilder = showModelBuilder;
