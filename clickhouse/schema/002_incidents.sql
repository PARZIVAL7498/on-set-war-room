-- Incidents + agent action observability (MVP)
-- Apply via: python scripts/apply_clickhouse.py --schema
-- Compatible with Midnight Protocol IDs (String production_id, UInt16 scene_number).

CREATE TABLE IF NOT EXISTS on_set_war_room.incidents
(
    incident_id String,
    production_id String,
    event_id String,
    status LowCardinality(String) DEFAULT 'open',
    risk_level LowCardinality(String),
    risk_score UInt8,
    risk_factors String DEFAULT '[]',
    affected_scenes Array(UInt16),
    evidence_json String,
    recommended_scene UInt16 DEFAULT 0,
    pivot_reasons String DEFAULT '[]',
    narrative String DEFAULT '',
    timeline_json String DEFAULT '[]',
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (production_id, created_at, incident_id);

CREATE TABLE IF NOT EXISTS on_set_war_room.agent_actions
(
    action_id String,
    incident_id String,
    step_name LowCardinality(String),
    agent_name LowCardinality(String),
    tool_name LowCardinality(String) DEFAULT '',
    query_summary String DEFAULT '',
    latency_ms Float64 DEFAULT 0,
    row_count UInt32 DEFAULT 0,
    status LowCardinality(String) DEFAULT 'ok',
    detail String DEFAULT '',
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (incident_id, created_at, action_id);
