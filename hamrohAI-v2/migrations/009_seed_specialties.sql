-- 009_seed_specialties.sql — specialty list is data, not code (PLAN.md
-- principle 1). Adding a new specialty later is a migration row, never a
-- Python change.

INSERT INTO specialties (key, label) VALUES
    ('umumiy_amaliyot',  'Umumiy amaliyot shifokori'),
    ('endokrinolog',     'Endokrinolog'),
    ('kardiolog',        'Kardiolog'),
    ('terapevt',         'Terapevt'),
    ('nevropatolog',     'Nevropatolog'),
    ('ginekolog',        'Ginekolog-akusher'),
    ('pediatr',          'Pediatr'),
    ('jarroh',           'Jarroh'),
    ('urolog',           'Urolog'),
    ('dermatolog',       'Dermatolog'),
    ('oftalmolog',       'Oftalmolog'),
    ('stomatolog',       'Stomatolog');
