-- Sample queries for Midnight Protocol / CAMERA-02 demo
-- Run against ClickHouse Cloud after schema + seed are applied.

-- 1) Confirm production exists
SELECT production_id, name, shoot_date
FROM on_set_war_room.productions;

-- 2) List all scenes
SELECT scene_number, title, location_id, scheduled_start, status
FROM on_set_war_room.scenes
WHERE production_id = 'prod-midnight-protocol'
ORDER BY scene_number;

-- 3) CORE DEMO: Which upcoming scenes require CAMERA-02?
-- Expected: Scene 43, Scene 48
SELECT
    s.scene_number,
    s.title,
    s.scheduled_start,
    s.status
FROM on_set_war_room.scene_requirements AS r
ANY INNER JOIN on_set_war_room.scenes AS s
    ON r.production_id = s.production_id
   AND r.scene_number = s.scene_number
WHERE r.requirement_type = 'equipment'
  AND r.requirement_id = 'CAMERA-02'
  AND s.status = 'scheduled'
ORDER BY s.scheduled_start;

-- 4) Confirm Scene 47 does NOT depend on CAMERA-02
SELECT scene_number, requirement_type, requirement_id, requirement_name
FROM on_set_war_room.scene_requirements
WHERE scene_number = 47
ORDER BY requirement_type, requirement_id;

-- 5) Latest CAMERA-02 status events (seed + ingested)
SELECT toString(event_id) AS event_id, resource_id, status, event_time, notes
FROM on_set_war_room.resource_status_events
WHERE resource_type = 'equipment'
  AND resource_id = 'CAMERA-02'
ORDER BY event_time DESC
LIMIT 10;
