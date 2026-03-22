-- ============================================================
-- EVEREST NEXUS — Data Scanner Helper Functions
-- SECURITY DEFINER functions for data_scanner.py to query
-- information_schema, pg_catalog, and compute table stats.
-- ============================================================

-- ── nexus_get_table_stats() ──────────────────────────────────────────────
-- Returns metadata for all user tables: row count, size, RLS, columns, FKs.
-- Called by data_scanner.py via /rest/v1/rpc/nexus_get_table_stats
CREATE OR REPLACE FUNCTION nexus_get_table_stats()
RETURNS TABLE (
    table_name       TEXT,
    schema_name      TEXT,
    row_count        BIGINT,
    size_bytes       BIGINT,
    rls_enabled      BOOLEAN,
    column_count     INT,
    has_fk_refs      BOOLEAN,
    last_vacuum      TIMESTAMPTZ,
    last_analyze     TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT
        t.table_name::TEXT,
        t.table_schema::TEXT                                         AS schema_name,
        COALESCE(c.reltuples::BIGINT, 0)                            AS row_count,
        pg_total_relation_size(c.oid)                               AS size_bytes,
        COALESCE(pt.rowsecurity, false)                             AS rls_enabled,
        (SELECT COUNT(*)::INT
           FROM information_schema.columns ic
          WHERE ic.table_name   = t.table_name
            AND ic.table_schema = t.table_schema)                   AS column_count,
        EXISTS (
            SELECT 1
            FROM information_schema.referential_constraints rc
            JOIN information_schema.key_column_usage kcu
              ON kcu.constraint_name = rc.unique_constraint_name
            WHERE kcu.table_name   = t.table_name
              AND kcu.table_schema = t.table_schema
        )                                                            AS has_fk_refs,
        psu.last_vacuum,
        psu.last_analyze
    FROM information_schema.tables t
    LEFT JOIN pg_class c
           ON c.relname = t.table_name
          AND c.relnamespace = (
              SELECT oid FROM pg_namespace WHERE nspname = t.table_schema
          )
    LEFT JOIN pg_tables pt
           ON pt.tablename  = t.table_name
          AND pt.schemaname = t.table_schema
    LEFT JOIN pg_stat_user_tables psu
           ON psu.relname  = t.table_name
          AND psu.schemaname = t.table_schema
    WHERE t.table_type   = 'BASE TABLE'
      AND t.table_schema = 'public'
    ORDER BY size_bytes DESC NULLS LAST;
$$;

GRANT EXECUTE ON FUNCTION nexus_get_table_stats() TO service_role;
GRANT EXECUTE ON FUNCTION nexus_get_table_stats() TO anon;

-- ── nexus_get_table_columns(table_name TEXT) ─────────────────────────────
-- Returns columns for a given table.
CREATE OR REPLACE FUNCTION nexus_get_table_columns(p_table TEXT)
RETURNS TABLE (
    column_name    TEXT,
    data_type      TEXT,
    is_nullable    TEXT,
    column_default TEXT,
    ordinal        INT
)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT
        column_name::TEXT,
        data_type::TEXT,
        is_nullable::TEXT,
        column_default::TEXT,
        ordinal_position::INT
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = p_table
    ORDER BY ordinal_position;
$$;

GRANT EXECUTE ON FUNCTION nexus_get_table_columns(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION nexus_get_table_columns(TEXT) TO anon;

-- ── nexus_get_fk_refs() ───────────────────────────────────────────────────
-- Returns all FK relationships (referenced table → source table).
CREATE OR REPLACE FUNCTION nexus_get_fk_refs()
RETURNS TABLE (
    source_table     TEXT,
    source_column    TEXT,
    referenced_table TEXT,
    referenced_column TEXT
)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT
        kcu.table_name::TEXT                                         AS source_table,
        kcu.column_name::TEXT                                        AS source_column,
        ccu.table_name::TEXT                                         AS referenced_table,
        ccu.column_name::TEXT                                        AS referenced_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON kcu.constraint_name = tc.constraint_name
     AND kcu.table_schema    = tc.table_schema
    JOIN information_schema.constraint_column_usage ccu
      ON ccu.constraint_name = tc.constraint_name
     AND ccu.table_schema    = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema    = 'public';
$$;

GRANT EXECUTE ON FUNCTION nexus_get_fk_refs() TO service_role;
GRANT EXECUTE ON FUNCTION nexus_get_fk_refs() TO anon;

-- ── nexus_count_table_rows(table_name TEXT) ───────────────────────────────
-- Returns exact row count for a table (used for orphan detection).
CREATE OR REPLACE FUNCTION nexus_count_table_rows(p_table TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count BIGINT;
BEGIN
    EXECUTE format('SELECT COUNT(*) FROM %I', p_table) INTO v_count;
    RETURN v_count;
EXCEPTION WHEN OTHERS THEN
    RETURN -1;
END;
$$;

GRANT EXECUTE ON FUNCTION nexus_count_table_rows(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION nexus_count_table_rows(TEXT) TO anon;
