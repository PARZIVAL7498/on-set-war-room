-- Midnight Protocol — demo seed for CAMERA-02 failure MVP
-- Apply via: python scripts/apply_clickhouse.py --seed
--
-- CAMERA-02 is required by Scene 43 and Scene 48.
-- Scene 47 does NOT require CAMERA-02 (valid pivot candidate later).

INSERT INTO on_set_war_room.productions
    (production_id, name, shoot_date)
VALUES
    ('prod-midnight-protocol', 'MIDNIGHT PROTOCOL', '2026-08-25');

INSERT INTO on_set_war_room.scenes
    (production_id, scene_number, title, location_id, scheduled_start, scheduled_end, status)
VALUES
    ('prod-midnight-protocol', 42, 'Lobby Arrival', 'LOC-SOUNDSTAGE-A', '2026-08-25 08:00:00', '2026-08-25 09:30:00', 'completed'),
    ('prod-midnight-protocol', 43, 'Rooftop Chase — Unit A', 'LOC-SOUNDSTAGE-A', '2026-08-25 10:00:00', '2026-08-25 12:00:00', 'scheduled'),
    ('prod-midnight-protocol', 47, 'Safehouse Interrogation', 'LOC-SOUNDSTAGE-A', '2026-08-25 13:00:00', '2026-08-25 15:00:00', 'scheduled'),
    ('prod-midnight-protocol', 48, 'Night Exterior — Camera Intensive', 'LOC-EXTERIOR-B', '2026-08-25 16:00:00', '2026-08-25 19:00:00', 'scheduled'),
    ('prod-midnight-protocol', 52, 'End Credits Pickup', 'LOC-SOUNDSTAGE-A', '2026-08-25 20:00:00', '2026-08-25 21:00:00', 'scheduled');

INSERT INTO on_set_war_room.scene_requirements
    (production_id, scene_number, requirement_type, requirement_id, requirement_name)
VALUES
    -- Scene 43: CAMERA-02 + Actor B + Soundstage A
    ('prod-midnight-protocol', 43, 'equipment', 'CAMERA-02', 'Primary A-Cam'),
    ('prod-midnight-protocol', 43, 'actor', 'ACTOR-B', 'Actor B'),
    ('prod-midnight-protocol', 43, 'location', 'LOC-SOUNDSTAGE-A', 'Soundstage A'),

    -- Scene 47: NO CAMERA-02 — dialogue-heavy, handheld package
    ('prod-midnight-protocol', 47, 'equipment', 'CAMERA-01', 'B-Cam / Handheld'),
    ('prod-midnight-protocol', 47, 'actor', 'ACTOR-C', 'Actor C'),
    ('prod-midnight-protocol', 47, 'location', 'LOC-SOUNDSTAGE-A', 'Soundstage A'),

    -- Scene 48: CAMERA-02 + Actor B + Exterior
    ('prod-midnight-protocol', 48, 'equipment', 'CAMERA-02', 'Primary A-Cam'),
    ('prod-midnight-protocol', 48, 'actor', 'ACTOR-B', 'Actor B'),
    ('prod-midnight-protocol', 48, 'location', 'LOC-EXTERIOR-B', 'Exterior Lot B'),

    -- Scene 42 / 52 light deps (no CAMERA-02)
    ('prod-midnight-protocol', 42, 'equipment', 'CAMERA-01', 'B-Cam / Handheld'),
    ('prod-midnight-protocol', 42, 'location', 'LOC-SOUNDSTAGE-A', 'Soundstage A'),
    ('prod-midnight-protocol', 52, 'equipment', 'CAMERA-01', 'B-Cam / Handheld'),
    ('prod-midnight-protocol', 52, 'location', 'LOC-SOUNDSTAGE-A', 'Soundstage A');

-- Seed an operational event so the events table is non-empty for demos.
INSERT INTO on_set_war_room.resource_status_events
    (production_id, resource_type, resource_id, status, event_time, notes)
VALUES
    ('prod-midnight-protocol', 'equipment', 'CAMERA-02', 'DOWN', '2026-08-25 09:45:00', 'Primary A-Cam offline — link drop reported on set');
