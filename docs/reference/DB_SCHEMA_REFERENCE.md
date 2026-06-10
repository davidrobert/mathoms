# DB Schema Reference — Mathoms AI

> **Auto-gerado** por `dev/generate_db_schema_reference.py`. Não edite manualmente — rode `make update-db-schema-reference` e comite o diff.
>
> **Última regeneração:** consulte `git log -1 --format=%cs -- docs/reference/DB_SCHEMA_REFERENCE.md`. O conteúdo é determinístico (mesmo `Base.metadata` ⇒ mesmos bytes — verificado por `backend/tests/test_db_schema_reference_snapshot.py`), por isso não embutimos `datetime.now()` no header.

Referência canônica de schema do banco. Cobre todos os models registrados em `backend/app/models/` via `Base.metadata`.

**Total de tabelas:** 60

---

## Índice

- [`asset_catalog`](#assetcatalog)
- [`audit_logs`](#auditlogs)
- [`bank_accounts`](#bankaccounts)
- [`categories`](#categories)
- [`categorization_rules`](#categorizationrules)
- [`category_keywords`](#categorykeywords)
- [`category_templates`](#categorytemplates)
- [`data_export_requests`](#dataexportrequests)
- [`data_source`](#datasource)
- [`debt`](#debt)
- [`decision_events`](#decisionevents)
- [`decisions`](#decisions)
- [`documents`](#documents)
- [`economic_asset_class`](#economicassetclass)
- [`economic_assumptions`](#economicassumptions)
- [`family_members`](#familymembers)
- [`feature_flags`](#featureflags)
- [`fiscal_parameters`](#fiscalparameters)
- [`goals`](#goals)
- [`institution_catalog`](#institutioncatalog)
- [`institution_configs`](#institutionconfigs)
- [`llm_call_log`](#llmcalllog)
- [`llm_configs`](#llmconfigs)
- [`market_rates`](#marketrates)
- [`notifications`](#notifications)
- [`password_vault`](#passwordvault)
- [`pipeline_artifacts`](#pipelineartifacts)
- [`pipeline_configs`](#pipelineconfigs)
- [`pipeline_run_costs`](#pipelineruncosts)
- [`pipeline_runs`](#pipelineruns)
- [`pipeline_stage_logs`](#pipelinestagelogs)
- [`planner_field_requests`](#plannerfieldrequests)
- [`planner_review_metadata`](#plannerreviewmetadata)
- [`property_identity`](#propertyidentity)
- [`property_market_value`](#propertymarketvalue)
- [`protections`](#protections)
- [`report_layouts`](#reportlayouts)
- [`report_publications`](#reportpublications)
- [`reports`](#reports)
- [`review_reasons`](#reviewreasons)
- [`risks`](#risks)
- [`stage_reviews`](#stagereviews)
- [`suggestions`](#suggestions)
- [`task_attachments`](#taskattachments)
- [`task_suggestions`](#tasksuggestions)
- [`tasks`](#tasks)
- [`transaction_overrides`](#transactionoverrides)
- [`transfer_configs`](#transferconfigs)
- [`users`](#users)
- [`vehicles`](#vehicles)
- [`workspace_asset_overrides`](#workspaceassetoverrides)
- [`workspace_category_overrides`](#workspacecategoryoverrides)
- [`workspace_economic_assumptions_override`](#workspaceeconomicassumptionsoverride)
- [`workspace_invitations`](#workspaceinvitations)
- [`workspace_irpf_suggestion_dismissals`](#workspaceirpfsuggestiondismissals)
- [`workspace_members`](#workspacemembers)
- [`workspace_memory_confirmations`](#workspacememoryconfirmations)
- [`workspace_notes`](#workspacenotes)
- [`workspace_property_overrides`](#workspacepropertyoverrides)
- [`workspaces`](#workspaces)

---

## Tabelas

### `asset_catalog`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `catalog_version` | `INTEGER` | no | `1` | INDEX |
| `ticker` | `VARCHAR(12)` | yes | — | INDEX |
| `cnpj` | `VARCHAR(20)` | yes | — | INDEX |
| `match_keyword` | `VARCHAR(200)` | yes | — | — |
| `asset_class` | `VARCHAR(40)` | no | — | — |
| `lastro_moeda` | `VARCHAR(8)` | no | — | — |
| `lastro_source` | `VARCHAR(20)` | no | `'catalog'` | — |
| `notes` | `VARCHAR` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Indexes:**

- `ix_asset_catalog_catalog_version` (catalog_version)
- `ix_asset_catalog_cnpj` (cnpj)
- `ix_asset_catalog_ticker` (ticker)

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
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (actor_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_audit_logs_action` (action)
- `ix_audit_logs_actor_created` (actor_user_id, created_at)
- `ix_audit_logs_actor_user_id` (actor_user_id)
- `ix_audit_logs_resource_id` (resource_id)
- `ix_audit_logs_workspace_created` (workspace_id, created_at)
- `ix_audit_logs_workspace_id` (workspace_id)

### `bank_accounts`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `member_id` | `VARCHAR(36)` | no | — | FK→family_members.id, INDEX |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `institution_code` | `VARCHAR(50)` | no | — | — |
| `account_type` | `VARCHAR(100)` | no | — | — |
| `agency` | `VARCHAR(20)` | yes | — | — |
| `account_number` | `VARCHAR(30)` | yes | — | — |
| `label` | `VARCHAR(255)` | yes | — | — |
| `source_tier` | `SMALLINT` | yes | — | — |
| `is_joint` | `BOOLEAN` | no | `False` | — |
| `co_titulares` | `JSON` | yes | — | — |
| `irpf_snapshots` | `JSON` | yes | — | — |

**Constraints:**

- FOREIGN KEY (member_id) REFERENCES family_members.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_bank_accounts_member_id` (member_id)
- `ix_bank_accounts_workspace_id` (workspace_id)

### `categories`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `code` | `VARCHAR(50)` | no | — | — |
| `name` | `VARCHAR(100)` | no | — | — |
| `category_type` | `VARCHAR(10)` | no | — | — |
| `order` | `INTEGER` | no | `0` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_categories_workspace_id` (workspace_id)

### `categorization_rules`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `keyword` | `VARCHAR(255)` | no | — | — |
| `target_category` | `VARCHAR(255)` | no | — | — |
| `priority` | `INTEGER` | no | server: `100` | — |
| `enabled` | `BOOLEAN` | no | server: `1` | — |
| `origin_override_id` | `VARCHAR(36)` | yes | — | — |
| `created_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |
| `applied_count` | `INTEGER` | no | server: `0` | — |
| `revert_count_manual_edit` | `INTEGER` | no | server: `0` | — |
| `revert_count_rule_disabled` | `INTEGER` | no | server: `0` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `deleted_at` | `DATETIME` | yes | — | — |

**Constraints:**

- FOREIGN KEY (created_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, keyword, target_category) — `uq_cat_rules_ws_keyword_target`

**Indexes:**

- `ix_categorization_rules_workspace_id` (workspace_id)

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

### `category_templates`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `template_version` | `INTEGER` | no | `1` | INDEX |
| `key` | `VARCHAR(100)` | no | — | INDEX |
| `parent_key` | `VARCHAR(100)` | yes | — | — |
| `label` | `VARCHAR(120)` | no | — | — |
| `category_type` | `VARCHAR(10)` | no | — | — |
| `default_keywords` | `JSON` | no | callable: `list` | — |
| `default_monthly_cap_brl_cents` | `BIGINT` | yes | — | — |
| `sort_order` | `INTEGER` | no | `0` | — |
| `metadata_json` | `JSON` | no | callable: `dict` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- UNIQUE (template_version, key) — `uq_category_templates_version_key`

**Indexes:**

- `ix_category_templates_key` (key)
- `ix_category_templates_template_version` (template_version)

### `data_export_requests`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `user_id` | `VARCHAR(36)` | no | — | FK→users.id, INDEX |
| `status` | `VARCHAR(16)` | no | server: `pending` | INDEX |
| `download_token` | `VARCHAR(96)` | yes | — | UNIQUE |
| `expires_at` | `DATETIME` | yes | — | INDEX |
| `file_path` | `VARCHAR(512)` | yes | — | — |
| `file_size_bytes` | `BIGINT` | yes | — | — |
| `error_message` | `TEXT` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | INDEX |
| `completed_at` | `DATETIME` | yes | — | — |

**Constraints:**

- FOREIGN KEY (user_id) REFERENCES users.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (download_token) — `(unnamed)`

**Indexes:**

- `ix_data_export_requests_created_at` (created_at)
- `ix_data_export_requests_expires_at` (expires_at)
- `ix_data_export_requests_status` (status)
- `ix_data_export_requests_user_id` (user_id)

### `data_source`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `kind` | `VARCHAR(20)` | no | — | — |
| `institution_code` | `VARCHAR(64)` | no | server: `` | — |
| `external_account_ref` | `VARCHAR(128)` | no | server: `` | — |
| `display_name` | `VARCHAR(255)` | no | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, kind, institution_code, external_account_ref) — `uq_data_source_natural_key`

**Indexes:**

- `ix_data_source_workspace_id` (workspace_id)

### `debt`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id |
| `family_member_id` | `VARCHAR(36)` | yes | — | FK→family_members.id |
| `property_id` | `VARCHAR(36)` | yes | — | FK→property_identity.id |
| `tipo` | `VARCHAR(30)` | no | — | — |
| `descricao` | `TEXT` | yes | — | — |
| `saldo_devedor_cents` | `BIGINT` | no | — | — |
| `parcela_mensal_cents` | `BIGINT` | yes | — | — |
| `taxa_juros_aa` | `NUMERIC(5, 2)` | yes | — | — |
| `prazo_meses_restantes` | `INTEGER` | yes | — | — |
| `data_contratacao` | `DATE` | yes | — | — |
| `source` | `VARCHAR(30)` | no | — | — |
| `migration_source_key` | `VARCHAR(64)` | yes | — | — |
| `needs_review` | `BOOLEAN` | no | server: `0` | — |
| `percentual_atribuicao_imovel` | `NUMERIC(5, 2)` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- CHECK (`family_member_id IS NOT NULL OR property_id IS NOT NULL OR descricao IS NOT NULL`) — `chk_debt_identity`
- CHECK (`percentual_atribuicao_imovel IS NULL OR (percentual_atribuicao_imovel > 0 AND percentual_atribuicao_imovel <= 100)`) — `chk_debt_pct_atribuicao`
- CHECK (`source IN ('baseline_irpf_migration','user_declared','open_banking_futuro')`) — `chk_debt_source`
- CHECK (`tipo IN ('financiamento_imobiliario','consignado','cdc','cartao_rotativo','rotativo','outro')`) — `chk_debt_tipo`
- FOREIGN KEY (family_member_id) REFERENCES family_members.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (property_id) REFERENCES property_identity.id ON DELETE RESTRICT — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_debt_property` (property_id)
- `ix_debt_workspace` (workspace_id)
- UNIQUE `uq_debt_migration_source` (workspace_id, migration_source_key)

### `decision_events`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `decision_id` | `VARCHAR(36)` | no | — | FK→decisions.id, INDEX |
| `event_type` | `VARCHAR(32)` | no | — | — |
| `occurred_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `actor` | `VARCHAR(128)` | no | — | — |
| `payload` | `JSON` | no | callable: `dict` | — |

**Constraints:**

- FOREIGN KEY (decision_id) REFERENCES decisions.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_decision_events_decision_id` (decision_id)
- `ix_decision_events_decision_occurred` (decision_id, occurred_at)

### `decisions`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `code` | `VARCHAR(16)` | no | — | — |
| `title` | `VARCHAR(500)` | no | — | — |
| `rationale` | `TEXT` | yes | — | — |
| `amount_brl_cents` | `BIGINT` | yes | — | — |
| `status` | `VARCHAR(32)` | no | — | — |
| `supersedes_id` | `VARCHAR(36)` | yes | — | FK→decisions.id |
| `decided_at` | `DATE` | yes | — | — |
| `executed_at` | `DATE` | yes | — | — |
| `target_field` | `VARCHAR(64)` | yes | — | — |
| `target_value` | `VARCHAR(128)` | yes | — | — |
| `target_value_type` | `VARCHAR(8)` | yes | — | — |
| `context_snapshot` | `JSON` | yes | — | — |
| `impact_1y_brl_cents` | `BIGINT` | yes | — | — |
| `impact_10y_brl_cents` | `BIGINT` | yes | — | — |
| `horizon` | `VARCHAR(16)` | no | server: `short_6_12m` | — |
| `priority` | `SMALLINT` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (supersedes_id) REFERENCES decisions.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, code) — `uq_decisions_workspace_code`

**Indexes:**

- `ix_decisions_workspace_id` (workspace_id)
- `ix_decisions_ws_horizon` (workspace_id, horizon)
- `ix_decisions_ws_status` (workspace_id, status)

### `documents`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `original_name` | `VARCHAR(500)` | no | — | — |
| `stored_path` | `TEXT` | yes | — | — |
| `doc_type` | `VARCHAR(26)` | yes | `<DocumentType.other: 'other'>` | — |
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
- UNIQUE `ux_documents_workspace_content_hash` (workspace_id, content_hash)

### `economic_asset_class`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `code` | `VARCHAR(40)` | no | — | PK |
| `label` | `VARCHAR(120)` | no | — | — |
| `sort_order` | `INTEGER` | no | — | INDEX |
| `active` | `BOOLEAN` | no | `True` | INDEX |
| `deprecated_at` | `DATETIME` | yes | — | — |
| `description` | `TEXT` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Indexes:**

- `ix_economic_asset_class_active` (active)
- `ix_economic_asset_class_sort_order` (sort_order)

### `economic_assumptions`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `classe_auvp` | `VARCHAR(40)` | no | — | FK→economic_asset_class.code, INDEX |
| `retorno_real_esperado_pct_anual` | `NUMERIC(6, 3)` | no | — | — |
| `sigma_anual_pct` | `NUMERIC(6, 3)` | no | — | — |
| `fonte` | `TEXT` | no | — | — |
| `effective_from` | `DATE` | no | — | INDEX |
| `effective_to` | `DATE` | yes | — | INDEX |
| `created_by` | `VARCHAR(255)` | no | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (classe_auvp) REFERENCES economic_asset_class.code ON DELETE RESTRICT — `(unnamed)`
- UNIQUE (classe_auvp, effective_from) — `uq_economic_assumptions_classe_from`

**Indexes:**

- `ix_economic_assumptions_classe_auvp` (classe_auvp)
- `ix_economic_assumptions_effective_from` (effective_from)
- `ix_economic_assumptions_effective_to` (effective_to)

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
| `us_tax_status` | `VARCHAR(32)` | yes | — | — |
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

### `fiscal_parameters`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `year` | `INTEGER` | no | — | INDEX |
| `ir_brackets` | `JSON` | no | — | — |
| `pgbl_limit_brl_cents` | `BIGINT` | no | — | — |
| `inss_ceiling_brl_cents` | `BIGINT` | no | — | — |
| `lucro_presumido_aliquota` | `NUMERIC(5, 4)` | no | — | — |
| `effective_from` | `DATE` | no | — | INDEX |
| `effective_to` | `DATE` | yes | — | INDEX |
| `source` | `TEXT` | no | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Indexes:**

- `ix_fiscal_parameters_effective_from` (effective_from)
- `ix_fiscal_parameters_effective_to` (effective_to)
- `ix_fiscal_parameters_year` (year)

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

### `institution_catalog`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `code` | `VARCHAR(50)` | no | — | UNIQUE, INDEX |
| `name` | `VARCHAR(120)` | no | — | — |
| `default_parser` | `VARCHAR(80)` | yes | — | — |
| `category` | `VARCHAR(20)` | no | `'bank'` | — |
| `tax_regime` | `VARCHAR(8)` | no | server: `both` | — |
| `metadata_json` | `JSON` | no | callable: `dict` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Indexes:**

- UNIQUE `ix_institution_catalog_code` (code)

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

### `llm_call_log`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `stage` | `VARCHAR(64)` | no | — | — |
| `model_name` | `VARCHAR(120)` | no | — | — |
| `prompt_version` | `VARCHAR(40)` | yes | — | — |
| `tokens_in` | `INTEGER` | no | `0` | — |
| `tokens_out` | `INTEGER` | no | `0` | — |
| `cost_usd` | `NUMERIC(12, 6)` | no | `Decimal('0.000000')` | — |
| `cost_known` | `BOOLEAN` | no | `True` | — |
| `duration_ms` | `INTEGER` | no | `0` | — |
| `pipeline_run_id` | `VARCHAR(36)` | yes | — | INDEX |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | INDEX |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_llm_call_log_created_at` (created_at)
- `ix_llm_call_log_pipeline_run_id` (pipeline_run_id)
- `ix_llm_call_log_workspace_id` (workspace_id)
- `ix_llm_call_log_ws_created` (workspace_id, created_at)
- `ix_llm_call_log_ws_model_created` (workspace_id, model_name, created_at)

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

### `market_rates`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `pair` | `VARCHAR(16)` | no | — | INDEX |
| `rate` | `NUMERIC(20, 10)` | no | — | — |
| `observed_at` | `DATE` | no | — | INDEX |
| `reference_month` | `VARCHAR(7)` | yes | — | — |
| `source` | `TEXT` | no | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- UNIQUE (pair, observed_at) — `uq_market_rates_pair_observed_at`

**Indexes:**

- `ix_market_rates_observed_at` (observed_at)
- `ix_market_rates_pair` (pair)

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
| `data_source_id` | `VARCHAR(36)` | yes | — | — |
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

- `ix_pipeline_artifacts_data_source_id` (data_source_id)
- `ix_pipeline_artifacts_document_id` (document_id)
- `ix_pipeline_artifacts_pipeline_run_id` (pipeline_run_id)
- `ix_pipeline_artifacts_workspace_id` (workspace_id)
- `ix_pipeline_artifacts_workspace_stage_key` (workspace_id, stage, artifact_key)
- `ix_pipeline_artifacts_ws_stage_key_created` (workspace_id, stage, artifact_key, created_at)

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

### `pipeline_run_costs`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `INTEGER` | no | — | PK |
| `pipeline_run_id` | `VARCHAR(36)` | no | — | FK→pipeline_runs.id, INDEX |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `stage` | `VARCHAR(50)` | no | — | — |
| `model_id` | `VARCHAR(100)` | no | — | — |
| `tokens_in` | `INTEGER` | no | `0` | — |
| `tokens_out` | `INTEGER` | no | `0` | — |
| `cost_usd_cents` | `BIGINT` | no | `0` | — |
| `latency_ms` | `INTEGER` | no | `0` | — |
| `tool_iterations` | `INTEGER` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_pipeline_run_costs_pipeline_run_id` (pipeline_run_id)
- `ix_pipeline_run_costs_stage` (stage, created_at)
- `ix_pipeline_run_costs_workspace_date` (workspace_id, created_at)
- `ix_pipeline_run_costs_workspace_id` (workspace_id)

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
| `last_heartbeat_at` | `DATETIME` | yes | — | — |
| `failure_reason` | `VARCHAR(50)` | yes | — | — |

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

### `planner_field_requests`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `planner_review_id` | `VARCHAR(36)` | no | — | FK→planner_review_metadata.id, INDEX |
| `field_path` | `VARCHAR(255)` | no | — | INDEX |
| `motivo` | `TEXT` | no | — | — |
| `reason` | `VARCHAR(64)` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | INDEX |

**Constraints:**

- FOREIGN KEY (planner_review_id) REFERENCES planner_review_metadata.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (planner_review_id, field_path) — `uq_planner_field_request_review_path`

**Indexes:**

- `ix_planner_field_requests_created_at` (created_at)
- `ix_planner_field_requests_date_path` (created_at, field_path)
- `ix_planner_field_requests_field_path` (field_path)
- `ix_planner_field_requests_planner_review_id` (planner_review_id)
- `ix_planner_field_requests_workspace_id` (workspace_id)

### `planner_review_metadata`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `pipeline_run_id` | `VARCHAR(36)` | no | — | FK→pipeline_runs.id, INDEX |
| `pipeline_artifact_id` | `INTEGER` | no | — | FK→pipeline_artifacts.id, UNIQUE, INDEX |
| `e5_artifact_id` | `INTEGER` | no | — | FK→pipeline_artifacts.id, INDEX |
| `status` | `VARCHAR(20)` | no | `'Pendente'` | INDEX |
| `supersedes_id` | `VARCHAR(36)` | yes | — | FK→planner_review_metadata.id, INDEX |
| `superseded_by_id` | `VARCHAR(36)` | yes | — | INDEX |
| `persona_hash` | `VARCHAR(64)` | no | — | — |
| `manifest_version` | `VARCHAR(20)` | no | — | — |
| `schema_version` | `VARCHAR(20)` | no | — | — |
| `model_id` | `VARCHAR(100)` | no | — | — |
| `immutable_hash` | `VARCHAR(64)` | yes | — | — |
| `tier_at_generation` | `VARCHAR(20)` | no | — | — |
| `items_shown_count` | `INTEGER` | no | `0` | — |
| `items_gated_count` | `INTEGER` | no | `0` | — |
| `cost_usd_cents` | `BIGINT` | no | `0` | — |
| `tokens_in` | `INTEGER` | no | `0` | — |
| `tokens_out` | `INTEGER` | no | `0` | — |
| `tool_iterations` | `INTEGER` | no | `0` | — |
| `latency_ms` | `INTEGER` | no | `0` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | INDEX |
| `published_at` | `DATETIME` | yes | — | — |
| `superseded_at` | `DATETIME` | yes | — | — |

**Constraints:**

- FOREIGN KEY (e5_artifact_id) REFERENCES pipeline_artifacts.id ON DELETE RESTRICT — `(unnamed)`
- FOREIGN KEY (pipeline_artifact_id) REFERENCES pipeline_artifacts.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (supersedes_id) REFERENCES planner_review_metadata.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, pipeline_run_id) — `uq_planner_review_workspace_run`

**Indexes:**

- `ix_planner_review_metadata_created_at` (created_at)
- `ix_planner_review_metadata_e5_artifact_id` (e5_artifact_id)
- UNIQUE `ix_planner_review_metadata_pipeline_artifact_id` (pipeline_artifact_id)
- `ix_planner_review_metadata_pipeline_run_id` (pipeline_run_id)
- `ix_planner_review_metadata_status` (status)
- `ix_planner_review_metadata_superseded_by_id` (superseded_by_id)
- `ix_planner_review_metadata_supersedes_id` (supersedes_id)
- `ix_planner_review_metadata_workspace_id` (workspace_id)
- `ix_planner_review_workspace_status` (workspace_id, status)

### `property_identity`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `titular_key` | `VARCHAR(64)` | no | — | — |
| `codigo_rfb` | `VARCHAR(4)` | no | — | — |
| `endereco_canonical` | `VARCHAR(255)` | yes | — | — |
| `first_seen_year` | `INTEGER` | no | — | — |
| `descricao_sample` | `TEXT` | yes | — | — |
| `low_confidence` | `BOOLEAN` | no | server: `0` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_property_identity_workspace_id` (workspace_id)

### `property_market_value`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `property_id` | `VARCHAR(36)` | no | — | FK→property_identity.id |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id |
| `valor_brl_cents` | `BIGINT` | no | — | — |
| `valuation_date` | `DATE` | no | — | — |
| `source` | `VARCHAR(30)` | no | — | — |
| `confidence` | `NUMERIC(3, 2)` | yes | — | — |
| `notes` | `TEXT` | yes | — | — |
| `superseded_by_id` | `VARCHAR(36)` | yes | — | FK→property_market_value.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `created_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |

**Constraints:**

- CHECK (`confidence IS NULL OR (confidence >= 0 AND confidence <= 1)`) — `chk_pmv_confidence`
- CHECK (`source IN ('user_declared','avaliacao_terceiros','cep_proxy_futuro')`) — `chk_pmv_source`
- FOREIGN KEY (created_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (property_id) REFERENCES property_identity.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (superseded_by_id) REFERENCES property_market_value.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (property_id, valuation_date) — `uq_property_valuation_date`

**Indexes:**

- `idx_pmv_lookup` (workspace_id, property_id)

### `protections`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `category` | `VARCHAR(32)` | no | — | — |
| `holder_family_member_id` | `VARCHAR(36)` | yes | — | FK→family_members.id |
| `insurer` | `VARCHAR(120)` | yes | — | — |
| `policy_ref` | `TEXT` | yes | — | — |
| `coverage_brl_cents` | `BIGINT` | no | — | — |
| `premium_monthly_brl_cents` | `BIGINT` | yes | — | — |
| `coverage_type` | `VARCHAR(16)` | yes | — | — |
| `starts_at` | `DATE` | no | — | — |
| `ends_at` | `DATE` | yes | — | — |
| `status` | `VARCHAR(16)` | no | `'Ativa'` | — |
| `notes` | `TEXT` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (holder_family_member_id) REFERENCES family_members.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_protections_workspace_id` (workspace_id)
- `ix_protections_ws_category` (workspace_id, category)
- `ix_protections_ws_ends_at` (workspace_id, ends_at)
- `ix_protections_ws_status` (workspace_id, status)

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

### `report_publications`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id |
| `period_yyyymm` | `VARCHAR(6)` | no | — | — |
| `artifact_id` | `INTEGER` | no | — | FK→pipeline_artifacts.id |
| `published_at` | `DATETIME` | no | — | — |
| `published_by` | `VARCHAR(64)` | no | — | — |
| `immutable_hash` | `VARCHAR(64)` | no | — | — |
| `unpublished_at` | `DATETIME` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- CHECK (`length(period_yyyymm) = 6`) — `ck_report_publications_period_len`
- FOREIGN KEY (artifact_id) REFERENCES pipeline_artifacts.id ON DELETE RESTRICT — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_report_publications_workspace_id` (workspace_id)
- `ix_report_publications_workspace_period` (workspace_id, period_yyyymm)
- UNIQUE `uq_report_publications_active` (workspace_id, period_yyyymm)

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
| `patrimonio_liquido` | `NUMERIC(18, 2)` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (analysis_artifact_id) REFERENCES pipeline_artifacts.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

### `review_reasons`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `pipeline_run_id` | `VARCHAR(36)` | no | — | FK→pipeline_runs.id, INDEX |
| `stage` | `VARCHAR(50)` | no | — | — |
| `code` | `VARCHAR(64)` | no | — | — |
| `artifact_key` | `VARCHAR(255)` | no | `''` | — |
| `document_id` | `VARCHAR(36)` | yes | — | FK→documents.id |
| `offending_value` | `TEXT` | no | `''` | — |
| `expected` | `TEXT` | no | `''` | — |
| `message` | `TEXT` | no | `''` | — |
| `occurrence_count` | `INTEGER` | no | `1` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (document_id) REFERENCES documents.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_review_reasons_pipeline_run_id` (pipeline_run_id)
- `ix_review_reasons_workspace_id` (workspace_id)
- `ix_review_reasons_ws_run_code` (workspace_id, pipeline_run_id, code)

### `risks`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `code` | `VARCHAR(64)` | no | — | — |
| `name` | `VARCHAR(200)` | no | — | — |
| `rationale` | `TEXT` | no | — | — |
| `probability` | `VARCHAR(16)` | yes | — | — |
| `impact_level` | `VARCHAR(16)` | no | — | — |
| `impact_brl_cents` | `BIGINT` | yes | — | — |
| `status` | `VARCHAR(32)` | no | `'Ativo'` | — |
| `mitigations_decision_ids` | `JSON` | no | callable: `list` | — |
| `mitigation_protection_ids` | `JSON` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, code) — `uq_risks_workspace_code`

**Indexes:**

- `ix_risks_workspace_id` (workspace_id)
- `ix_risks_ws_impact` (workspace_id, impact_level)
- `ix_risks_ws_status` (workspace_id, status)

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
| `validation_issues` | `JSON` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `reviewed_at` | `DATETIME` | yes | — | — |

**Constraints:**

- FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_stage_reviews_pipeline_run_id` (pipeline_run_id)

### `suggestions`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id |
| `report_id` | `VARCHAR(36)` | yes | — | FK→reports.id |
| `section_id` | `VARCHAR(32)` | no | — | — |
| `kind` | `VARCHAR(64)` | no | — | — |
| `category` | `VARCHAR(32)` | yes | — | — |
| `origin` | `VARCHAR(32)` | no | `'deterministic'` | — |
| `severity` | `VARCHAR(16)` | no | — | — |
| `title` | `VARCHAR(500)` | no | — | — |
| `rationale` | `TEXT` | no | — | — |
| `amount_brl_cents` | `BIGINT` | yes | — | — |
| `dedup_key` | `VARCHAR(64)` | no | — | — |
| `status` | `VARCHAR(32)` | no | `'Pendente'` | — |
| `accepted_decision_id` | `VARCHAR(36)` | yes | — | FK→decisions.id |
| `dismissed_reason` | `VARCHAR(32)` | yes | — | — |
| `accepted_at` | `DATETIME` | yes | — | — |
| `dismissed_at` | `DATETIME` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (accepted_decision_id) REFERENCES decisions.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (report_id) REFERENCES reports.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, dedup_key, status) — `uq_sugagg_ws_dedup_status`

**Indexes:**

- `ix_sugagg_workspace_id` (workspace_id)
- `ix_sugagg_ws_dedup` (workspace_id, dedup_key)
- `ix_sugagg_ws_section` (workspace_id, section_id)
- `ix_sugagg_ws_status` (workspace_id, status)

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
| `dedup_key` | `VARCHAR(64)` | yes | — | — |
| `status` | `VARCHAR(32)` | no | `'pending'` | INDEX |
| `rejection_reason` | `TEXT` | yes | — | — |
| `superseded_at` | `DATETIME` | yes | — | — |
| `superseded_by_run_id` | `VARCHAR(36)` | yes | — | — |
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
| `derived_from_decision_id` | `VARCHAR(36)` | yes | — | FK→decisions.id, INDEX |
| `board_column` | `VARCHAR(32)` | yes | — | — |
| `board_order` | `INTEGER` | yes | — | — |
| `urgency` | `VARCHAR(8)` | yes | — | — |
| `origin_report_id` | `VARCHAR(36)` | yes | — | FK→reports.id |
| `is_board_only` | `BOOLEAN` | no | server: `0` | — |
| `completed_at` | `DATETIME` | yes | — | — |
| `cancelled_at` | `DATETIME` | yes | — | — |
| `created_by` | `VARCHAR(36)` | yes | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (assigned_to) REFERENCES family_members.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (created_by) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (derived_from_decision_id) REFERENCES decisions.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (origin_report_id) REFERENCES reports.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (parent_task_id) REFERENCES tasks.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (related_goal_id) REFERENCES goals.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, number) — `uq_task_ws_number`

**Indexes:**

- `ix_tasks_category` (category)
- `ix_tasks_deadline_date` (deadline_date)
- `ix_tasks_derived_from_decision_id` (derived_from_decision_id)
- `ix_tasks_parent_task_id` (parent_task_id)
- `ix_tasks_priority` (priority)
- `ix_tasks_status` (status)
- `ix_tasks_workspace_id` (workspace_id)
- `ix_tasks_ws_board_column` (workspace_id, board_column)
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
| `source` | `VARCHAR(20)` | no | server: `manual` | — |
| `rule_id` | `VARCHAR(36)` | yes | — | FK→categorization_rules.id, INDEX |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `deleted_at` | `DATETIME` | yes | — | — |
| `natural_key_hash` | `VARCHAR(16)` | yes | — | — |
| `hash_version` | `SMALLINT` | yes | — | — |
| `tx_data` | `VARCHAR(10)` | yes | — | — |
| `tx_banco` | `VARCHAR(255)` | yes | — | — |
| `tx_titular` | `VARCHAR(255)` | yes | — | — |
| `tx_tipo_conta` | `VARCHAR(255)` | yes | — | — |
| `tx_valor_cents` | `INTEGER` | yes | — | — |
| `tx_moeda` | `VARCHAR(3)` | yes | — | — |
| `tx_direction` | `VARCHAR(6)` | yes | — | — |
| `tx_descricao` | `TEXT` | yes | — | — |
| `orphaned_at` | `DATETIME` | yes | — | — |

**Constraints:**

- FOREIGN KEY (rule_id) REFERENCES categorization_rules.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, transaction_hash) — `uq_override_ws_hash`

**Indexes:**

- `ix_transaction_overrides_rule_id` (rule_id)
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
| `deletion_requested_at` | `DATETIME` | yes | — | INDEX |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Indexes:**

- `ix_users_deletion_requested_at` (deletion_requested_at)
- UNIQUE `ix_users_email` (email)

### `vehicles`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `placa` | `VARCHAR(10)` | no | — | — |
| `renavam` | `VARCHAR(11)` | no | — | — |
| `marca` | `VARCHAR(60)` | no | — | — |
| `modelo` | `VARCHAR(120)` | no | — | — |
| `ano_modelo` | `INTEGER` | no | — | — |
| `ano_fabricacao` | `INTEGER` | no | — | — |
| `fipe_code` | `VARCHAR(20)` | yes | — | — |
| `cor` | `VARCHAR(30)` | yes | — | — |
| `combustivel` | `VARCHAR(20)` | yes | — | — |
| `codigo_rfb` | `VARCHAR(4)` | no | server: `21` | — |
| `archived_at` | `DATETIME` | yes | — | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- CHECK (`codigo_rfb IN ('21', '22', '23')`) — `chk_vehicles_codigo_rfb`
- CHECK (`length(renavam) BETWEEN 9 AND 11`) — `chk_vehicles_renavam_length`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, placa) — `uq_workspace_placa`

**Indexes:**

- `ix_vehicles_workspace_id` (workspace_id)

### `workspace_asset_overrides`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `asset_match_key` | `VARCHAR(200)` | no | — | — |
| `match_kind` | `VARCHAR(20)` | no | — | — |
| `lastro_moeda` | `VARCHAR(8)` | no | — | — |
| `override_source` | `VARCHAR(20)` | no | `'user_manual'` | — |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `created_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |

**Constraints:**

- FOREIGN KEY (created_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_workspace_asset_overrides_workspace_id` (workspace_id)

### `workspace_category_overrides`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `template_key` | `VARCHAR(100)` | no | — | INDEX |
| `label_override` | `VARCHAR(120)` | yes | — | — |
| `keywords_override` | `JSON` | yes | — | — |
| `monthly_cap_brl_cents_override` | `BIGINT` | yes | — | — |
| `disabled` | `BOOLEAN` | no | `False` | — |
| `updated_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (updated_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, template_key) — `uq_ws_cat_override_ws_key`

**Indexes:**

- `ix_workspace_category_overrides_template_key` (template_key)
- `ix_workspace_category_overrides_workspace_id` (workspace_id)

### `workspace_economic_assumptions_override`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `classe_auvp` | `VARCHAR(40)` | no | — | FK→economic_asset_class.code, INDEX |
| `retorno_real_esperado_pct_anual` | `NUMERIC(6, 3)` | no | — | — |
| `sigma_anual_pct` | `NUMERIC(6, 3)` | no | — | — |
| `fonte` | `TEXT` | no | — | — |
| `justificativa` | `TEXT` | no | — | — |
| `effective_from` | `DATE` | no | — | INDEX |
| `effective_to` | `DATE` | yes | — | — |
| `created_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (classe_auvp) REFERENCES economic_asset_class.code ON DELETE RESTRICT — `(unnamed)`
- FOREIGN KEY (created_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, classe_auvp, effective_from) — `uq_ws_econ_override_ws_classe_from`

**Indexes:**

- `ix_workspace_economic_assumptions_override_classe_auvp` (classe_auvp)
- `ix_workspace_economic_assumptions_override_effective_from` (effective_from)
- `ix_workspace_economic_assumptions_override_workspace_id` (workspace_id)

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

### `workspace_irpf_suggestion_dismissals`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `irpf_year` | `INTEGER` | no | — | — |
| `institution_code` | `VARCHAR(50)` | no | — | — |
| `account_number_norm` | `VARCHAR(30)` | yes | — | — |
| `member_key` | `VARCHAR(50)` | yes | — | — |
| `dismissed_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `created_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |

**Constraints:**

- FOREIGN KEY (created_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, irpf_year, institution_code, account_number_norm) — `uq_workspace_irpf_dismissal`

**Indexes:**

- `ix_workspace_irpf_suggestion_dismissals_workspace_id` (workspace_id)

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

### `workspace_memory_confirmations`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `memory_key` | `VARCHAR(256)` | no | — | — |
| `source_aggregate` | `VARCHAR(64)` | no | — | — |
| `confirmed_value_snapshot` | `TEXT` | yes | — | — |
| `confirmed_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |
| `confirmed_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `note` | `TEXT` | yes | — | — |

**Constraints:**

- FOREIGN KEY (confirmed_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_wmc_ws_confirmed_at` (workspace_id, confirmed_at)
- `ix_wmc_ws_key` (workspace_id, memory_key)
- `ix_workspace_memory_confirmations_workspace_id` (workspace_id)

### `workspace_notes`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `title` | `VARCHAR(200)` | yes | — | — |
| `content` | `TEXT` | no | `''` | — |
| `pinned` | `BOOLEAN` | no | server: `0` | — |
| `author_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- FOREIGN KEY (author_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`

**Indexes:**

- `ix_workspace_notes_workspace_id` (workspace_id)
- `ix_workspace_notes_ws_pinned_updated` (workspace_id, pinned, updated_at)

### `workspace_property_overrides`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `workspace_id` | `VARCHAR(36)` | no | — | FK→workspaces.id, INDEX |
| `property_id` | `VARCHAR(36)` | no | — | FK→property_identity.id |
| `classification` | `VARCHAR(20)` | no | — | — |
| `override_source` | `VARCHAR(20)` | no | `'user_manual'` | — |
| `created_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `updated_at` | `DATETIME` | no | callable: `<lambda>` | — |

**Constraints:**

- CHECK (`classification IN ('residencia_principal','uso_pessoal','locado','comercial','especulacao','nu_proprietario','desconhecido')`) — `chk_classification_enum`
- CHECK (`override_source IN ('user_manual','fuzzy_match_accepted','migration_keyword')`) — `chk_override_source_enum`
- FOREIGN KEY (created_by_user_id) REFERENCES users.id ON DELETE SET NULL — `(unnamed)`
- FOREIGN KEY (property_id) REFERENCES property_identity.id ON DELETE CASCADE — `(unnamed)`
- FOREIGN KEY (workspace_id) REFERENCES workspaces.id ON DELETE CASCADE — `(unnamed)`
- UNIQUE (workspace_id, property_id) — `uq_workspace_property`

**Indexes:**

- `ix_workspace_property_overrides_workspace_id` (workspace_id)
- UNIQUE `uq_workspace_one_residencia_principal` (workspace_id)

### `workspaces`

| Column | Type | Nullable | Default | Tags |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | callable: `<lambda>` | PK |
| `name` | `VARCHAR(255)` | no | — | — |
| `family_surname` | `VARCHAR(255)` | yes | — | — |
| `owner_id` | `VARCHAR(36)` | no | — | FK→users.id |
| `created_at` | `DATETIME` | no | callable: `<lambda>` | — |
| `monthly_llm_budget_usd` | `NUMERIC(10, 2)` | no | server: `5.00` | — |
| `deleted_at` | `DATETIME` | yes | — | INDEX |
| `business_profile_json` | `JSON` | yes | — | — |
| `rule_cap_override` | `INTEGER` | yes | — | — |
| `residencia_status` | `VARCHAR(20)` | no | server: `undeclared` | — |
| `imoveis_no_if` | `BOOLEAN` | no | server: `0` | — |
| `imoveis_no_if_set_at` | `DATETIME` | yes | — | — |
| `imoveis_no_if_set_by_user_id` | `VARCHAR(36)` | yes | — | FK→users.id |

**Constraints:**

- FOREIGN KEY (imoveis_no_if_set_by_user_id) REFERENCES users.id ON DELETE SET NULL — `fk_workspaces_imoveis_no_if_set_by_user_id`
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

- `documents.doc_type → (bank_statement, comprovante_bem, credit_card_bill, e1_5_baseline_json, e1_members_json, informe_rendimentos_anuais, investment_report, irpf, other)`
- `documents.status → (classifying, error, needs_password, processed, processing, ready, unlocking, uploaded)`
- `pipeline_runs.status → (cancelled, completed, failed, needs_review, partial_failure, pending, resuming, running)`
- `pipeline_stage_logs.status → (completed, failed, needs_review, pending, running, skipped, skipped_free_tier)`
- `stage_reviews.status → (approved, edited, pending)`

### 4. Colunas JSON (observação, não risco)

Campos JSON exigem schema explícito (documentado em `config/schemas/*.json` ou docstring do model) para serem portáveis cross-language.

- `audit_logs.details`
- `bank_accounts.co_titulares`
- `bank_accounts.irpf_snapshots`
- `category_templates.default_keywords`
- `category_templates.metadata_json`
- `decision_events.payload`
- `decisions.context_snapshot`
- `documents.classification_meta`
- `family_members.extra`
- `feature_flags.flags_json`
- `fiscal_parameters.ir_brackets`
- `goals.derived_json`
- `goals.params_json`
- `institution_catalog.metadata_json`
- `institution_configs.config_json`
- `pipeline_artifacts.content_json`
- `pipeline_configs.config_json`
- `pipeline_runs.config_snapshot`
- `pipeline_runs.incremental_doc_ids`
- `pipeline_stage_logs.output_summary`
- `report_layouts.config_json`
- `reports.premissas_snapshot_json`
- `reports.tasks_snapshot_json`
- `risks.mitigation_protection_ids`
- `risks.mitigations_decision_ids`
- `stage_reviews.edited_output_json`
- `stage_reviews.original_output_json`
- `stage_reviews.validation_issues`
- `task_suggestions.proposed_payload`
- `transfer_configs.config_json`
- `workspace_category_overrides.keywords_override`
- `workspaces.business_profile_json`

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

### `asset_catalog` → `type AssetCatalog struct`

```go
type AssetCatalog struct {
	Id string `db:"id" json:"id"`
	CatalogVersion int `db:"catalog_version" json:"catalog_version"`
	Ticker *string `db:"ticker" json:"ticker"`
	Cnpj *string `db:"cnpj" json:"cnpj"`
	MatchKeyword *string `db:"match_keyword" json:"match_keyword"`
	AssetClass string `db:"asset_class" json:"asset_class"`
	LastroMoeda string `db:"lastro_moeda" json:"lastro_moeda"`
	LastroSource string `db:"lastro_source" json:"lastro_source"`
	Notes *string `db:"notes" json:"notes"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
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
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	InstitutionCode string `db:"institution_code" json:"institution_code"`
	AccountType string `db:"account_type" json:"account_type"`
	Agency *string `db:"agency" json:"agency"`
	AccountNumber *string `db:"account_number" json:"account_number"`
	Label *string `db:"label" json:"label"`
	SourceTier *string `db:"source_tier" json:"source_tier"`
	IsJoint bool `db:"is_joint" json:"is_joint"`
	CoTitulares json.RawMessage `db:"co_titulares" json:"co_titulares"`
	IrpfSnapshots json.RawMessage `db:"irpf_snapshots" json:"irpf_snapshots"`
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
	Order int `db:"order" json:"order"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `categorization_rules` → `type CategorizationRule struct`

```go
type CategorizationRule struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Keyword string `db:"keyword" json:"keyword"`
	TargetCategory string `db:"target_category" json:"target_category"`
	Priority int `db:"priority" json:"priority"`
	Enabled bool `db:"enabled" json:"enabled"`
	OriginOverrideId *string `db:"origin_override_id" json:"origin_override_id"`
	CreatedByUserId *string `db:"created_by_user_id" json:"created_by_user_id"`
	AppliedCount int `db:"applied_count" json:"applied_count"`
	RevertCountManualEdit int `db:"revert_count_manual_edit" json:"revert_count_manual_edit"`
	RevertCountRuleDisabled int `db:"revert_count_rule_disabled" json:"revert_count_rule_disabled"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
	DeletedAt *time.Time `db:"deleted_at" json:"deleted_at"`
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

### `category_templates` → `type CategoryTemplate struct`

```go
type CategoryTemplate struct {
	Id string `db:"id" json:"id"`
	TemplateVersion int `db:"template_version" json:"template_version"`
	Key string `db:"key" json:"key"`
	ParentKey *string `db:"parent_key" json:"parent_key"`
	Label string `db:"label" json:"label"`
	CategoryType string `db:"category_type" json:"category_type"`
	DefaultKeywords json.RawMessage `db:"default_keywords" json:"default_keywords"`
	DefaultMonthlyCapBrlCents *int64 `db:"default_monthly_cap_brl_cents" json:"default_monthly_cap_brl_cents"`
	SortOrder int `db:"sort_order" json:"sort_order"`
	MetadataJson json.RawMessage `db:"metadata_json" json:"metadata_json"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `data_export_requests` → `type DataExportRequest struct`

```go
type DataExportRequest struct {
	Id string `db:"id" json:"id"`
	UserId string `db:"user_id" json:"user_id"`
	Status string `db:"status" json:"status"`
	DownloadToken *string `db:"download_token" json:"download_token"`
	ExpiresAt *time.Time `db:"expires_at" json:"expires_at"`
	FilePath *string `db:"file_path" json:"file_path"`
	FileSizeBytes *int64 `db:"file_size_bytes" json:"file_size_bytes"`
	ErrorMessage *string `db:"error_message" json:"error_message"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	CompletedAt *time.Time `db:"completed_at" json:"completed_at"`
}
```

### `data_source` → `type DataSource struct`

```go
type DataSource struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Kind string `db:"kind" json:"kind"`
	InstitutionCode string `db:"institution_code" json:"institution_code"`
	ExternalAccountRef string `db:"external_account_ref" json:"external_account_ref"`
	DisplayName string `db:"display_name" json:"display_name"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `debt` → `type Debt struct`

```go
type Debt struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	FamilyMemberId *string `db:"family_member_id" json:"family_member_id"`
	PropertyId *string `db:"property_id" json:"property_id"`
	Tipo string `db:"tipo" json:"tipo"`
	Descricao *string `db:"descricao" json:"descricao"`
	SaldoDevedorCents int64 `db:"saldo_devedor_cents" json:"saldo_devedor_cents"`
	ParcelaMensalCents *int64 `db:"parcela_mensal_cents" json:"parcela_mensal_cents"`
	TaxaJurosAa *decimal.Decimal `db:"taxa_juros_aa" json:"taxa_juros_aa"`
	PrazoMesesRestantes *int `db:"prazo_meses_restantes" json:"prazo_meses_restantes"`
	DataContratacao *time.Time `db:"data_contratacao" json:"data_contratacao"`
	Source string `db:"source" json:"source"`
	MigrationSourceKey *string `db:"migration_source_key" json:"migration_source_key"`
	NeedsReview bool `db:"needs_review" json:"needs_review"`
	PercentualAtribuicaoImovel *decimal.Decimal `db:"percentual_atribuicao_imovel" json:"percentual_atribuicao_imovel"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `decision_events` → `type DecisionEvent struct`

```go
type DecisionEvent struct {
	Id string `db:"id" json:"id"`
	DecisionId string `db:"decision_id" json:"decision_id"`
	EventType string `db:"event_type" json:"event_type"`
	OccurredAt time.Time `db:"occurred_at" json:"occurred_at"`
	Actor string `db:"actor" json:"actor"`
	Payload json.RawMessage `db:"payload" json:"payload"`
}
```

### `decisions` → `type Decision struct`

```go
type Decision struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Code string `db:"code" json:"code"`
	Title string `db:"title" json:"title"`
	Rationale *string `db:"rationale" json:"rationale"`
	AmountBrlCents *int64 `db:"amount_brl_cents" json:"amount_brl_cents"`
	Status string `db:"status" json:"status"`
	SupersedesId *string `db:"supersedes_id" json:"supersedes_id"`
	DecidedAt *time.Time `db:"decided_at" json:"decided_at"`
	ExecutedAt *time.Time `db:"executed_at" json:"executed_at"`
	TargetField *string `db:"target_field" json:"target_field"`
	TargetValue *string `db:"target_value" json:"target_value"`
	TargetValueType *string `db:"target_value_type" json:"target_value_type"`
	ContextSnapshot json.RawMessage `db:"context_snapshot" json:"context_snapshot"`
	Impact1yBrlCents *int64 `db:"impact_1y_brl_cents" json:"impact_1y_brl_cents"`
	Impact10yBrlCents *int64 `db:"impact_10y_brl_cents" json:"impact_10y_brl_cents"`
	Horizon string `db:"horizon" json:"horizon"`
	Priority *string `db:"priority" json:"priority"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
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

### `economic_asset_class` → `type EconomicAssetClas struct`

```go
type EconomicAssetClas struct {
	Code string `db:"code" json:"code"`
	Label string `db:"label" json:"label"`
	SortOrder int `db:"sort_order" json:"sort_order"`
	Active bool `db:"active" json:"active"`
	DeprecatedAt *time.Time `db:"deprecated_at" json:"deprecated_at"`
	Description *string `db:"description" json:"description"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `economic_assumptions` → `type EconomicAssumption struct`

```go
type EconomicAssumption struct {
	Id string `db:"id" json:"id"`
	ClasseAuvp string `db:"classe_auvp" json:"classe_auvp"`
	RetornoRealEsperadoPctAnual decimal.Decimal `db:"retorno_real_esperado_pct_anual" json:"retorno_real_esperado_pct_anual"`
	SigmaAnualPct decimal.Decimal `db:"sigma_anual_pct" json:"sigma_anual_pct"`
	Fonte string `db:"fonte" json:"fonte"`
	EffectiveFrom time.Time `db:"effective_from" json:"effective_from"`
	EffectiveTo *time.Time `db:"effective_to" json:"effective_to"`
	CreatedBy string `db:"created_by" json:"created_by"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
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
	UsTaxStatus *string `db:"us_tax_status" json:"us_tax_status"`
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

### `fiscal_parameters` → `type FiscalParameter struct`

```go
type FiscalParameter struct {
	Id string `db:"id" json:"id"`
	Year int `db:"year" json:"year"`
	IrBrackets json.RawMessage `db:"ir_brackets" json:"ir_brackets"`
	PgblLimitBrlCents int64 `db:"pgbl_limit_brl_cents" json:"pgbl_limit_brl_cents"`
	InssCeilingBrlCents int64 `db:"inss_ceiling_brl_cents" json:"inss_ceiling_brl_cents"`
	LucroPresumidoAliquota decimal.Decimal `db:"lucro_presumido_aliquota" json:"lucro_presumido_aliquota"`
	EffectiveFrom time.Time `db:"effective_from" json:"effective_from"`
	EffectiveTo *time.Time `db:"effective_to" json:"effective_to"`
	Source string `db:"source" json:"source"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
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

### `institution_catalog` → `type InstitutionCatalog struct`

```go
type InstitutionCatalog struct {
	Id string `db:"id" json:"id"`
	Code string `db:"code" json:"code"`
	Name string `db:"name" json:"name"`
	DefaultParser *string `db:"default_parser" json:"default_parser"`
	Category string `db:"category" json:"category"`
	TaxRegime string `db:"tax_regime" json:"tax_regime"`
	MetadataJson json.RawMessage `db:"metadata_json" json:"metadata_json"`
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

### `llm_call_log` → `type LlmCallLog struct`

```go
type LlmCallLog struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Stage string `db:"stage" json:"stage"`
	ModelName string `db:"model_name" json:"model_name"`
	PromptVersion *string `db:"prompt_version" json:"prompt_version"`
	TokensIn int `db:"tokens_in" json:"tokens_in"`
	TokensOut int `db:"tokens_out" json:"tokens_out"`
	CostUsd decimal.Decimal `db:"cost_usd" json:"cost_usd"`
	CostKnown bool `db:"cost_known" json:"cost_known"`
	DurationMs int `db:"duration_ms" json:"duration_ms"`
	PipelineRunId *string `db:"pipeline_run_id" json:"pipeline_run_id"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
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

### `market_rates` → `type MarketRate struct`

```go
type MarketRate struct {
	Id string `db:"id" json:"id"`
	Pair string `db:"pair" json:"pair"`
	Rate decimal.Decimal `db:"rate" json:"rate"`
	ObservedAt time.Time `db:"observed_at" json:"observed_at"`
	ReferenceMonth *string `db:"reference_month" json:"reference_month"`
	Source string `db:"source" json:"source"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
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
	DataSourceId *string `db:"data_source_id" json:"data_source_id"`
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

### `pipeline_run_costs` → `type PipelineRunCost struct`

```go
type PipelineRunCost struct {
	Id int `db:"id" json:"id"`
	PipelineRunId string `db:"pipeline_run_id" json:"pipeline_run_id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Stage string `db:"stage" json:"stage"`
	ModelId string `db:"model_id" json:"model_id"`
	TokensIn int `db:"tokens_in" json:"tokens_in"`
	TokensOut int `db:"tokens_out" json:"tokens_out"`
	CostUsdCents int64 `db:"cost_usd_cents" json:"cost_usd_cents"`
	LatencyMs int `db:"latency_ms" json:"latency_ms"`
	ToolIterations *int `db:"tool_iterations" json:"tool_iterations"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
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
	LastHeartbeatAt *time.Time `db:"last_heartbeat_at" json:"last_heartbeat_at"`
	FailureReason *string `db:"failure_reason" json:"failure_reason"`
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

### `planner_field_requests` → `type PlannerFieldRequest struct`

```go
type PlannerFieldRequest struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	PlannerReviewId string `db:"planner_review_id" json:"planner_review_id"`
	FieldPath string `db:"field_path" json:"field_path"`
	Motivo string `db:"motivo" json:"motivo"`
	Reason *string `db:"reason" json:"reason"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `planner_review_metadata` → `type PlannerReviewMetadata struct`

```go
type PlannerReviewMetadata struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	PipelineRunId string `db:"pipeline_run_id" json:"pipeline_run_id"`
	PipelineArtifactId int `db:"pipeline_artifact_id" json:"pipeline_artifact_id"`
	E5ArtifactId int `db:"e5_artifact_id" json:"e5_artifact_id"`
	Status string `db:"status" json:"status"`
	SupersedesId *string `db:"supersedes_id" json:"supersedes_id"`
	SupersededById *string `db:"superseded_by_id" json:"superseded_by_id"`
	PersonaHash string `db:"persona_hash" json:"persona_hash"`
	ManifestVersion string `db:"manifest_version" json:"manifest_version"`
	SchemaVersion string `db:"schema_version" json:"schema_version"`
	ModelId string `db:"model_id" json:"model_id"`
	ImmutableHash *string `db:"immutable_hash" json:"immutable_hash"`
	TierAtGeneration string `db:"tier_at_generation" json:"tier_at_generation"`
	ItemsShownCount int `db:"items_shown_count" json:"items_shown_count"`
	ItemsGatedCount int `db:"items_gated_count" json:"items_gated_count"`
	CostUsdCents int64 `db:"cost_usd_cents" json:"cost_usd_cents"`
	TokensIn int `db:"tokens_in" json:"tokens_in"`
	TokensOut int `db:"tokens_out" json:"tokens_out"`
	ToolIterations int `db:"tool_iterations" json:"tool_iterations"`
	LatencyMs int `db:"latency_ms" json:"latency_ms"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	PublishedAt *time.Time `db:"published_at" json:"published_at"`
	SupersededAt *time.Time `db:"superseded_at" json:"superseded_at"`
}
```

### `property_identity` → `type PropertyIdentity struct`

```go
type PropertyIdentity struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	TitularKey string `db:"titular_key" json:"titular_key"`
	CodigoRfb string `db:"codigo_rfb" json:"codigo_rfb"`
	EnderecoCanonical *string `db:"endereco_canonical" json:"endereco_canonical"`
	FirstSeenYear int `db:"first_seen_year" json:"first_seen_year"`
	DescricaoSample *string `db:"descricao_sample" json:"descricao_sample"`
	LowConfidence bool `db:"low_confidence" json:"low_confidence"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `property_market_value` → `type PropertyMarketValue struct`

```go
type PropertyMarketValue struct {
	Id string `db:"id" json:"id"`
	PropertyId string `db:"property_id" json:"property_id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ValorBrlCents int64 `db:"valor_brl_cents" json:"valor_brl_cents"`
	ValuationDate time.Time `db:"valuation_date" json:"valuation_date"`
	Source string `db:"source" json:"source"`
	Confidence *decimal.Decimal `db:"confidence" json:"confidence"`
	Notes *string `db:"notes" json:"notes"`
	SupersededById *string `db:"superseded_by_id" json:"superseded_by_id"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	CreatedByUserId *string `db:"created_by_user_id" json:"created_by_user_id"`
}
```

### `protections` → `type Protection struct`

```go
type Protection struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Category string `db:"category" json:"category"`
	HolderFamilyMemberId *string `db:"holder_family_member_id" json:"holder_family_member_id"`
	Insurer *string `db:"insurer" json:"insurer"`
	PolicyRef *string `db:"policy_ref" json:"policy_ref"`
	CoverageBrlCents int64 `db:"coverage_brl_cents" json:"coverage_brl_cents"`
	PremiumMonthlyBrlCents *int64 `db:"premium_monthly_brl_cents" json:"premium_monthly_brl_cents"`
	CoverageType *string `db:"coverage_type" json:"coverage_type"`
	StartsAt time.Time `db:"starts_at" json:"starts_at"`
	EndsAt *time.Time `db:"ends_at" json:"ends_at"`
	Status string `db:"status" json:"status"`
	Notes *string `db:"notes" json:"notes"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
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

### `report_publications` → `type ReportPublication struct`

```go
type ReportPublication struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	PeriodYyyymm string `db:"period_yyyymm" json:"period_yyyymm"`
	ArtifactId int `db:"artifact_id" json:"artifact_id"`
	PublishedAt time.Time `db:"published_at" json:"published_at"`
	PublishedBy string `db:"published_by" json:"published_by"`
	ImmutableHash string `db:"immutable_hash" json:"immutable_hash"`
	UnpublishedAt *time.Time `db:"unpublished_at" json:"unpublished_at"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
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
	PatrimonioLiquido *decimal.Decimal `db:"patrimonio_liquido" json:"patrimonio_liquido"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `review_reasons` → `type ReviewReason struct`

```go
type ReviewReason struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	PipelineRunId string `db:"pipeline_run_id" json:"pipeline_run_id"`
	Stage string `db:"stage" json:"stage"`
	Code string `db:"code" json:"code"`
	ArtifactKey string `db:"artifact_key" json:"artifact_key"`
	DocumentId *string `db:"document_id" json:"document_id"`
	OffendingValue string `db:"offending_value" json:"offending_value"`
	Expected string `db:"expected" json:"expected"`
	Message string `db:"message" json:"message"`
	OccurrenceCount int `db:"occurrence_count" json:"occurrence_count"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `risks` → `type Risk struct`

```go
type Risk struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Code string `db:"code" json:"code"`
	Name string `db:"name" json:"name"`
	Rationale string `db:"rationale" json:"rationale"`
	Probability *string `db:"probability" json:"probability"`
	ImpactLevel string `db:"impact_level" json:"impact_level"`
	ImpactBrlCents *int64 `db:"impact_brl_cents" json:"impact_brl_cents"`
	Status string `db:"status" json:"status"`
	MitigationsDecisionIds json.RawMessage `db:"mitigations_decision_ids" json:"mitigations_decision_ids"`
	MitigationProtectionIds json.RawMessage `db:"mitigation_protection_ids" json:"mitigation_protection_ids"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
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
	ValidationIssues json.RawMessage `db:"validation_issues" json:"validation_issues"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	ReviewedAt *time.Time `db:"reviewed_at" json:"reviewed_at"`
}
```

### `suggestions` → `type Suggestion struct`

```go
type Suggestion struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ReportId *string `db:"report_id" json:"report_id"`
	SectionId string `db:"section_id" json:"section_id"`
	Kind string `db:"kind" json:"kind"`
	Category *string `db:"category" json:"category"`
	Origin string `db:"origin" json:"origin"`
	Severity string `db:"severity" json:"severity"`
	Title string `db:"title" json:"title"`
	Rationale string `db:"rationale" json:"rationale"`
	AmountBrlCents *int64 `db:"amount_brl_cents" json:"amount_brl_cents"`
	DedupKey string `db:"dedup_key" json:"dedup_key"`
	Status string `db:"status" json:"status"`
	AcceptedDecisionId *string `db:"accepted_decision_id" json:"accepted_decision_id"`
	DismissedReason *string `db:"dismissed_reason" json:"dismissed_reason"`
	AcceptedAt *time.Time `db:"accepted_at" json:"accepted_at"`
	DismissedAt *time.Time `db:"dismissed_at" json:"dismissed_at"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
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
	DedupKey *string `db:"dedup_key" json:"dedup_key"`
	Status string `db:"status" json:"status"`
	RejectionReason *string `db:"rejection_reason" json:"rejection_reason"`
	SupersededAt *time.Time `db:"superseded_at" json:"superseded_at"`
	SupersededByRunId *string `db:"superseded_by_run_id" json:"superseded_by_run_id"`
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
	DerivedFromDecisionId *string `db:"derived_from_decision_id" json:"derived_from_decision_id"`
	BoardColumn *string `db:"board_column" json:"board_column"`
	BoardOrder *int `db:"board_order" json:"board_order"`
	Urgency *string `db:"urgency" json:"urgency"`
	OriginReportId *string `db:"origin_report_id" json:"origin_report_id"`
	IsBoardOnly bool `db:"is_board_only" json:"is_board_only"`
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
	Source string `db:"source" json:"source"`
	RuleId *string `db:"rule_id" json:"rule_id"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	DeletedAt *time.Time `db:"deleted_at" json:"deleted_at"`
	NaturalKeyHash *string `db:"natural_key_hash" json:"natural_key_hash"`
	HashVersion *string `db:"hash_version" json:"hash_version"`
	TxData *string `db:"tx_data" json:"tx_data"`
	TxBanco *string `db:"tx_banco" json:"tx_banco"`
	TxTitular *string `db:"tx_titular" json:"tx_titular"`
	TxTipoConta *string `db:"tx_tipo_conta" json:"tx_tipo_conta"`
	TxValorCents *int `db:"tx_valor_cents" json:"tx_valor_cents"`
	TxMoeda *string `db:"tx_moeda" json:"tx_moeda"`
	TxDirection *string `db:"tx_direction" json:"tx_direction"`
	TxDescricao *string `db:"tx_descricao" json:"tx_descricao"`
	OrphanedAt *time.Time `db:"orphaned_at" json:"orphaned_at"`
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
	DeletionRequestedAt *time.Time `db:"deletion_requested_at" json:"deletion_requested_at"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
}
```

### `vehicles` → `type Vehicle struct`

```go
type Vehicle struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Placa string `db:"placa" json:"placa"`
	Renavam string `db:"renavam" json:"renavam"`
	Marca string `db:"marca" json:"marca"`
	Modelo string `db:"modelo" json:"modelo"`
	AnoModelo int `db:"ano_modelo" json:"ano_modelo"`
	AnoFabricacao int `db:"ano_fabricacao" json:"ano_fabricacao"`
	FipeCode *string `db:"fipe_code" json:"fipe_code"`
	Cor *string `db:"cor" json:"cor"`
	Combustivel *string `db:"combustivel" json:"combustivel"`
	CodigoRfb string `db:"codigo_rfb" json:"codigo_rfb"`
	ArchivedAt *time.Time `db:"archived_at" json:"archived_at"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `workspace_asset_overrides` → `type WorkspaceAssetOverride struct`

```go
type WorkspaceAssetOverride struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	AssetMatchKey string `db:"asset_match_key" json:"asset_match_key"`
	MatchKind string `db:"match_kind" json:"match_kind"`
	LastroMoeda string `db:"lastro_moeda" json:"lastro_moeda"`
	OverrideSource string `db:"override_source" json:"override_source"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
	CreatedByUserId *string `db:"created_by_user_id" json:"created_by_user_id"`
}
```

### `workspace_category_overrides` → `type WorkspaceCategoryOverride struct`

```go
type WorkspaceCategoryOverride struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	TemplateKey string `db:"template_key" json:"template_key"`
	LabelOverride *string `db:"label_override" json:"label_override"`
	KeywordsOverride json.RawMessage `db:"keywords_override" json:"keywords_override"`
	MonthlyCapBrlCentsOverride *int64 `db:"monthly_cap_brl_cents_override" json:"monthly_cap_brl_cents_override"`
	Disabled bool `db:"disabled" json:"disabled"`
	UpdatedByUserId *string `db:"updated_by_user_id" json:"updated_by_user_id"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `workspace_economic_assumptions_override` → `type WorkspaceEconomicAssumptionsOverride struct`

```go
type WorkspaceEconomicAssumptionsOverride struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	ClasseAuvp string `db:"classe_auvp" json:"classe_auvp"`
	RetornoRealEsperadoPctAnual decimal.Decimal `db:"retorno_real_esperado_pct_anual" json:"retorno_real_esperado_pct_anual"`
	SigmaAnualPct decimal.Decimal `db:"sigma_anual_pct" json:"sigma_anual_pct"`
	Fonte string `db:"fonte" json:"fonte"`
	Justificativa string `db:"justificativa" json:"justificativa"`
	EffectiveFrom time.Time `db:"effective_from" json:"effective_from"`
	EffectiveTo *time.Time `db:"effective_to" json:"effective_to"`
	CreatedByUserId *string `db:"created_by_user_id" json:"created_by_user_id"`
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

### `workspace_irpf_suggestion_dismissals` → `type WorkspaceIrpfSuggestionDismissal struct`

```go
type WorkspaceIrpfSuggestionDismissal struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	IrpfYear int `db:"irpf_year" json:"irpf_year"`
	InstitutionCode string `db:"institution_code" json:"institution_code"`
	AccountNumberNorm *string `db:"account_number_norm" json:"account_number_norm"`
	MemberKey *string `db:"member_key" json:"member_key"`
	DismissedAt time.Time `db:"dismissed_at" json:"dismissed_at"`
	CreatedByUserId *string `db:"created_by_user_id" json:"created_by_user_id"`
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

### `workspace_memory_confirmations` → `type WorkspaceMemoryConfirmation struct`

```go
type WorkspaceMemoryConfirmation struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	MemoryKey string `db:"memory_key" json:"memory_key"`
	SourceAggregate string `db:"source_aggregate" json:"source_aggregate"`
	ConfirmedValueSnapshot *string `db:"confirmed_value_snapshot" json:"confirmed_value_snapshot"`
	ConfirmedByUserId *string `db:"confirmed_by_user_id" json:"confirmed_by_user_id"`
	ConfirmedAt time.Time `db:"confirmed_at" json:"confirmed_at"`
	Note *string `db:"note" json:"note"`
}
```

### `workspace_notes` → `type WorkspaceNote struct`

```go
type WorkspaceNote struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	Title *string `db:"title" json:"title"`
	Content string `db:"content" json:"content"`
	Pinned bool `db:"pinned" json:"pinned"`
	AuthorUserId *string `db:"author_user_id" json:"author_user_id"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
}
```

### `workspace_property_overrides` → `type WorkspacePropertyOverride struct`

```go
type WorkspacePropertyOverride struct {
	Id string `db:"id" json:"id"`
	WorkspaceId string `db:"workspace_id" json:"workspace_id"`
	PropertyId string `db:"property_id" json:"property_id"`
	Classification string `db:"classification" json:"classification"`
	OverrideSource string `db:"override_source" json:"override_source"`
	CreatedByUserId *string `db:"created_by_user_id" json:"created_by_user_id"`
	CreatedAt time.Time `db:"created_at" json:"created_at"`
	UpdatedAt time.Time `db:"updated_at" json:"updated_at"`
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
	MonthlyLlmBudgetUsd decimal.Decimal `db:"monthly_llm_budget_usd" json:"monthly_llm_budget_usd"`
	DeletedAt *time.Time `db:"deleted_at" json:"deleted_at"`
	BusinessProfileJson json.RawMessage `db:"business_profile_json" json:"business_profile_json"`
	RuleCapOverride *int `db:"rule_cap_override" json:"rule_cap_override"`
	ResidenciaStatus string `db:"residencia_status" json:"residencia_status"`
	ImoveisNoIf bool `db:"imoveis_no_if" json:"imoveis_no_if"`
	ImoveisNoIfSetAt *time.Time `db:"imoveis_no_if_set_at" json:"imoveis_no_if_set_at"`
	ImoveisNoIfSetByUserId *string `db:"imoveis_no_if_set_by_user_id" json:"imoveis_no_if_set_by_user_id"`
}
```
