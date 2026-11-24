-- Generated from the live FK graph at Alembic 20261124_0028 (ACC-14).
-- Usage: psql ... -v tenant_id=<uuid> -v confirm=DELETE -f tenant_data_deletion.sql
-- Deletes tenant business data child-first; RETAINS financial/audit records and
-- anonymises the tenant row, because every financial table cascades from tenants.
\set ON_ERROR_STOP on
\if :{?tenant_id}
\else
  \echo 'error: pass -v tenant_id=<uuid>'
  \quit 2
\endif
BEGIN;
SELECT set_config('yance.deletion_tenant', :'tenant_id', true);
SELECT id, name, slug FROM tenants WHERE id = :'tenant_id';
DELETE FROM agent_retries WHERE tenant_id = :'tenant_id';
DELETE FROM agent_run_errors WHERE tenant_id = :'tenant_id';
DELETE FROM tool_calls WHERE tenant_id = :'tenant_id';
DELETE FROM agent_steps WHERE tenant_id = :'tenant_id';
DELETE FROM artifacts WHERE tenant_id = :'tenant_id';
DELETE FROM demo_scenarios WHERE tenant_id = :'tenant_id';
DELETE FROM evaluation_dimension_scores WHERE tenant_id = :'tenant_id';
DELETE FROM evaluation_errors WHERE tenant_id = :'tenant_id';
DELETE FROM evaluation_evidence WHERE tenant_id = :'tenant_id';
DELETE FROM evaluations WHERE tenant_id = :'tenant_id';
DELETE FROM agent_runs WHERE tenant_id = :'tenant_id';
DELETE FROM analytics_events WHERE tenant_id = :'tenant_id';
DELETE FROM api_keys WHERE tenant_id = :'tenant_id';
DELETE FROM application_activities WHERE tenant_id = :'tenant_id';
DELETE FROM application_artifacts WHERE tenant_id = :'tenant_id';
DELETE FROM application_comments WHERE tenant_id = :'tenant_id';
DELETE FROM application_document_links WHERE tenant_id = :'tenant_id';
DELETE FROM application_requirements WHERE tenant_id = :'tenant_id';
DELETE FROM milestones WHERE tenant_id = :'tenant_id';
DELETE FROM revision_requests WHERE tenant_id = :'tenant_id';
DELETE FROM deliverables WHERE tenant_id = :'tenant_id';
DELETE FROM tasks WHERE tenant_id = :'tenant_id';
DELETE FROM applications WHERE tenant_id = :'tenant_id';
DELETE FROM company_facts WHERE tenant_id = :'tenant_id';
DELETE FROM evidence WHERE tenant_id = :'tenant_id';
DELETE FROM eligibility_results WHERE tenant_id = :'tenant_id';
DELETE FROM opportunities WHERE tenant_id = :'tenant_id';
DELETE FROM policy_scans WHERE tenant_id = :'tenant_id';
DELETE FROM company_profile_versions WHERE tenant_id = :'tenant_id';
DELETE FROM company_profiles WHERE tenant_id = :'tenant_id';
DELETE FROM document_fact_candidates WHERE tenant_id = :'tenant_id';
DELETE FROM document_chunks WHERE tenant_id = :'tenant_id';
DELETE FROM document_contents WHERE tenant_id = :'tenant_id';
DELETE FROM document_ingestion_runs WHERE tenant_id = :'tenant_id';
DELETE FROM documents WHERE tenant_id = :'tenant_id';
DELETE FROM workflow_runs WHERE tenant_id = :'tenant_id';
DELETE FROM companies WHERE tenant_id = :'tenant_id';
DELETE FROM eligibility_rules WHERE tenant_id = :'tenant_id';
DELETE FROM eval_runs WHERE tenant_id = :'tenant_id';
DELETE FROM export_jobs WHERE tenant_id = :'tenant_id';
DELETE FROM feedback WHERE tenant_id = :'tenant_id';
DELETE FROM memberships WHERE tenant_id = :'tenant_id';
DELETE FROM notifications WHERE tenant_id = :'tenant_id';
DELETE FROM policy_benefits WHERE tenant_id = :'tenant_id';
DELETE FROM policy_chunks WHERE tenant_id = :'tenant_id';
DELETE FROM policy_rules WHERE tenant_id = :'tenant_id';
DELETE FROM required_materials WHERE tenant_id = :'tenant_id';
DELETE FROM policy_versions WHERE tenant_id = :'tenant_id';
DELETE FROM policies WHERE tenant_id = :'tenant_id';
DELETE FROM retention_policies WHERE tenant_id = :'tenant_id';
DELETE FROM tenant_feature_flags WHERE tenant_id = :'tenant_id';
DELETE FROM usage_budgets WHERE tenant_id = :'tenant_id';
DELETE FROM users WHERE tenant_id = :'tenant_id';
-- Tenant row is kept (retained financial rows reference it) but anonymised and disabled.
UPDATE tenants SET name = '已注销租户', slug = 'deleted-' || replace(id::text, '-', ''), is_active = false WHERE id = :'tenant_id';
-- Post-check: every non-retained tenant table must now be empty for this tenant.
DO $$
DECLARE t text; n bigint; tid uuid := current_setting('yance.deletion_tenant')::uuid;
BEGIN
  FOR t IN SELECT table_name FROM information_schema.columns
           WHERE table_schema = 'public' AND column_name = 'tenant_id'
             AND table_name NOT IN ('audit_logs', 'deletion_requests', 'entitlements', 'invoices', 'orders', 'payment_events', 'payments', 'subscription_items', 'subscriptions', 'usage_records')
  LOOP
    EXECUTE format('SELECT count(*) FROM %I WHERE tenant_id = $1', t) INTO n USING tid;
    IF n > 0 THEN RAISE EXCEPTION 'table % still has % rows for tenant', t, n; END IF;
  END LOOP;
END $$;
\if :{?confirm}
\else
  \set confirm none
\endif
SELECT :'confirm' = 'DELETE' AS do_commit \gset
\if :do_commit
  COMMIT;
  \echo 'committed'
\else
  ROLLBACK;
  \echo 'dry run: rolled back (pass -v confirm=DELETE to commit)'
\endif
