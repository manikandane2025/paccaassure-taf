-- Northwind Health sandbox schema (database: northwind, owner: northwind_app).
-- Fictitious company, synthetic data only. Runs once, on an empty data volume.
SET ROLE northwind_app;

CREATE TABLE plans (
    plan_code        varchar(8)    PRIMARY KEY,               -- NWH-P001
    name             varchar(60)   NOT NULL UNIQUE,
    tier             varchar(10)   NOT NULL CHECK (tier IN ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM')),
    monthly_premium  numeric(8, 2) NOT NULL CHECK (monthly_premium > 0),
    deductible       numeric(8, 2) NOT NULL CHECK (deductible >= 0),
    active           boolean       NOT NULL DEFAULT true,
    description      text          NOT NULL
);

CREATE TABLE members (
    member_id      varchar(11)  PRIMARY KEY,                  -- NWH-M000123
    first_name     varchar(40)  NOT NULL,
    last_name      varchar(40)  NOT NULL,
    date_of_birth  date         NOT NULL,
    ssn            char(11)     NOT NULL CHECK (ssn ~ '^9[0-9]{2}-[0-9]{2}-[0-9]{4}$'),  -- 9xx: never issued
    email          varchar(120) NOT NULL,
    phone          varchar(12)  NOT NULL,                     -- 555-01xx-style fictional numbers
    address_line   varchar(80)  NOT NULL,
    city           varchar(40)  NOT NULL,
    state          char(2)      NOT NULL,
    postal_code    char(5)      NOT NULL,
    status         varchar(10)  NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING')),
    plan_code      varchar(8)   NOT NULL REFERENCES plans (plan_code),
    enrolled_on    date         NOT NULL,
    version        integer      NOT NULL DEFAULT 1,           -- optimistic concurrency (API: 409 on stale)
    updated_at     timestamptz  NOT NULL DEFAULT timestamptz '2026-01-01 00:00:00+00'
);
CREATE INDEX members_last_name_idx ON members (lower(last_name));
CREATE INDEX members_status_idx ON members (status);

CREATE SEQUENCE claim_seq;

CREATE TABLE claims (
    claim_id        varchar(12)    PRIMARY KEY
                                   DEFAULT 'NWH-C' || lpad(nextval('claim_seq')::text, 7, '0'),
    member_id       varchar(11)    NOT NULL REFERENCES members (member_id),
    external_ref    varchar(40)    NOT NULL UNIQUE,           -- submitter's id; a duplicate is a 409
    service_date    date           NOT NULL,
    submitted_at    timestamptz    NOT NULL,
    provider_name   varchar(80)    NOT NULL,
    diagnosis_code  varchar(8)     NOT NULL,
    amount          numeric(10, 2) NOT NULL CHECK (amount > 0),
    status          varchar(10)    NOT NULL
                                   CHECK (status IN ('SUBMITTED', 'IN_REVIEW', 'APPROVED', 'DENIED', 'PAID')),
    notes           text           NOT NULL DEFAULT ''
);
ALTER SEQUENCE claim_seq OWNED BY claims.claim_id;
CREATE INDEX claims_member_idx ON claims (member_id);

-- Web/API sign-in. Passwords are bcrypt hashes (pgcrypto); verified in SQL by the API.
CREATE TABLE app_users (
    username       varchar(40)  PRIMARY KEY,
    display_name   varchar(60)  NOT NULL,
    role           varchar(10)  NOT NULL CHECK (role IN ('ADMIN', 'EXAMINER', 'VIEWER')),
    password_hash  text         NOT NULL,
    locked         boolean      NOT NULL DEFAULT false
);

-- OAuth2-style client_credentials for machine-to-machine API tests.
CREATE TABLE api_clients (
    client_id      varchar(40)  PRIMARY KEY,
    role           varchar(10)  NOT NULL CHECK (role IN ('ADMIN', 'EXAMINER', 'VIEWER')),
    secret_hash    text         NOT NULL
);

-- Read-only role: app data, never credentials.
GRANT SELECT ON plans, members, claims TO northwind_ro;

RESET ROLE;
