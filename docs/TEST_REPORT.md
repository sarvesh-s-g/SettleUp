# SettleUp — Test Report

**Environment:** Windows 11, Python 3.14.7, PostgreSQL 16.2 (local test database
`settleup_test`, rebuilt from the Alembic migration at the start of every run), Node.js 24.21,
Vitest 3.2.7.

**Commands:** `pytest -v` in `backend/`, `npm test -- --reporter=verbose` in `frontend/`.

**Result of the final recorded runs (20 Nov 2026):**

| Suite | Tests | Passed | Failed | Raw log |
|---|---:|---:|---:|---|
| Backend (pytest) | 97 | 97 | 0 | [`test-results/backend-pytest.txt`](test-results/backend-pytest.txt) |
| Frontend (Vitest) | 13 | 13 | 0 | [`test-results/frontend-vitest.txt`](test-results/frontend-vitest.txt) |

"Actual result" below means the assertions listed under *Expected* were executed and held.
Only tests that were actually executed are listed.

## Backend — authentication (`tests/test_auth.py`)

| # | Test case | Expected | Actual | Status |
|---|---|---|---|---|
| 1 | Register success | 201; email lower-cased; no password or hash in response | As expected | PASS |
| 2 | Password stored hashed | DB value ≠ password, starts with `$2b$` (bcrypt) | As expected | PASS |
| 3 | Duplicate email (different case) | 409 | As expected | PASS |
| 4 | Invalid email / short password / blank name | 422 each; response does not echo the password; error `loc` = `["body","password"]` | As expected | PASS |
| 5 | Login success + `/auth/me` | 200 with the same user | As expected | PASS |
| 6 | Incorrect password | 401 "Incorrect email or password" | As expected | PASS |
| 7 | Unknown email | 401 with the same message | As expected | PASS |
| 8 | No token on protected routes | 401 for `/auth/me`, `/groups`, `/dashboard` | As expected | PASS |
| 9 | Malformed / tampered token | 401 | As expected | PASS |
| 10 | Expired token | 401 | As expected | PASS |

## Backend — groups and members (`tests/test_groups.py`)

| # | Test case | Expected | Actual | Status |
|---|---|---|---|---|
| 11 | Create group | 201; creator is the only member, role admin | As expected | PASS |
| 12 | Blank group name | 422 | As expected | PASS |
| 13 | List groups shows only my groups | Outsider's group not listed; member_count 4; role member | As expected | PASS |
| 14 | Add members + list members | Members in join order; first is admin | As expected | PASS |
| 15 | Duplicate membership (incl. adding yourself) | 409 | As expected | PASS |
| 16 | Add unregistered email | 404 | As expected | PASS |
| 17 | Non-admin adds member | 403 | As expected | PASS |
| 18 | Non-member views group / members / unknown id | 404 in all three cases | As expected | PASS |
| 19 | Member leaves when settled | 204; afterwards the group is 404 for them | As expected | PASS |
| 20 | Remove member with a balance | 400 | As expected | PASS |
| 21 | Non-admin removes another member | 403 | As expected | PASS |
| 22 | Only admin leaves | Earliest remaining member becomes admin | As expected | PASS |
| 23 | Last member leaves | 400 | As expected | PASS |

## Backend — expenses (`tests/test_expenses.py`)

| # | Test case | Expected | Actual | Status |
|---|---|---|---|---|
| 24 | Equal split ₹1,200 / 4 | 201; four shares of 30000 | As expected | PASS |
| 25 | Equal split with remainder ₹100 / 3 | Shares 3333, 3333, 3334; sum 10000 | As expected | PASS |
| 26 | Custom split 400/300/200/100 | 201; shares stored exactly | As expected | PASS |
| 27 | Custom split total mismatch | 422 mentioning "add up" | As expected | PASS |
| 28 | Zero and negative amounts | 422 | As expected | PASS |
| 29 | Fractional paise (100.5) | 422 | As expected | PASS |
| 30 | Non-member payer / participant | 400 each | As expected | PASS |
| 31 | Duplicate participants | 422 | As expected | PASS |
| 32 | Non-member create / list / read / delete | 404 for each | As expected | PASS |
| 33 | Edit amount + participants | 200; 3 new splits of 30000; old split rows removed in DB | As expected | PASS |
| 34 | Edit notes/category only | 200; 4 splits unchanged | As expected | PASS |
| 35 | Edit amount without split_type | 422 | As expected | PASS |
| 36 | Only payer or admin can edit/delete | Other member 403; payer 200; admin 204 | As expected | PASS |
| 37 | Delete expense | 204; then 404; no split rows remain | As expected | PASS |
| 38 | Filters and pagination | Newest first; category, date range, member filters; page 2 of size 2; invalid category 422 | As expected | PASS |
| 39 | DB CHECK constraint (raw SQL, negative amount) | PostgreSQL raises IntegrityError | As expected | PASS |

## Backend — balances and settlements (`tests/test_balances_settlements.py`)

| # | Test case | Expected | Actual | Status |
|---|---|---|---|---|
| 40 | Balance formula (problem-statement data) | S +45000, R +5000, K −15000, A −35000; sum 0 | As expected | PASS |
| 41 | Balance breakdown fields | Sarvesh paid 120000, share 75000, net 45000 | As expected | PASS |
| 42 | Zero-balance group | All 0; no suggestions | As expected | PASS |
| 43 | Suggested settlements | Aman→Sarvesh 35000, Kiran→Sarvesh 10000, Kiran→Rahul 5000 | As expected | PASS |
| 44 | Record settlements | Balances update; applying all suggestions → all 0; history has 3 rows | As expected | PASS |
| 45 | Partial settlement | Aman −35000 → −25000 | As expected | PASS |
| 46 | Invalid settlements | Same person 422; zero/negative 422; above debt 400 "Maximum allowed is Rs 350.00"; above receiver credit 400; creditor paying 400; debtor receiving 400; outsider 400; nothing stored | As expected | PASS |
| 47 | Member records a settlement between two others | 403 | As expected | PASS |
| 48 | Non-member reads balances / settlements / suggestions | 404 | As expected | PASS |
| 49 | Multiple group isolation | Trip expense does not affect Room 204; non-member 404 | As expected | PASS |
| 50 | Rounding with odd amounts | Balances sum to 0; all suggested amounts > 0; suggestions total = total debt | As expected | PASS |
| 51 | Edit and delete change balances | Recomputed correctly; all 0 after delete | As expected | PASS |

## Backend — dashboard (`tests/test_dashboard.py`)

| # | Test case | Expected | Actual | Status |
|---|---|---|---|---|
| 52 | New user dashboard | 0 groups, 0 spending, 6 months of zeros | As expected | PASS |
| 53 | Dashboard totals | Spending 160000, paid 120000, share 30000, net 90000; category totals; current month row; my share 0 where not involved; suggestions only involve me and total 90000 | As expected | PASS |

## Backend — settlement algorithm, unit tests (`tests/test_settlement_algorithm.py`)

| # | Test case | Expected | Actual | Status |
|---|---|---|---|---|
| 54 | Problem-statement example | Exact 3-payment plan; all balances zero | As expected | PASS |
| 55 | Empty group | `[]` | As expected | PASS |
| 56 | Everyone settled | `[]` | As expected | PASS |
| 57 | One debtor, one creditor | One payment | As expected | PASS |
| 58 | One creditor, many debtors | Each debtor pays the creditor | As expected | PASS |
| 59 | One debtor, many creditors | Pays largest creditor first | As expected | PASS |
| 60 | Odd paise | Exact settlement, all amounts > 0 | As expected | PASS |
| 61 | Unbalanced input | ValueError | As expected | PASS |
| 62 | Deterministic output | Same plan regardless of dict order | As expected | PASS |
| 63–87 | 25 random groups (seeds 0–24, 2–12 people) | All settle; amounts > 0; no self-payment; ≤ n−1 payments; total = debt | As expected | PASS ×25 |
| 88 | Debtors only pay, creditors only receive | Holds | As expected | PASS |
| 89 | Small case where greedy is optimal | Valid plan; brute-force minimum is 3 | As expected | PASS |
| 90 | Known case where greedy is not minimal | Greedy 5 payments; brute-force minimum 4 | As expected | PASS |

## Backend — split service, unit tests (`tests/test_split_service.py`)

| # | Test case | Expected | Actual | Status |
|---|---|---|---|---|
| 91 | Even split | 4 × 30000 | As expected | PASS |
| 92 | Remainder to lowest ids | {1: 334, 2: 333, 3: 333} | As expected | PASS |
| 93 | Shares always add up (many amounts × 1–8 people) | Sum = amount; max − min ≤ 1 | As expected | PASS |
| 94 | Single participant | Pays everything | As expected | PASS |
| 95 | No participants | ValueError | As expected | PASS |
| 96 | Custom shares sum check | Valid accepted; mismatch ValueError | As expected | PASS |
| 97 | Custom duplicates / zero share | ValueError | As expected | PASS |

## Frontend (`src/test/*.test.js[x]`)

| # | Test case | Expected | Actual | Status |
|---|---|---|---|---|
| F1 | `rupeesToPaise` conversions | "125.5" → 12550, "1,200.99" → 120099, "0.29" → 29 | As expected | PASS |
| F2 | `rupeesToPaise` invalid input | null for "", "abc", "12.345", "-5", "1e3", null | As expected | PASS |
| F3 | `formatPaise` Indian grouping | "₹1,23,456.78", "-₹350.00", "+₹450.00" | As expected | PASS |
| F4 | Round trip paise ↔ input | 12550 → "125.50" → 12550 | As expected | PASS |
| F5 | Equal split preview matches backend | {1: 334, 2: 333, 3: 333} | As expected | PASS |
| F6 | Error message: string detail | Returned as is | As expected | PASS |
| F7 | Error message: validation list | "amount_paise: Input should be greater than 0" | As expected | PASS |
| F8 | Error message: network failure | "Cannot reach the server…" | As expected | PASS |
| F9 | ProtectedRoute | Anonymous user redirected to login | As expected | PASS |
| F10 | Login failure | Server message shown in an alert | As expected | PASS |
| F11 | Login success | Token stored; navigates to dashboard | As expected | PASS |
| F12 | ExpenseForm equal split | Payload has amount_paise 120000 and 4 participants; preview shows ₹300.00 ×4 | As expected | PASS |
| F13 | ExpenseForm custom mismatch | "₹300.00 left to assign"; submit blocked with message | As expected | PASS |

## Manual end-to-end verification

Performed in a browser against the running backend (port 8000) and frontend (port 5173) with
seed data: login, dashboard (stat cards, charts, recent expenses, suggestions), groups list,
group expenses with filters, add expense with live equal-split preview and remainder case
(₹1,000 / 3 → ₹333.34 + ₹333.33 + ₹333.33), expense details, settle-up with an over-payment
rejected ("Maximum allowed is Rs 2520.88") and the exact amount accepted, members page, and a
mobile-width layout. The API walkthrough in Chapter 21 of the technical guide was also run
against the live server.

## Not covered by automated tests

* Concurrent settlement requests (row-lock behaviour relies on PostgreSQL semantics; no
  multi-connection test).
* Concurrent edits of the same expense.
* Full browser end-to-end automation (pages were verified manually and by screenshots).
