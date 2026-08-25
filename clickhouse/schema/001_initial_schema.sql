-- On-Set War Room — initial ClickHouse Cloud schema
-- Source of truth for DDL. Apply via: python scripts/apply_clickhouse.py --schema
--
-- Tables support: "Which upcoming scenes require CAMERA-02?" → Scenes 43, 48

CREATE DATABASE IF NOT EXISTS on_set_war_room;

CREATE TABLE IF NOT EXISTS on_set_war_room.productions
(
    production_id String,
    name String,
    shoot_date Date
)
ENGINE = MergeTree
ORDER BY (production_id);

CREATE TABLE IF NOT EXISTS on_set_war_room.scenes
(
    production_id String,
    scene_number UInt16,
    title String,
    location_id LowCardinality(String),
    scheduled_start DateTime,
    scheduled_end DateTime,
    status LowCardinality(String) DEFAULT 'scheduled'
)
ENGINE = MergeTree
ORDER BY (production_id, scene_number);

-- ORDER BY leads with requirement filters so CAMERA-02 lookups use the primary key.
CREATE TABLE IF NOT EXISTS on_set_war_room.scene_requirements
(
    production_id String,
    scene_number UInt16,
    requirement_type LowCardinality(String),
    requirement_id String,
    requirement_name String DEFAULT ''
)
ENGINE = MergeTree
ORDER BY (requirement_type, requirement_id, scene_number);

CREATE TABLE IF NOT EXISTS on_set_war_room.resource_status_events
(
    event_id UUID DEFAULT generateUUIDv4(),
    production_id String,
    resource_type LowCardinality(String),
    resource_id String,
    status LowCardinality(String),
    event_time DateTime,
    notes String DEFAULT ''
)
ENGINE = MergeTree
ORDER BY (production_id, resource_type, resource_id, event_time);
