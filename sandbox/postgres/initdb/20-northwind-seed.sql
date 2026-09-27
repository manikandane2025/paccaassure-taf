-- Northwind Health synthetic seed. Deterministic: the same rows on every reset.
--   nwh_reset_seed() truncates app data and re-inserts it; the API's POST /admin/reset calls it.
-- Rules: fictitious names only; SSN-shaped values only in the never-issued 9xx range; phone numbers in
-- the fictional 555-01xx range; e-mail under the reserved .example TLD; synthetic credentials contain
-- "Northwind" (gitleaks allowlist).
--
-- Well-known rows for scenarios (see sandbox/README.md):
--   NWH-M000123  Ava Thompson, ACTIVE, Gold Plus, 5 claims (one per status)
--   NWH-M000150  Seán O'Brien-Nuñez (accents + apostrophe), ACTIVE
--   NWH-M000200  INACTIVE          NWH-M000033  SUSPENDED          NWH-M000047  PENDING
--   250 members; each of 25 last names exactly 10 times ("Garcia" -> 10 rows); NWH-P006 inactive plan.
SET ROLE northwind_app;

CREATE FUNCTION nwh_reset_seed() RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    first_names text[] := ARRAY[
        'Ava', 'Liam', 'Olivia', 'Noah', 'Emma', 'Mateo', 'Sophia', 'Elijah', 'Isabella', 'Lucas',
        'Mia', 'Kai', 'Amara', 'Ethan', 'Priya', 'Omar', 'Hana', 'Diego', 'Zoe', 'Wei',
        'Fatima', 'Jonah', 'Leila', 'Arjun', 'Nora', 'Malik', 'Ines', 'Theo', 'Yuki', 'Grace'];
    last_names text[] := ARRAY[
        'Thompson', 'Garcia', 'Chen', 'Patel', 'Okafor', 'Nguyen', 'Rossi', 'Kim', 'Johnson', 'Silva',
        'Novak', 'Haddad', 'Murphy', 'Tanaka', 'Lopez', 'Schmidt', 'Adeyemi', 'Kowalski', 'Martin', 'Singh',
        'Dubois', 'Larsen', 'Moreno', 'Walsh', 'Ibrahim'];
    states text[] := ARRAY['GA', 'TX', 'NY', 'CA', 'IL', 'WA', 'FL', 'OH'];
    cities text[] := ARRAY[
        'Atlanta', 'Austin', 'Albany', 'Sacramento', 'Springfield', 'Olympia', 'Tallahassee', 'Columbus'];
    area_codes text[] := ARRAY['404', '512', '518', '916', '217', '360', '850', '614'];
    streets text[] := ARRAY[
        'Maple Ave', 'Oak St', 'Cedar Ln', 'Elm Dr', 'Birch Rd', 'Willow Way', 'Pine Ct', 'Aspen Blvd'];
    providers text[] := ARRAY[
        'Northwind Family Clinic', 'Lakeside Imaging Center', 'Riverbend Pediatrics', 'Summit Orthopedics',
        'Harbor Urgent Care', 'Meadow Pharmacy', 'Crescent Dental Group', 'Northwind Health Lab'];
    diagnoses text[] := ARRAY['Z00.00', 'J06.9', 'I10', 'E11.9', 'M54.50', 'K21.9', 'R51.9', 'S93.401A'];
    claim_statuses text[] := ARRAY['SUBMITTED', 'IN_REVIEW', 'APPROVED', 'DENIED', 'PAID'];
BEGIN
    TRUNCATE claims, members, plans, app_users, api_clients;

    INSERT INTO plans (plan_code, name, tier, monthly_premium, deductible, active, description) VALUES
        ('NWH-P001', 'Bronze Basic',     'BRONZE',   189.00, 6500.00, true,  'Low premium, high deductible coverage for essential care.'),
        ('NWH-P002', 'Silver Standard',  'SILVER',   312.50, 3000.00, true,  'Balanced premium and deductible with preventive care included.'),
        ('NWH-P003', 'Gold Plus',        'GOLD',     455.25, 1250.00, true,  'Lower out-of-pocket costs and a wide provider network.'),
        ('NWH-P004', 'Platinum Premier', 'PLATINUM', 610.00,  250.00, true,  'Highest coverage with the lowest deductible.'),
        ('NWH-P005', 'Silver HSA',       'SILVER',   275.75, 3500.00, true,  'Health savings account eligible silver plan.'),
        ('NWH-P006', 'Legacy Bronze',    'BRONZE',   165.00, 7000.00, false, 'Closed to new enrollment; existing members only.');

    INSERT INTO members (
        member_id, first_name, last_name, date_of_birth, ssn, email, phone,
        address_line, city, state, postal_code, status, plan_code, enrolled_on)
    SELECT
        'NWH-M' || lpad(i::text, 6, '0'),
        first_names[1 + (i * 7) % 30],
        last_names[1 + (i * 11) % 25],
        date '1938-01-01' + (i * 7919) % 27000,
        '9' || lpad((i % 100)::text, 2, '0') || '-' || lpad(((i * 13) % 100)::text, 2, '0')
            || '-' || lpad(((i * 7919) % 10000)::text, 4, '0'),
        lower(first_names[1 + (i * 7) % 30] || '.' || last_names[1 + (i * 11) % 25])
            || '.' || i || '@members.northwind.example',
        area_codes[1 + i % 8] || '-555-01' || lpad((i % 100)::text, 2, '0'),
        ((i * 37) % 9000 + 100) || ' ' || streets[1 + (i * 3) % 8],
        cities[1 + i % 8],
        states[1 + i % 8],
        lpad(((i * 97) % 90000 + 10000)::text, 5, '0'),
        CASE WHEN i % 20 = 0 THEN 'INACTIVE'
             WHEN i % 33 = 0 THEN 'SUSPENDED'
             WHEN i % 47 = 0 THEN 'PENDING'
             ELSE 'ACTIVE' END,
        CASE WHEN i % 50 = 7 THEN 'NWH-P006' ELSE 'NWH-P00' || (1 + i % 5) END,
        date '2015-01-01' + (i * 389) % 4000
    FROM generate_series(1, 250) AS i;

    -- Well-known anchors.
    UPDATE members SET first_name = 'Ava', last_name = 'Thompson', date_of_birth = date '1985-04-12',
        email = 'ava.thompson@members.northwind.example', plan_code = 'NWH-P003', status = 'ACTIVE'
        WHERE member_id = 'NWH-M000123';
    UPDATE members SET first_name = 'Seán', last_name = 'O''Brien-Nuñez',
        email = 'sean.obrien-nunez@members.northwind.example', status = 'ACTIVE'
        WHERE member_id = 'NWH-M000150';

    INSERT INTO claims (
        claim_id, member_id, external_ref, service_date, submitted_at,
        provider_name, diagnosis_code, amount, status)
    SELECT
        'NWH-C' || lpad(row_number() OVER (ORDER BY i, j)::text, 7, '0'),
        'NWH-M' || lpad(i::text, 6, '0'),
        'EXT-NWH-M' || lpad(i::text, 6, '0') || '-' || j,
        date '2026-01-05' + (i * 31 + j * 17) % 200,
        (date '2026-01-08' + (i * 31 + j * 17) % 200) + time '09:30',
        providers[1 + (i + j * 3) % 8],
        diagnoses[1 + (i * 5 + j) % 8],
        25 + ((i * 7907 + j * 131) % 250000) / 100.0,
        claim_statuses[1 + (i + j) % 5]
    FROM generate_series(1, 250) AS i
    CROSS JOIN LATERAL generate_series(1, CASE WHEN i = 123 THEN 5 ELSE i % 4 END) AS j;

    PERFORM setval('claim_seq', (SELECT count(*) FROM claims));

    INSERT INTO app_users (username, display_name, role, password_hash, locked) VALUES
        ('admin',    'Alex Admin',     'ADMIN',    crypt('pw-Northwind-admin',    gen_salt('bf', 4)), false),
        ('examiner', 'Erin Examiner',  'EXAMINER', crypt('pw-Northwind-examiner', gen_salt('bf', 4)), false),
        ('viewer',   'Val Viewer',     'VIEWER',   crypt('pw-Northwind-viewer',   gen_salt('bf', 4)), false),
        ('locked',   'Lee Locked',     'VIEWER',   crypt('pw-Northwind-locked',   gen_salt('bf', 4)), true);

    INSERT INTO api_clients (client_id, role, secret_hash) VALUES
        ('nwh-batch',    'EXAMINER', crypt('cs-Northwind-batch',    gen_salt('bf', 4))),
        ('nwh-reporter', 'VIEWER',   crypt('cs-Northwind-reporter', gen_salt('bf', 4)));
END
$$;

SELECT nwh_reset_seed();

RESET ROLE;
