# DB Schema Reference — Mathoms AI

> **Auto-gerado** por `dev/generate_db_schema_reference.py`. Não edite manualmente — rode `make update-db-schema-reference` e comite o diff.

Referência canônica de schema do banco. Cobre todos os models registrados em `backend/app/models/` via `Base.metadata`.

**Total de tabelas:** 30

---

## Índice

- [`audit_logs`](#auditlogs)
- [`bank_accounts`](#bankaccounts)
- [`categories`](#categories)
- [`category_keywords`](#categorykeywords)
- [`documents`](#documents)
- [`family_members`](#familymembers)
- [`feature_flags`](#featureflags)
- [`goals`](#goals)
- [`institution_configs`](#institutionconfigs)
- [`kanban_items`](#kanbanitems)
- [`llm_configs`](#llmconfigs)
- [`notifications`](#notifications)
- [`password_vault`](#passwordvault)
- [`pipeline_artifacts`](#pipelineartifacts)
- [`pipeline_configs`](#pipelineconfigs)
- [`pipeline_runs`](#pipelineruns)
- [`pipeline_stage_logs`](#pipelinestagelogs)
- [`report_layouts`](#reportlayouts)
- [`report_notes`](#reportnotes)
- [`reports`](#reports)
- [`stage_reviews`](#stagereviews)
- [`task_attachments`](#taskattachments)
- [`task_suggestions`](#tasksuggestions)
- [`tasks`](#tasks)
- [`transaction_overrides`](#transactionoverrides)
- [`transfer_configs`](#transferconfigs)
- [`users`](#users)
- [`workspace_invitations`](#workspaceinvitations)
- [`workspace_members`](#workspacemembers)
- [`workspaces`](#workspaces)

---

## Tabelas

### `audit_logs`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | yes | — | FK→workspaces.id, INDEX |
| `actor_user_id` | `VARCHAR(36)` | yes | — | FK→users.id, INDEX |
| `action` | `VARCHAR(64)` | no | — | INDEX |
| `resource_type` | `VARCHAR(64)` | no | — | — |
| `resource_id` | `VARCHAR(255)` | yes | — | INDEX |
| `ip_address` | `VARCHAR(45)` | yes | — | — |
| `user_agent` | `TEXT` | yes | — | — |
| `details` | `JSON` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | INDEX |

**Constraints:**

- FOREIGN KEY (actor_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_audit_logs_action` (action)
- `ix_audit_logs_actor_user_id` (actor_user_id)
- `ix_audit_logs_created_at` (created_at)
- `ix_audit_logs_resource_id` (resource_id)
- `ix_audit_logs_workspace_id` (workspace_id)

### `bank_accounts`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `member_id` | `VARCHAR(36)` | no | — | FK→family_members.id, INDEX |
| `institution_code` | `VARCHAR(50)` | no | — | — |
| `account_type` | `VARCHAR(100)` | no | — | — |
| `agency` | `VARCHAR(20)` | yes | — | — |
| `account_number` | `VARCHAR(30)` | yes | — | — |
| `label` | `VARCHAR(255)` | yes | — | — |

**Constraints:**

- FOREIGN KEY (member_id) REFERENCES family_members.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_bank_accounts_member_id` (member_id)

### `categories`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `code` | `VARCHAR(50)` | no | — | — |
| `name` | `VARCHAR(100)` | no | — | — |
| `category_type` | `VARCHAR(10)` | no | — | — |
| `monthly_cap` | `FLOAT` | yes | — | — |
| `order` | `INTEGER` | no | `0` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_categories_workspace_id` (workspace_id)

### `category_keywords`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `category_id` | `VARCHAR(36)` | no | — | FK→categories.id, INDEX |
| `keyword` | `TEXT` | no | — | — |

**Constraints:**

- FOREIGN KEY (category_id) REFERENCES categories.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_category_keywords_category_id` (category_id)

### `documents`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `original_name` | `VARCHAR(500)` | no | — | — |
| `stored_path` | `TEXT` | yes | — | — |
| `doc_type` | `VARCHAR(18)` | yes | `<DocumentType.other: 'other'>` | — |
| `bank_code` | `VARCHAR(50)` | yes | — | — |
| `period` | `VARCHAR(50)` | yes | — | — |
| `status` | `VARCHAR(14)` | no | `<DocumentStatus.uploaded: 'uploaded'>` | INDEX |
| `classification_meta` | `JSON` | yes | — | — |
| `file_size_bytes` | `INTEGER` | yes | — | — |
| `content_hash` | `VARCHAR(64)` | yes | — | INDEX |
| `content_type` | `VARCHAR(100)` | yes | — | — |
| `error_message` | `TEXT` | yes | — | — |
| `classification_confidence` | `FLOAT` | yes | — | — |
| `needs_review` | `BOOLEAN` | no | server: `0` | INDEX |
| `possible_duplicate_of_id` | `VARCHAR(36)` | yes | — | INDEX |
| `uploaded_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `pipeline_last_run_at` | `DATETIME` | yes | — | — |
| `pipeline_e2_extract_ok` | `BOOLEAN` | yes | — | — |
| `pipeline_extract_notes` | `TEXT` | yes | — | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_documents_content_hash` (content_hash)
- `ix_documents_needs_review` (needs_review)
- `ix_documents_possible_duplicate_of_id` (possible_duplicate_of_id)
- `ix_documents_status` (status)
- `ix_documents_workspace_id` (workspace_id)

### `family_members`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `key` | `VARCHAR(50)` | no | — | — |
| `full_name` | `VARCHAR(255)` | no | — | — |
| `short_name` | `VARCHAR(100)` | no | — | — |
| `cpf_encrypted` | `TEXT` | yes | — | — |
| `birth_date` | `DATE` | yes | — | — |
| `role` | `VARCHAR(20)` | no | `'titular'` | — |
| `order` | `INTEGER` | no | `0` | — |
| `extra` | `JSON` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_family_members_workspace_id` (workspace_id)

### `feature_flags`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `flags_json` | `JSON` | no | callable: `dict` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id) — `uq_feature_flags_workspace`

**Indexes:**

- `ix_feature_flags_workspace_id` (workspace_id)

### `goals`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `type` | `VARCHAR(64)` | no | — | INDEX |
| `params_json` | `JSON` | no | — | — |
| `derived_json` | `JSON` | no | — | — |
| `effective_from` | `DATE` | no | — | INDEX |
| `effective_to` | `DATE` | yes | — | — |
| `created_by` | `VARCHAR(36)` | yes | — | FK→users.id |
| `notes` | `TEXT` | yes | — | — |
| `is_template` | `BOOLEAN` | no | `False` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (created_by) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_goals_effective_from` (effective_from)
- `ix_goals_type` (type)
- `ix_goals_workspace_id` (workspace_id)
- `ix_goals_ws_type_effective_from` (workspace_id, type, effective_from)
- `ix_goals_ws_type_effective_to` (workspace_id, type, effective_to)

### `institution_configs`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, UNIQUE, INDEX |
| `config_json` | `JSON` | no | callable: `dict` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- UNIQUE `ix_institution_configs_workspace_id` (workspace_id)

### `kanban_items`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `report_id` | `VARCHAR(36)` | no | — | FK→reports.id, INDEX |
| `titulo` | `VARCHAR(500)` | no | — | — |
| `coluna` | `VARCHAR(32)` | no | `'a_fazer'` | — |
| `prioridade` | `VARCHAR(16)` | yes | — | — |
| `prazo` | `DATE` | yes | — | — |
| `categoria` | `VARCHAR(64)` | yes | — | — |
| `essencial` | `VARCHAR(1)` | yes | — | — |
| `ordem` | `INTEGER` | no | `0` | — |
| `created_by` | `VARCHAR(36)` | yes | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (created_by) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (report_id) REFERENCES reports.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_kanban_items_report_id` (report_id)
- `ix_kanban_items_workspace_id` (workspace_id)
- `ix_kanban_items_ws_report_col` (workspace_id, report_id, coluna)

### `llm_configs`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, UNIQUE, INDEX |
| `provider` | `VARCHAR(50)` | no | `'anthropic'` | — |
| `api_key_encrypted` | `TEXT` | no | — | — |
| `model_name` | `VARCHAR(100)` | no | `'claude-sonnet-4-20250514'` | — |
| `max_tokens` | `INTEGER` | no | `4096` | — |
| `temperature` | `FLOAT` | no | `0.1` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- UNIQUE `ix_llm_configs_workspace_id` (workspace_id)

### `notifications`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `severity` | `VARCHAR(20)` | no | — | — |
| `title` | `VARCHAR(500)` | no | — | — |
| `message` | `TEXT` | no | — | — |
| `source` | `VARCHAR(50)` | yes | — | — |
| `is_read` | `BOOLEAN` | no | `False` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_notifications_workspace_id` (workspace_id)

### `password_vault`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `label` | `VARCHAR(255)` | no | — | — |
| `encrypted_password` | `TEXT` | no | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_password_vault_workspace_id` (workspace_id)

### `pipeline_artifacts`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `INTEGER` | no | — | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `pipeline_run_id` | `VARCHAR(36)` | no | — | FK→pipeline_runs.id, INDEX |
| `stage` | `VARCHAR(50)` | no | — | — |
| `artifact_key` | `VARCHAR(255)` | no | — | — |
| `document_id` | `VARCHAR(36)` | yes | — | FK→documents.id |
| `content_json` | `JSON` | no | — | — |
| `schema_version` | `VARCHAR(20)` | yes | — | — |
| `byte_size` | `INTEGER` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (document_id) REFERENCES documents.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (pipeline_run_id, stage, artifact_key) — `uq_pipeline_artifacts_run_stage_key`

**Indexes:**

- `ix_pipeline_artifacts_document_id` (document_id)
- `ix_pipeline_artifacts_pipeline_run_id` (pipeline_run_id)
- `ix_pipeline_artifacts_workspace_id` (workspace_id)
- `ix_pipeline_artifacts_workspace_stage_key` (workspace_id, stage, artifact_key)

### `pipeline_configs`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, UNIQUE, INDEX |
| `config_json` | `JSON` | no | callable: `dict` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- UNIQUE `ix_pipeline_configs_workspace_id` (workspace_id)

### `pipeline_runs`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `status` | `VARCHAR(15)` | no | `<PipelineRunStatus.pending: 'pending'>` | — |
| `current_stage` | `VARCHAR(50)` | yes | — | — |
| `failed_at_stage` | `VARCHAR(50)` | yes | — | — |
| `config_snapshot` | `JSON` | yes | — | — |
| `total_documents` | `INTEGER` | yes | — | — |
| `reprocess_all` | `BOOLEAN` | no | `False` | — |
| `incremental` | `BOOLEAN` | no | `False` | — |
| `incremental_doc_ids` | `JSON` | yes | — | — |
| `started_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `completed_at` | `DATETIME` | yes | — | — |
| `tier_at_run` | `VARCHAR(20)` | no | `'free'` | — |
| `paused_at_stage` | `VARCHAR(50)` | yes | — | — |
| `celery_task_id` | `VARCHAR(255)` | yes | — | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_pipeline_runs_workspace_id` (workspace_id)

### `pipeline_stage_logs`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `pipeline_run_id` | `VARCHAR(36)` | no | — | FK→pipeline_runs.id, INDEX |
| `stage` | `VARCHAR(50)` | no | — | — |
| `status` | `VARCHAR(17)` | no | `<PipelineStageStatus.pending: 'pending'>` | — |
| `output_summary` | `JSON` | yes | — | — |
| `errors` | `TEXT` | yes | — | — |
| `duration_ms` | `INTEGER` | yes | — | — |
| `started_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `completed_at` | `DATETIME` | yes | — | — |

**Constraints:**

- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_pipeline_stage_logs_pipeline_run_id` (pipeline_run_id)

### `report_layouts`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, UNIQUE, INDEX |
| `config_json` | `JSON` | no | callable: `dict` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- UNIQUE `ix_report_layouts_workspace_id` (workspace_id)

### `report_notes`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `report_id` | `VARCHAR(36)` | no | — | FK→reports.id |
| `author_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |
| `content` | `TEXT` | no | `''` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (author_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (report_id) REFERENCES reports.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, report_id) — `uq_report_notes_ws_report`

**Indexes:**

- `ix_report_notes_workspace_id` (workspace_id)

### `reports`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id |
| `pipeline_run_id` | `VARCHAR(36)` | yes | — | FK→pipeline_runs.id |
| `title` | `VARCHAR(255)` | no | — | — |
| `period` | `VARCHAR(50)` | yes | — | — |
| `analysis_artifact_id` | `INTEGER` | yes | — | FK→pipeline_artifacts.id |
| `tasks_snapshot_json` | `JSON` | yes | — | — |
| `premissas_snapshot_json` | `JSON` | yes | — | — |
| `score` | `FLOAT` | yes | — | — |
| `patrimonio_liquido` | `FLOAT` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (analysis_artifact_id) REFERENCES pipeline_artifacts.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

### `stage_reviews`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `pipeline_run_id` | `VARCHAR(36)` | no | — | FK→pipeline_runs.id, INDEX |
| `stage` | `VARCHAR(50)` | no | — | — |
| `status` | `VARCHAR(8)` | no | `<StageReviewStatus.pending: 'pending'>` | — |
| `original_output_json` | `JSON` | yes | — | — |
| `edited_output_json` | `JSON` | yes | — | — |
| `validation_errors` | `TEXT` | yes | — | — |
| `reviewer_notes` | `TEXT` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `reviewed_at` | `DATETIME` | yes | — | — |

**Constraints:**

- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_stage_reviews_pipeline_run_id` (pipeline_run_id)

### `task_attachments`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `task_id` | `VARCHAR(36)` | no | — | FK→tasks.id, INDEX |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `storage_path` | `VARCHAR(500)` | no | — | — |
| `original_filename` | `VARCHAR(255)` | no | — | — |
| `content_type` | `VARCHAR(128)` | yes | — | — |
| `size_bytes` | `INTEGER` | yes | — | — |
| `uploaded_by` | `VARCHAR(36)` | yes | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (task_id) REFERENCES tasks.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (uploaded_by) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_task_attachments_task_id` (task_id)
- `ix_task_attachments_workspace_id` (workspace_id)

### `task_suggestions`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `proposed_payload` | `JSON` | no | — | — |
| `source` | `VARCHAR(32)` | no | — | — |
| `source_run_id` | `VARCHAR(36)` | yes | — | — |
| `status` | `VARCHAR(32)` | no | `'pending'` | INDEX |
| `rejection_reason` | `TEXT` | yes | — | — |
| `approved_task_id` | `VARCHAR(36)` | yes | — | FK→tasks.id |
| `reviewed_by` | `VARCHAR(36)` | yes | — | FK→users.id |
| `reviewed_at` | `DATETIME` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (approved_task_id) REFERENCES tasks.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (reviewed_by) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_suggestions_ws_status` (workspace_id, status)
- `ix_task_suggestions_status` (status)
- `ix_task_suggestions_workspace_id` (workspace_id)

### `tasks`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `number` | `INTEGER` | no | — | — |
| `title` | `VARCHAR(500)` | no | — | — |
| `description` | `TEXT` | yes | — | — |
| `category` | `VARCHAR(64)` | no | — | INDEX |
| `priority` | `VARCHAR(1)` | no | — | INDEX |
| `deadline_kind` | `VARCHAR(32)` | no | `'UNSCHEDULED'` | — |
| `deadline_date` | `DATE` | yes | — | INDEX |
| `deadline_label` | `VARCHAR(128)` | yes | — | — |
| `status` | `VARCHAR(32)` | no | `'pending'` | INDEX |
| `status_reason` | `TEXT` | yes | — | — |
| `ref` | `VARCHAR(255)` | yes | — | — |
| `parent_task_id` | `VARCHAR(36)` | yes | — | FK→tasks.id, INDEX |
| `related_transaction_id` | `VARCHAR(36)` | yes | — | — |
| `related_goal_id` | `VARCHAR(36)` | yes | — | FK→goals.id |
| `assigned_to` | `VARCHAR(36)` | yes | — | FK→family_members.id |
| `created_from` | `VARCHAR(32)` | no | `'manual'` | — |
| `source_suggestion_id` | `VARCHAR(36)` | yes | — | — |
| `completed_at` | `DATETIME` | yes | — | — |
| `cancelled_at` | `DATETIME` | yes | — | — |
| `created_by` | `VARCHAR(36)` | yes | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (assigned_to) REFERENCES family_members.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (created_by) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (parent_task_id) REFERENCES tasks.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (related_goal_id) REFERENCES goals.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, number) — `uq_task_ws_number`

**Indexes:**

- `ix_tasks_category` (category)
- `ix_tasks_deadline_date` (deadline_date)
- `ix_tasks_parent_task_id` (parent_task_id)
- `ix_tasks_priority` (priority)
- `ix_tasks_status` (status)
- `ix_tasks_workspace_id` (workspace_id)
- `ix_tasks_ws_priority_status` (workspace_id, priority, status)
- `ix_tasks_ws_status_deadline` (workspace_id, status, deadline_date)

### `transaction_overrides`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `transaction_hash` | `VARCHAR(64)` | no | — | INDEX |
| `original_category` | `VARCHAR(255)` | no | — | — |
| `new_category` | `VARCHAR(255)` | no | — | — |
| `notes` | `TEXT` | yes | — | — |
| `reviewed` | `BOOLEAN` | no | `True` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, transaction_hash) — `uq_override_ws_hash`

**Indexes:**

- `ix_transaction_overrides_transaction_hash` (transaction_hash)
- `ix_transaction_overrides_workspace_id` (workspace_id)

### `transfer_configs`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, UNIQUE, INDEX |
| `config_json` | `JSON` | no | callable: `dict` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- UNIQUE `ix_transfer_configs_workspace_id` (workspace_id)

### `users`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `email` | `VARCHAR(255)` | no | — | UNIQUE, INDEX |
| `hashed_password` | `VARCHAR(255)` | no | — | — |
| `full_name` | `VARCHAR(255)` | no | — | — |
| `is_active` | `BOOLEAN` | no | `True` | — |
| `is_developer` | `BOOLEAN` | no | server: `false` | — |
| `token_version` | `INTEGER` | no | server: `0` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Indexes:**

- UNIQUE `ix_users_email` (email)

### `workspace_invitations`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `email` | `VARCHAR(255)` | no | — | INDEX |
| `role` | `VARCHAR(32)` | no | — | — |
| `token_hash` | `VARCHAR(64)` | no | — | UNIQUE, INDEX |
| `invited_by` | `VARCHAR(36)` | yes | — | FK→users.id |
| `expires_at` | `DATETIME` | no | — | — |
| `accepted_at` | `DATETIME` | yes | — | — |
| `accepted_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |
| `revoked_at` | `DATETIME` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (accepted_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (invited_by) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_workspace_invitations_email` (email)
- UNIQUE `ix_workspace_invitations_token_hash` (token_hash)
- `ix_workspace_invitations_workspace_id` (workspace_id)
- `ix_workspace_invitations_ws_email` (workspace_id, email)

### `workspace_members`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `user_id` | `VARCHAR(36)` | no | — | FK→users.id, INDEX |
| `role` | `VARCHAR(32)` | no | `'member'` | — |
| `invited_by` | `VARCHAR(36)` | yes | — | FK→users.id |
| `joined_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (invited_by) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (user_id) REFERENCES users.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, user_id) — `uq_workspace_member`

**Indexes:**

- `ix_workspace_members_user_id` (user_id)
- `ix_workspace_members_workspace_id` (workspace_id)
- `ix_workspace_members_ws_user` (workspace_id, user_id)

### `workspaces`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `name` | `VARCHAR(255)` | no | — | — |
| `family_surname` | `VARCHAR(255)` | yes | — | — |
| `owner_id` | `VARCHAR(36)` | no | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `use_db_artifacts_override` | `BOOLEAN` | yes | — | — |
| `deleted_at` | `DATETIME` | yes | — | INDEX |

**Constraints:**

- FOREIGN KEY (owner_id) REFERENCES users.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_workspaces_deleted_at` (deleted_at)

---

## Auditoria de risco (A6f.4 · R20)

Três categorias que quebram portabilidade language-neutral. Zero ocorrências nas 3 primeiras é o alvo; listagens positivas indicam trabalho pendente.

### 1. `PickleType` / `TypeDecorator` exótico (bloqueante)

✅ **Zero ocorrências.** Schema é 100% nativo SQL.

### 2. Timestamps naive (sem `timezone=True`)

✅ **Zero ocorrências.** Todos os `DateTime` usam `timezone=True` (UTC-aware em Python, `TIMESTAMP WITH TIME ZONE` no SQL quando o dialeto suporta).

### 3. Enums — nativo SQLAlchemy `Enum` vs `VARCHAR + CHECK`

Schema usa `SQLAlchemy Enum()` nativo (Python enum → DB enum ou `VARCHAR + CHECK` dependendo do dialect). Em Postgres vira um TYPE real; em SQLite degrada para `VARCHAR + CHECK`. Portável para Go via tipo alias `type Status string` + constantes.

- `documents.doc_type → (bank_statement, credit_card_bill, e1_5_baseline_json, e1_members_json, investment_report, irpf, other)`
- `documents.status → (classifying, error, needs_password, processed, processing, ready, unlocking, uploaded)`
- `pipeline_runs.status → (cancelled, completed, failed, needs_review, partial_failure, pending, resuming, running)`
- `pipeline_stage_logs.status → (completed, failed, needs_review, pending, running, skipped, skipped_free_tier)`
- `stage_reviews.status → (approved, edited, pending)`

### 4. Colunas JSON (observação, não risco)

Campos JSON exigem schema explícito (documentado em `config/schemas/*.json` ou docstring do model) para serem portáveis cross-language.

- `audit_logs.details`
- `documents.classification_meta`
- `family_members.extra`
- `feature_flags.flags_json`
- `goals.derived_json`
- `goals.params_json`
- `institution_configs.config_json`
- `pipeline_artifacts.content_json`
- `pipeline_configs.config_json`
- `pipeline_runs.config_snapshot`
- `pipeline_runs.incremental_doc_ids`
- `pipeline_stage_logs.output_summary`
- `report_layouts.config_json`
- `reports.premissas_snapshot_json`
- `reports.tasks_snapshot_json`
- `stage_reviews.edited_output_json`
- `stage_reviews.original_output_json`
- `task_suggestions.proposed_payload`
- `transfer_configs.config_json`

---

## Equivalentes Go (referência para migração futura)

Mapeamento mecânico de cada tabela para `type XXX struct`. Nullable vira ponteiro (`*T`). `JSON` vira `json.RawMessage`. `DateTime(timezone=True)` vira `time.Time`. `Numeric` vira `decimal.Decimal` (pacote `github.com/shopspring/decimal`).

> **Nota sobre convenções idiomáticas Go.** Field names usam PascalCase simples (`Id`, `IpAddress`, `JsonField`). Na migração real, ajustar para `ID`, `IPAddress`, `JSONField` (ver [Effective Go — MixedCaps](https://go.dev/doc/effective_go#mixed-caps)). Este doc é **referência estrutural**, não codegen final.

Imports sugeridos:

```go
import (
	"encoding/json"
	"time"

	"github.com/shopspring/decimal"
)
```

### `audit_logs` → `type AuditLog struct`

```go
type AuditLog struct {
	Id string `db:"id" json:"id"`
	WorkspaceId *string `db:"workspace_id" json:"workspace_id"`
	ActorUserId *string `db:"actor_user_id" json:"actor_user_id"`
	Action string `db:"action" json:"action"`
	ResourceType string `db:"resource_type" json:"resource_type"`
	ResourceId *string `db:"resource_id" json:"resource_id"`
	IpAddress *string `db:"ip_address" json:"ip_address"`
	UserAgent *string `db:"user_agent" json:"user_agent"`
	Details json.RawMessage `db:"details" json:"details"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `bank_accounts` → `type BankAccount struct`

```go
type BankAccount struct {
	Id string `db:"id" json:"id"`
	MemberId string `db:"member_id" json:"member_id"`
	InstitutionCode string `db:"institution_code" json:"institution_code"`
	AccountType string `db:"account_type" json:"account_type"`
	Agency *string `db:"agency" json:"agency"`
	AccountNumber *string `db:"account_number" json:"account_number"`
	Label *string `db:"label" json:"label"`
}
```

### `categories` → `type Category struct`

```go
type Category struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Code string `db:"code" json:"code"`
	Name string `db:"name" json:"name"`
	CategoryType string `db:"category_type" json:"category_type"`
	MonthlyCap *float64 `db:"monthly_cap" json:"monthly_cap"`
	Order int `db:"order" json:"order"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `category_keywords` → `type CategoryKeyword struct`

```go
type CategoryKeyword struct {
	Id string `db:"id" json:"id"`
	CategoryId string `db:"category_id" json:"category_id"`
	Keyword string `db:"keyword" json:"keyword"`
}
```

### `documents` → `type Document struct`

```go
type Document struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	OriginalName string `db:"original_name" json:"original_name"`
	StoredPath *string `db:"stored_path" json:"stored_path"`
	DocType *string `db:"doc_type" json:"doc_type"`
	BankCode *string `db:"bank_code" json:"bank_code"`
	Period *string `db:"period" json:"period"`
	Status string `db:"status" json:"status"`
	ClassificationMeta json.RawMessage `db:"classification_meta" json:"classification_meta"`
	FileSizeBytes *int `db:"file_size_bytes" json:"file_size_bytes"`
	ContentHash *string `db:"content_hash" json:"content_hash"`
	ContentType *string `db:"content_type" json:"content_type"`
	ErrorMessage *string `db:"error_message" json:"error_message"`
	ClassificationConfidence *float64 `db:"classification_confidence" json:"classification_confidence"`
	NeedsReview bool `db:"needs_review" json:"needs_review"`
	PossibleDuplicateOfId *string `db:"possible_duplicate_of_id" json:"possible_duplicate_of_id"`
	UploadedAt time.Time `db:"uploaded_at" json:"uploaded_at"`
	PipelineLastRunAt *time.Time `db:"pipeline_last_run_at" json:"pipeline_last_run_at"`
	PipelineE2ExtractOk *bool `db:"pipeline_e2_extract_ok" json:"pipeline_e2_extract_ok"`
	PipelineExtractNotes *string `db:"pipeline_extract_notes" json:"pipeline_extract_notes"`
}
```

### `family_members` → `type FamilyMember struct`

```go
type FamilyMember struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Key string `db:"key" json:"key"`
	FullName string `db:"full_name" json:"full_name"`
	ShortName string `db:"short_name" json:"short_name"`
	CpfEncrypted *string `db:"cpf_encrypted" json:"cpf_encrypted"`
	BirthDate *time.Time `db:"birth_date" json:"birth_date"`
	Role string `db:"role" json:"role"`
	Order int `db:"order" json:"order"`
	Extra json.RawMessage `db:"extra" json:"extra"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `feature_flags` → `type FeatureFlag struct`

```go
type FeatureFlag struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	FlagsJson json.RawMessage `db:"flags_json" json:"flags_json"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `goals` → `type Goal struct`

```go
type Goal struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Type string `db:"type" json:"type"`
	ParamsJson json.RawMessage `db:"params_json" json:"params_json"`
	DerivedJson json.RawMessage `db:"derived_json" json:"derived_json"`
	EffectiveFrom time.Time `db:"effective_from" json:"effective_from"`
	EffectiveTo *time.Time `db:"effective_to" json:"effective_to"`
	CreatedBy *string `db:"created_by" json:"created_by"`
	Notes *string `db:"notes" json:"notes"`
	IsTemplate bool `db:"is_template" json:"is_template"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `institution_configs` → `type InstitutionConfig struct`

```go
type InstitutionConfig struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ConfigJson json.RawMessage `db:"config_json" json:"config_json"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `kanban_items` → `type KanbanItem struct`

```go
type KanbanItem struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ReportId string `db:"report_id" json:"report_id"`
	Titulo string `db:"titulo" json:"titulo"`
	Coluna string `db:"coluna" json:"coluna"`
	Prioridade *string `db:"prioridade" json:"prioridade"`
	Prazo *time.Time `db:"prazo" json:"prazo"`
	Categoria *string `db:"categoria" json:"categoria"`
	Essencial *string `db:"essencial" json:"essencial"`
	Ordem int `db:"ordem" json:"ordem"`
	CreatedBy *string `db:"created_by" json:"created_by"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `llm_configs` → `type LLMConfig struct`

```go
type LLMConfig struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Provider string `db:"provider" json:"provider"`
	ApiKeyEncrypted string `db:"api_key_encrypted" json:"api_key_encrypted"`
	ModelName string `db:"model_name" json:"model_name"`
	MaxTokens int `db:"max_tokens" json:"max_tokens"`
	Temperature float64 `db:"temperature" json:"temperature"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `notifications` → `type Notification struct`

```go
type Notification struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Severity string `db:"severity" json:"severity"`
	Title string `db:"title" json:"title"`
	Message string `db:"message" json:"message"`
	Source *string `db:"source" json:"source"`
	IsRead bool `db:"is_read" json:"is_read"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `password_vault` → `type PasswordVault struct`

```go
type PasswordVault struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Label string `db:"label" json:"label"`
	EncryptedPassword string `db:"encrypted_password" json:"encrypted_password"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `pipeline_artifacts` → `type PipelineArtifact struct`

```go
type PipelineArtifact struct {
	Id int `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	PipelineRunId string `db:"pipeline_run_id" json:"pipeline_run_id"`
	Stage string `db:"stage" json:"stage"`
	ArtifactKey string `db:"artifact_key" json:"artifact_key"`
	DocumentId *string `db:"document_id" json:"document_id"`
	ContentJson json.RawMessage `db:"content_json" json:"content_json"`
	SchemaVersion *string `db:"schema_version" json:"schema_version"`
	ByteSize *int `db:"byte_size" json:"byte_size"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `pipeline_configs` → `type PipelineConfig struct`

```go
type PipelineConfig struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ConfigJson json.RawMessage `db:"config_json" json:"config_json"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `pipeline_runs` → `type PipelineRun struct`

```go
type PipelineRun struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Status string `db:"status" json:"status"`
	CurrentStage *string `db:"current_stage" json:"current_stage"`
	FailedAtStage *string `db:"failed_at_stage" json:"failed_at_stage"`
	ConfigSnapshot json.RawMessage `db:"config_snapshot" json:"config_snapshot"`
	TotalDocuments *int `db:"total_documents" json:"total_documents"`
	ReprocessAll bool `db:"reprocess_all" json:"reprocess_all"`
	Incremental bool `db:"incremental" json:"incremental"`
	IncrementalDocIds json.RawMessage `db:"incremental_doc_ids" json:"incremental_doc_ids"`
	StartedAt time.Time `db:"started_at" json:"started_at"`
	CompletedAt *time.Time `db:"completed_at" json:"completed_at"`
	TierAtRun string `db:"tier_at_run" json:"tier_at_run"`
	PausedAtStage *string `db:"paused_at_stage" json:"paused_at_stage"`
	CeleryTaskId *string `db:"celery_task_id" json:"celery_task_id"`
}
```

### `pipeline_stage_logs` → `type PipelineStageLog struct`

```go
type PipelineStageLog struct {
	Id string `db:"id" json:"id"`
	PipelineRunId string `db:"pipeline_run_id" json:"pipeline_run_id"`
	Stage string `db:"stage" json:"stage"`
	Status string `db:"status" json:"status"`
	OutputSummary json.RawMessage `db:"output_summary" json:"output_summary"`
	Errors *string `db:"errors" json:"errors"`
	DurationMs *int `db:"duration_ms" json:"duration_ms"`
	StartedAt time.Time `db:"started_at" json:"started_at"`
	CompletedAt *time.Time `db:"completed_at" json:"completed_at"`
}
```

### `report_layouts` → `type ReportLayout struct`

```go
type ReportLayout struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ConfigJson json.RawMessage `db:"config_json" json:"config_json"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `report_notes` → `type ReportNote struct`

```go
type ReportNote struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ReportId string `db:"report_id" json:"report_id"`
	AuthorUserId *string `db:"author_user_id" json:"author_user_id"`
	Content string `db:"content" json:"content"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `reports` → `type Report struct`

```go
type Report struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	PipelineRunId *string `db:"pipeline_run_id" json:"pipeline_run_id"`
	Title string `db:"title" json:"title"`
	Period *string `db:"period" json:"period"`
	AnalysisArtifactId *int `db:"analysis_artifact_id" json:"analysis_artifact_id"`
	TasksSnapshotJson json.RawMessage `db:"tasks_snapshot_json" json:"tasks_snapshot_json"`
	PremissasSnapshotJson json.RawMessage `db:"premissas_snapshot_json" json:"premissas_snapshot_json"`
	Score *float64 `db:"score" json:"score"`
	PatrimonioLiquido *float64 `db:"patrimonio_liquido" json:"patrimonio_liquido"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `stage_reviews` → `type StageReview struct`

```go
type StageReview struct {
	Id string `db:"id" json:"id"`
	PipelineRunId string `db:"pipeline_run_id" json:"pipeline_run_id"`
	Stage string `db:"stage" json:"stage"`
	Status string `db:"status" json:"status"`
	OriginalOutputJson json.RawMessage `db:"original_output_json" json:"original_output_json"`
	EditedOutputJson json.RawMessage `db:"edited_output_json" json:"edited_output_json"`
	ValidationErrors *string `db:"validation_errors" json:"validation_errors"`
	ReviewerNotes *string `db:"reviewer_notes" json:"reviewer_notes"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	ReviewedAt *time.Time `db:"reviewed_at" json:"reviewed_at"`
}
```

### `task_attachments` → `type TaskAttachment struct`

```go
type TaskAttachment struct {
	Id string `db:"id" json:"id"`
	TaskId string `db:"task_id" json:"task_id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	StoragePath string `db:"storage_path" json:"storage_path"`
	OriginalFilename string `db:"original_filename" json:"original_filename"`
	ContentType *string `db:"content_type" json:"content_type"`
	SizeBytes *int `db:"size_bytes" json:"size_bytes"`
	UploadedBy *string `db:"uploaded_by" json:"uploaded_by"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `task_suggestions` → `type TaskSuggestion struct`

```go
type TaskSuggestion struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ProposedPayload json.RawMessage `db:"proposed_payload" json:"proposed_payload"`
	Source string `db:"source" json:"source"`
	SourceRunId *string `db:"source_run_id" json:"source_run_id"`
	Status string `db:"status" json:"status"`
	RejectionReason *string `db:"rejection_reason" json:"rejection_reason"`
	ApprovedTaskId *string `db:"approved_task_id" json:"approved_task_id"`
	ReviewedBy *string `db:"reviewed_by" json:"reviewed_by"`
	ReviewedAt *time.Time `db:"reviewed_at" json:"reviewed_at"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `tasks` → `type Task struct`

```go
type Task struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Number int `db:"number" json:"number"`
	Title string `db:"title" json:"title"`
	Description *string `db:"description" json:"description"`
	Category string `db:"category" json:"category"`
	Priority string `db:"priority" json:"priority"`
	DeadlineKind string `db:"deadline_kind" json:"deadline_kind"`
	DeadlineDate *time.Time `db:"deadline_date" json:"deadline_date"`
	DeadlineLabel *string `db:"deadline_label" json:"deadline_label"`
	Status string `db:"status" json:"status"`
	StatusReason *string `db:"status_reason" json:"status_reason"`
	Ref *string `db:"ref" json:"ref"`
	ParentTaskId *string `db:"parent_task_id" json:"parent_task_id"`
	RelatedTransactionId *string `db:"related_transaction_id" json:"related_transaction_id"`
	RelatedGoalId *string `db:"related_goal_id" json:"related_goal_id"`
	AssignedTo *string `db:"assigned_to" json:"assigned_to"`
	CreatedFrom string `db:"created_from" json:"created_from"`
	SourceSuggestionId *string `db:"source_suggestion_id" json:"source_suggestion_id"`
	CompletedAt *time.Time `db:"completed_at" json:"completed_at"`
	CancelledAt *time.Time `db:"cancelled_at" json:"cancelled_at"`
	CreatedBy *string `db:"created_by" json:"created_by"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `transaction_overrides` → `type TransactionOverride struct`

```go
type TransactionOverride struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	TransactionHash string `db:"transaction_hash" json:"transaction_hash"`
	OriginalCategory string `db:"original_category" json:"original_category"`
	NewCategory string `db:"new_category" json:"new_category"`
	Notes *string `db:"notes" json:"notes"`
	Reviewed bool `db:"reviewed" json:"reviewed"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `transfer_configs` → `type TransferConfig struct`

```go
type TransferConfig struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ConfigJson json.RawMessage `db:"config_json" json:"config_json"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `users` → `type User struct`

```go
type User struct {
	Id string `db:"id" json:"id"`
	Email string `db:"email" json:"email"`
	HashedPassword string `db:"hashed_password" json:"hashed_password"`
	FullName string `db:"full_name" json:"full_name"`
	IsActive bool `db:"is_active" json:"is_active"`
	IsDeveloper bool `db:"is_developer" json:"is_developer"`
	TokenVersion int `db:"token_version" json:"token_version"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `workspace_invitations` → `type WorkspaceInvitation struct`

```go
type WorkspaceInvitation struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Email string `db:"email" json:"email"`
	Role string `db:"role" json:"role"`
	TokenHash string `db:"token_hash" json:"token_hash"`
	InvitedBy *string `db:"invited_by" json:"invited_by"`
	ExpiresAt time.Time `db:"expires_at" json:"expires_at"`
	AcceptedAt *time.Time `db:"accepted_at" json:"accepted_at"`
	AcceptedByUserId *string `db:"accepted_by_user_id" json:"accepted_by_user_id"`
	RevokedAt *time.Time `db:"revoked_at" json:"revoked_at"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `workspace_members` → `type WorkspaceMember struct`

```go
type WorkspaceMember struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	UserId string `db:"user_id" json:"user_id"`
	Role string `db:"role" json:"role"`
	InvitedBy *string `db:"invited_by" json:"invited_by"`
	JoinedAt time.Time `db:"joined_at" json:"joined_at"`
}
```

### `workspaces` → `type Workspace struct`

```go
type Workspace struct {
	Id string `db:"id" json:"id"`
	Name string `db:"name" json:"name"`
	FamilySurname *string `db:"family_surname" json:"family_surname"`
	OwnerId string `db:"owner_id" json:"owner_id"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UseDbArtifactsOverride *bool `db:"use_db_artifacts_override" json:"use_db_artifacts_override"`
	DeletedAt *time.Time `db:"deleted_at" json:"deleted_at"`
}
```
