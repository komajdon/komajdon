export type FieldType = 'string' | 'number' | 'boolean' | 'date' | 'array' | 'object' | 'relation'
export type RelationType = 'has_one' | 'has_many' | 'belongs_to'

export interface ValidationRule {
  required?: boolean
  unique?: boolean
  min_length?: number
  max_length?: number
  minimum?: number
  maximum?: number
  pattern?: string
  enum?: string[]
}

export interface Relationship {
  type: RelationType
  target_model: string
  foreign_key: string
  through?: string
}

export interface IndexSpec {
  field: string
  direction: 1 | -1
  unique?: boolean
}

export interface FieldDefinition {
  name: string
  type: FieldType
  required?: boolean
  default?: unknown
  validation?: ValidationRule
  relation?: Relationship
  indexed?: boolean
}

export interface ModelSchema {
  _id: string
  name: string
  fields: FieldDefinition[]
  indexes: IndexSpec[]
  auth_protected: boolean
  realtime_enabled: boolean
  created_at: string
}

export interface GenerateRequest {
  name: string
  fields: FieldDefinition[]
  indexes?: IndexSpec[]
  auth_protected?: boolean
  realtime_enabled?: boolean
}

export interface AggregationStage {
  type: string
  params: Record<string, unknown>
}

export interface AggregationPipeline {
  _id: string
  name: string
  collection: string
  stages: AggregationStage[]
  created_at: string
}

export interface User {
  id: string
  email: string
  role: string
  permissions?: string[]
  email_verified?: boolean
  is_active?: boolean
  created_at?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface UploadedFile {
  file_id: string
  filename: string
  size: number
  content_type: string
  upload_date: string
}

export interface ApiEndpoint {
  method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  path: string
  desc: string
  hasBody?: boolean
  hasQuery?: boolean
}

export interface Project {
  id: string
  name: string
  slug: string
  description: string
  created_by: string
  created_at: string
}

export interface Role {
  id: string
  name: string
  description: string
  permissions: string[]
  is_default: boolean
  created_at: string
}

export interface PermissionInfo {
  key: string
  description: string
}

export interface ApiKey {
  id: string
  name: string
  key_preview: string
  role: string
  permissions: string[]
  is_active: boolean
  last_used_at: string | null
  created_at: string
}

export interface RateLimitRule {
  id: string
  endpoint: string
  method: string
  max_requests: number
  window_seconds: number
  enabled: boolean
  description: string
  created_at: string
  updated_at: string
}
