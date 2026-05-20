from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi.responses import PlainTextResponse
from app.database import get_db
from app.auth.deps import require_user
from app.auth.projects import optional_project

router = APIRouter(prefix="/api/sdk", tags=["sdk"])

TS_TEMPLATE = r'''export interface {model} {{
{fields}
}}

export class {model}Api {{
  private baseUrl: string;
  private token: string | null;

  constructor(baseUrl: string, token: string | null = null) {{
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.token = token;
  }}

  private get headers(): Record<string, string> {{
    const h: Record<string, string> = {{ 'Content-Type': 'application/json' }};
    if (this.token) h['Authorization'] = `Bearer ${{this.token}}`;
    return h;
  }}

  async list(params?: {{ skip?: number; limit?: number; sort?: string; filter?: string[]; populate?: string; fields?: string }}): Promise<{model}[]> {{
    const qs = new URLSearchParams();
    if (params?.skip) qs.set('skip', String(params.skip));
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.sort) qs.set('sort', params.sort);
    if (params?.populate) qs.set('populate', params.populate);
    if (params?.fields) qs.set('fields', params.fields);
    if (params?.filter) params.filter.forEach(f => qs.append('filter', f));
    const url = `${{this.baseUrl}}/api/{endpoint}?${{qs}}`;
    const res = await fetch(url, {{ headers: this.headers }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async get(id: string, params?: {{ populate?: string; fields?: string }}): Promise<{model}> {{
    const qs = new URLSearchParams();
    if (params?.populate) qs.set('populate', params.populate);
    if (params?.fields) qs.set('fields', params.fields);
    const q = qs.toString();
    const url = `${{this.baseUrl}}/api/{endpoint}/${{id}}` + (q ? `?${{q}}` : '');
    const res = await fetch(url, {{ headers: this.headers }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async create(data: Partial<{model}>): Promise<{model}> {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}`, {{
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(data),
    }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async update(id: string, data: Partial<{model}>): Promise<{model}> {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/${{id}}`, {{
      method: 'PATCH',
      headers: this.headers,
      body: JSON.stringify(data),
    }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async replace(id: string, data: {model}): Promise<{model}> {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/${{id}}`, {{
      method: 'PUT',
      headers: this.headers,
      body: JSON.stringify(data),
    }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async delete(id: string, hard: boolean = false): Promise<void> {{
    const qs = hard ? '?hard=true' : '';
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/${{id}}${{qs}}`, {{
      method: 'DELETE',
      headers: this.headers,
    }});
    if (!res.ok) throw new Error(await res.text());
  }}

  async restore(id: string): Promise<{model}> {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/${{id}}/restore`, {{
      method: 'POST',
      headers: this.headers,
    }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async listDeleted(params?: {{ skip?: number; limit?: number }}): Promise<{model}[]> {{
    const qs = new URLSearchParams();
    if (params?.skip) qs.set('skip', String(params.skip));
    if (params?.limit) qs.set('limit', String(params.limit));
    qs.set('include_deleted', 'true');
    const url = `${{this.baseUrl}}/api/{endpoint}?${{qs}}`;
    const res = await fetch(url, {{ headers: this.headers }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async bulkCreate(items: Partial<{model}>[]): Promise<{model}[]> {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/bulk`, {{
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(items),
    }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async bulkUpdate(ids: string[], data: Partial<{model}>): Promise<void> {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/bulk`, {{
      method: 'PATCH',
      headers: this.headers,
      body: JSON.stringify({{ ids, data }}),
    }});
    if (!res.ok) throw new Error(await res.text());
  }}

  async bulkDelete(ids: string[], hard: boolean = false): Promise<void> {{
    const qs = hard ? '?hard=true' : '';
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/bulk${{qs}}`, {{
      method: 'DELETE',
      headers: this.headers,
      body: JSON.stringify({{ ids }}),
    }});
    if (!res.ok) throw new Error(await res.text());
  }}
}}

// Usage:
// const api = new {model}Api('http://localhost:8000', 'your-jwt-token');
// const items = await api.list({{ filter: ['status__eq=active'] }});
// const item = await api.create({{ title: 'Hello' }});
'''

PY_TEMPLATE = '''import httpx


class {model}:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self._endpoint = f'{{self.base_url}}/api/{endpoint}'

    @property
    def _headers(self):
        h = {{'Content-Type': 'application/json'}}
        if self.token:
            h['Authorization'] = f'Bearer {{self.token}}'
        return h

    def list(self, skip=0, limit=100, sort=None, populate=None, fields=None, **filters):
        params = {{'skip': skip, 'limit': limit}}
        if sort:
            params['sort'] = sort
        if populate:
            params['populate'] = populate
        if fields:
            params['fields'] = fields
        for k, v in filters.items():
            params.setdefault('filter', []).append(f'{{k}}__eq={{v}}')
        r = httpx.get(f'{{self._endpoint}}', headers=self._headers, params=params)
        r.raise_for_status()
        return r.json()

    def get(self, id: str, populate=None, fields=None):
        params = {{}}
        if populate:
            params['populate'] = populate
        if fields:
            params['fields'] = fields
        r = httpx.get(f'{{self._endpoint}}/{{id}}', headers=self._headers, params=params)
        r.raise_for_status()
        return r.json()

    def create(self, **data):
        r = httpx.post(f'{{self._endpoint}}', headers=self._headers, json=data)
        r.raise_for_status()
        return r.json()

    def update(self, id: str, **data):
        r = httpx.patch(f'{{self._endpoint}}/{{id}}', headers=self._headers, json=data)
        r.raise_for_status()
        return r.json()

    def replace(self, id: str, **data):
        r = httpx.put(f'{{self._endpoint}}/{{id}}', headers=self._headers, json=data)
        r.raise_for_status()
        return r.json()

    def delete(self, id: str, hard: bool = False):
        params = {{'hard': 'true'}} if hard else {{}}
        r = httpx.delete(f'{{self._endpoint}}/{{id}}', headers=self._headers, params=params)
        r.raise_for_status()

    def restore(self, id: str):
        r = httpx.post(f'{{self._endpoint}}/{{id}}/restore', headers=self._headers)
        r.raise_for_status()
        return r.json()

    def list_deleted(self, skip=0, limit=100):
        params = {{'include_deleted': 'true', 'skip': skip, 'limit': limit}}
        r = httpx.get(f'{{self._endpoint}}', headers=self._headers, params=params)
        r.raise_for_status()
        return r.json()


    def bulk_create(self, items: list[dict]) -> list[dict]:
        r = httpx.post(f'{{self._endpoint}}/bulk', headers=self._headers, json=items)
        r.raise_for_status()
        return r.json()

    def bulk_update(self, ids: list[str], **data):
        r = httpx.patch(f'{{self._endpoint}}/bulk', headers=self._headers, json={{{{ 'ids': ids, 'data': data }}}})
        r.raise_for_status()

    def bulk_delete(self, ids: list[str], hard: bool = False):
        params = {{'hard': 'true'}} if hard else {{}}
        r = httpx.delete(f'{{self._endpoint}}/bulk', headers=self._headers, params=params, json={{{{ 'ids': ids }}}})
        r.raise_for_status()


# Usage:
# api = {model}('http://localhost:8000', token='your-jwt-token')
# items = api.list(status='active')
# item = api.create(title='Hello')
'''

JS_TEMPLATE = r'''/**
 * @typedef {{Object}} {model}
{comment_fields}
 */

class {model}Api {{
  constructor(baseUrl, token = null) {{
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.token = token;
  }}

  get _headers() {{
    const h = {{ 'Content-Type': 'application/json' }};
    if (this.token) h['Authorization'] = `Bearer ${{this.token}}`;
    return h;
  }}

  async list(params = {{}}) {{
    const qs = new URLSearchParams();
    if (params.skip) qs.set('skip', params.skip);
    if (params.limit) qs.set('limit', params.limit);
    if (params.sort) qs.set('sort', params.sort);
    if (params.filter) params.filter.forEach(f => qs.append('filter', f));
    const url = `${{this.baseUrl}}/api/{endpoint}?${{qs}}`;
    const res = await fetch(url, {{ headers: this._headers }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async get(id) {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/${{id}}`, {{ headers: this._headers }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async create(data) {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}`, {{
      method: 'POST', headers: this._headers, body: JSON.stringify(data),
    }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async update(id, data) {{
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/${{id}}`, {{
      method: 'PATCH', headers: this._headers, body: JSON.stringify(data),
    }});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }}

  async delete(id, hard = false) {{
    const qs = hard ? '?hard=true' : '';
    const res = await fetch(`${{this.baseUrl}}/api/{endpoint}/${{id}}${{qs}}`, {{
      method: 'DELETE', headers: this._headers,
    }});
    if (!res.ok) throw new Error(await res.text());
  }}
}}

// Usage:
// const api = new {model}Api('http://localhost:8000', 'your-jwt-token');
// const items = await api.list({{ filter: ['status__eq=active'] }});
'''

CURL_TEMPLATE = r'''# {model} API — curl Examples

# ── Authentication ───────────────────────────────
# Replace YOUR_TOKEN with a JWT from POST /api/auth/signin

# ── List {model} ─────────────────────────────────
curl -H "Authorization: Bearer YOUR_TOKEN" \\
  "{base_url}/api/{endpoint}"

# ── List with filters ────────────────────────────
curl -H "Authorization: Bearer YOUR_TOKEN" \\
  "{base_url}/api/{endpoint}?filter=status__eq=active&limit=10"

# ── Get by ID ────────────────────────────────────
curl -H "Authorization: Bearer YOUR_TOKEN" \\
  "{base_url}/api/{endpoint}/DOCUMENT_ID"

# ── Create ───────────────────────────────────────
curl -X POST -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{{"field1": "value1", "field2": "value2"}}' \\
  "{base_url}/api/{endpoint}"

# ── Update (PATCH) ──────────────────────────────
curl -X PATCH -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{{"field1": "new-value"}}' \\
  "{base_url}/api/{endpoint}/DOCUMENT_ID"

# ── Delete (soft) ───────────────────────────────
curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" \\
  "{base_url}/api/{endpoint}/DOCUMENT_ID"

# ── Delete (hard) ───────────────────────────────
curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" \\
  "{base_url}/api/{endpoint}/DOCUMENT_ID?hard=true"
'''


def _gen_typescript(model_name: str, fields: list[dict]) -> str:
    type_map = {
        "string": "string", "number": "number", "boolean": "boolean",
        "date": "string", "array": "any[]", "object": "Record<string, any>", "relation": "string",
    }
    field_lines = []
    for f in fields:
        ts_type = type_map.get(f.get("type", "string"), "any")
        opt = "" if f.get("required") else "?"
        field_lines.append(f"  {f['name']}{opt}: {ts_type};")
    return TS_TEMPLATE.format(
        model=model_name,
        endpoint=model_name.lower(),
        fields="\n".join(field_lines),
    )


def _gen_python(model_name: str, fields: list[dict]) -> str:
    return PY_TEMPLATE.format(
        model=model_name,
        endpoint=model_name.lower(),
    )


def _gen_javascript(model_name: str, fields: list[dict]) -> str:
    comment_lines = []
    for f in fields:
        opt = " (optional)" if not f.get("required") else ""
        escaped_type = f.get('type', 'any').replace('{', '{{').replace('}', '}}')
        comment_lines.append(f" * @property {{{escaped_type}}} {f['name']}{opt}")
    return JS_TEMPLATE.format(
        model=model_name,
        endpoint=model_name.lower(),
        comment_fields="\n".join(comment_lines),
    )


def _gen_curl(model_name: str) -> str:
    return CURL_TEMPLATE.format(
        model=model_name,
        endpoint=model_name.lower(),
        base_url="http://localhost:8000",
    )


@router.get("/{model_name}")
async def generate_sdk(
    model_name: str,
    lang: str = "typescript",
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    q = {"name": model_name}
    if project:
        q["project_id"] = str(project["_id"])
    schema = await db["_schemas"].find_one(q)
    if not schema:
        return PlainTextResponse("Model not found", status_code=404)
    fields = schema.get("fields", [])

    generators = {
        "typescript": _gen_typescript,
        "python": _gen_python,
        "javascript": _gen_javascript,
        "js": _gen_javascript,
        "curl": _gen_curl,
    }
    gen = generators.get(lang, _gen_typescript)
    code = gen(model_name, fields) if lang != "curl" else gen(model_name)

    media_type = "text/plain"
    if lang == "curl":
        media_type = "text/x-shellscript"

    return PlainTextResponse(code, media_type=media_type)
