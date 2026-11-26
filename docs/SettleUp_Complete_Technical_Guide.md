---
title: "SettleUp — Complete Technical Guide"
subtitle: "Group Expense Management and Settlement Platform"
version: "1.0"
date: "20 November 2026"
---

# How to Read This Guide

This guide explains the SettleUp application **exactly as it is implemented** in the
repository. Every code listing is copied from the source files, every table and column exists
in the Alembic migration, and every test result quoted was produced by an actual test run.

* **Chapters 1–3** describe what was built and why.
* **Chapters 4–6** cover the Python, FastAPI and REST concepts the code uses.
* **Chapters 7–11** are the database core: PostgreSQL fundamentals, the schema, the ER
  diagram, SQLAlchemy and the real queries.
* **Chapters 12–16** trace the important workflows: authentication, expense creation,
  balance calculation, settlement optimisation and transactions.
* **Chapters 17–21** are reference and practical material: the full API, the frontend
  integration, testing, running the project and a complete walkthrough.
* **Chapter 22** is an interview question bank (250 questions).
* **Chapters 23–24** list limitations, future scope and a codebase map.

Conventions used throughout:

| Convention | Meaning |
|---|---|
| `amount_paise` | Money is always an integer number of paise. ₹1 = 100 paise, so ₹1,200.00 = `120000`. |
| `file.py:function()` | A function in the backend or frontend source. |
| **Implemented** | A feature that exists in the code and is tested. |
| **Future scope** | An idea that is *not* implemented. These only appear in Chapter 23 and are labelled. |

Software versions used to build and verify the project:

| Component | Version |
|---|---|
| Python | 3.14 (code is compatible with 3.11+) |
| FastAPI / Starlette | 0.165.0 / 1.10.0 |
| Pydantic | 2.14.4 |
| SQLAlchemy | 2.1.9 |
| psycopg (PostgreSQL driver) | 3.3.9 |
| Alembic | 1.20.1 |
| PyJWT / bcrypt | 2.15.1 / 5.0.0 |
| PostgreSQL | 16.2 |
| React / React Router | 19.3.1 / 7.18.6 |
| Vite / Tailwind CSS | 6.4.6 / 4.3.5 |
| Axios / Recharts | 1.21.1 / 3.11.0 |
| Pytest / Vitest | 9.2.0 / 3.2.7 |

# Chapter 1 — Project Overview

## 1.1 What is SettleUp?

SettleUp is a web application that lets a group of people — roommates, friends on a trip,
a project team — record shared expenses, see who owes whom, and settle debts with as few
repayments as possible.

A typical use: four roommates in *Room 204* share rent, groceries and electricity. Whoever pays
a bill enters it once. SettleUp splits it between the people involved, keeps a running net
balance for everyone, and when they want to settle up it suggests a short list of payments
such as *"Aman pays Sarvesh ₹350"*. When the payment happens (in cash or by UPI, outside the
app), someone records it and the balances update.

## 1.2 Problem statement

Shared expenses are usually tracked in chat messages, notebooks or memory. This breaks down
quickly:

* People forget who paid for what.
* People forget how much they owe, and to whom.
* Some expenses involve only some members (three of four people went for dinner).
* Different people pay different bills, so debts point in many directions.
* Working out the final "who pays whom" by hand is error-prone.
* Repayments are forgotten, so old debts are counted twice or not at all.

## 1.3 Motivation

The problem is small enough for a three-person student team to solve completely, yet it
exercises every layer of a real web application: authentication, authorisation, relational
data modelling, transactional writes, aggregate queries, an algorithm with a clear
correctness argument, and a usable interface. Money adds a useful constraint — the numbers
must be *exactly* right — which forces careful decisions (integer paise, database
constraints, atomic writes).

## 1.4 Target users

* Students sharing hostel rooms or flats.
* Friends travelling together.
* Small informal groups (clubs, project teams) that pool money.

The application is **not** aimed at businesses, does not handle real payments, and does not
need to scale to millions of users.

## 1.5 Main objectives

1. Let users register and log in securely.
2. Let users create groups and add other registered users.
3. Record shared expenses with equal or custom splits, accurate to the paisa.
4. Calculate each member's net balance from the stored records.
5. Suggest a small set of repayments that settles the group.
6. Record repayments and show the history.
7. Give each user a dashboard of their spending and balances.

## 1.6 Features (implemented)

| # | Feature | Where |
|---|---|---|
| 1 | Registration, login with JWT, current-user endpoint, logout | `routers/auth.py`, `AuthContext.jsx` |
| 2 | Create group; creator becomes admin | `routers/groups.py:create_group` |
| 3 | List only my groups, with my balance per group | `routers/groups.py:list_my_groups` |
| 4 | Add members by email (admin only), list members | `routers/groups.py` |
| 5 | Remove a member or leave (balance must be zero) | `routers/groups.py:remove_member` |
| 6 | Create, view, edit, delete expenses | `routers/expenses.py` |
| 7 | Equal split with deterministic paise remainder | `services/split_service.py:split_equally` |
| 8 | Custom split that must add up exactly | `schemas/expense.py`, `split_service.py:custom_shares` |
| 9 | Filter expenses by category, member, date range; pagination | `routers/expenses.py:list_expenses` |
| 10 | Net balance per member | `services/balance_service.py` |
| 11 | Greedy settlement suggestions | `services/settlement_service.py` |
| 12 | Record repayments with validation and row locking | `routers/settlements.py:record_settlement` |
| 13 | Settlement history | `routers/settlements.py:list_settlements` |
| 14 | Dashboard (totals, charts, recent expenses, suggestions) | `routers/dashboard.py`, `DashboardPage.jsx` |
| 15 | Development seed data | `backend/scripts/seed.py` |

## 1.7 Scope

In scope: everything in the table above, a responsive React interface with 14 screens,
Swagger documentation, automated backend and frontend tests, and Alembic migrations.

Out of scope (deliberately): real payment integration, email invitations or notifications,
OAuth/social login, refresh tokens, percentage splits, multi-currency support, file uploads,
and production deployment.

## 1.8 Limitations (summary)

Settlements are records only; members must already be registered to be added; JWTs cannot
be revoked before they expire; the greedy algorithm is not guaranteed to find the absolute
minimum number of payments; and the app has not been deployed or security-audited. Chapter 23
discusses each limitation.

## 1.9 Real-world use case

> *Room 204* has four members: Sarvesh, Rahul, Kiran and Aman. Sarvesh buys groceries for
> ₹1,200 for everyone. Rahul pays the ₹1,000 electricity bill, which they split by usage
> (₹400/₹300/₹200/₹100). Aman buys ₹100 of snacks for the other three.
>
> SettleUp computes: Sarvesh **+₹466.66**, Rahul **+₹366.67**, Kiran **−₹533.33**,
> Aman **−₹300.00**. It suggests three payments — Kiran → Sarvesh ₹466.66, Kiran → Rahul
> ₹66.67, Aman → Rahul ₹300.00. Aman pays Rahul and records it; Aman's balance becomes ₹0.

These are the real numbers produced by the running application; Chapter 21 shows every
request, response and database row for this scenario.

# Chapter 2 — Complete Application Architecture

## 2.1 The big picture

SettleUp is a classic **three-tier** web application:

```mermaid
flowchart LR
    subgraph Client["Presentation tier (browser)"]
      R["React single-page app<br/>React Router · Axios · Tailwind · Recharts"]
    end
    subgraph Server["Application tier (Python)"]
      F["FastAPI app<br/>routers · dependencies · services"]
      O["SQLAlchemy ORM<br/>models · sessions"]
    end
    subgraph Data["Data tier"]
      P[("PostgreSQL 16<br/>6 tables")]
    end
    R -- "JSON over HTTP<br/>Authorization: Bearer JWT" --> F
    F --> O
    O -- "SQL (psycopg 3)" --> P
```

* The **frontend** never touches the database. It only calls the REST API.
* The **backend** owns every rule: who can see what, how money is split, what a balance is.
* The **database** stores facts (expenses, splits, settlements) and enforces integrity rules
  (keys, uniqueness, checks) as a last line of defence.

## 2.2 Frontend architecture

```text
frontend/src/
  main.jsx            -> mounts <BrowserRouter><AuthProvider><App/></AuthProvider></BrowserRouter>
  App.jsx             -> all routes (public, protected, nested group routes)
  api/client.js       -> one Axios instance + token interceptors
  api/api.js          -> one function per backend endpoint
  context/AuthContext -> current user, token, login/register/logout
  components/         -> Layout, GroupLayout, ProtectedRoute, ExpenseForm, ui.jsx
  pages/              -> the 14 screens
  utils/money.js      -> rupees <-> paise conversion, formatting
  utils/format.js     -> dates, categories, error messages
```

Pages hold their own state with `useState` and fetch data in `useEffect`. Shared state is
limited to the logged-in user (React context) and the current group (passed to child routes
with `<Outlet context>`). There is no Redux — the app does not need it.

## 2.3 Backend architecture

```text
backend/app/
  main.py            -> creates FastAPI app, CORS, exception handlers, includes routers
  config.py          -> Settings (DATABASE_URL, JWT secret, CORS) from env/.env
  database.py        -> engine, SessionLocal, Base, get_db() dependency
  models/            -> SQLAlchemy classes = database tables
  schemas/           -> Pydantic classes = JSON request/response shapes
  routers/           -> HTTP endpoints, grouped by resource
  dependencies/auth  -> get_current_user, require_group_member, require_group_admin
  services/          -> pure business logic: splitting, balances, settlement plan
  utils/security.py  -> bcrypt hashing, JWT encode/decode
```

The layers have one job each:

| Layer | Responsibility | Knows about HTTP? | Knows about SQL? |
|---|---|---|---|
| Router | Parse request, check permissions, call services, build response | Yes | Through ORM |
| Dependency | Reusable pre-checks (authentication, DB session) | Yes | Through ORM |
| Schema | Validate input shape and simple rules; define output shape | No | No |
| Service | Business rules (split, balance, settlement) | No | Balance service queries via ORM |
| Model | Map Python classes to tables | No | Yes |

There is no separate "repository" or "manager" layer: for a project of this size the
SQLAlchemy session already is the data-access layer, and adding more layers would only add
indirection.

## 2.4 Database architecture

Six tables, all in third normal form (Chapter 7.19):

| Table | Stores | Key relationships |
|---|---|---|
| `users` | Accounts | — |
| `groups` | Expense groups | `created_by → users` |
| `group_members` | Who belongs to which group, and their role | `group_id → groups`, `user_id → users` |
| `expenses` | One row per bill | `group_id → groups`, `paid_by → users` |
| `expense_splits` | One row per participant of a bill | `expense_id → expenses`, `user_id → users` |
| `settlements` | Repayments between members | `group_id → groups`, `paid_by`, `paid_to → users` |

Balances are **not stored** — they are calculated from `expenses`, `expense_splits` and
`settlements` each time they are needed, so they can never drift out of sync.

## 2.5 How the frontend and backend communicate

* Transport: HTTP, JSON bodies, UTF-8.
* Base URL: `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).
* Authentication: after login the frontend stores the JWT in `localStorage` and the Axios
  request interceptor adds `Authorization: Bearer <token>` to every call.
* Cross-origin: the React dev server runs on port 5173 and the API on 8000, which are
  different *origins*, so the backend enables CORS for the configured frontend origins.
* Errors: FastAPI returns `{"detail": "..."}` (or a list of field errors for 422), which
  `utils/format.js:getErrorMessage()` turns into one readable sentence.

## 2.6 Complete request–response lifecycle

The following traces `GET /api/v1/groups/1/balances` from a click to the pixels on screen.

```mermaid
sequenceDiagram
    autonumber
    participant UI as BalancesPage (React)
    participant AX as Axios client
    participant FA as FastAPI
    participant DEP as Dependencies
    participant RT as settlements router
    participant SV as balance_service
    participant DB as PostgreSQL
    UI->>AX: settlementsApi.balances(1)
    AX->>AX: request interceptor adds Bearer token
    AX->>FA: GET /api/v1/groups/1/balances
    FA->>FA: CORS middleware, route matching, path param group_id=1 (int)
    FA->>DEP: get_db() opens Session
    FA->>DEP: get_current_user() decodes JWT, loads user
    DEP->>DB: SELECT ... FROM users WHERE id = :id
    FA->>RT: get_balances(group_id=1, db, current_user)
    RT->>DB: SELECT group_members WHERE group_id=1 AND user_id=:me
    RT->>SV: compute_group_balances(db, 1)
    SV->>DB: 4 GROUP BY queries + member ids + names
    SV-->>RT: list[BalanceRow]
    RT-->>FA: BalancesResponse (Pydantic)
    FA->>FA: response_model validation -> JSON
    FA->>DEP: get_db() finally: session.close()
    FA-->>AX: 200 OK + JSON
    AX-->>UI: response.data
    UI->>UI: setData() -> re-render bars and table
```

Where each concern lives:

| Step | Concern | File |
|---|---|---|
| 1–3 | Building the HTTP request, attaching the token | `frontend/src/api/client.js`, `api.js` |
| 4 | Routing, path parameter conversion | `backend/app/main.py`, `routers/settlements.py` |
| 5 | Database session per request | `backend/app/database.py:get_db` |
| 6–7 | Authentication | `backend/app/dependencies/auth.py:get_current_user` |
| 9 | Authorisation (membership) | `dependencies/auth.py:require_group_member` |
| 10–12 | Business logic + SQL | `services/balance_service.py` |
| 13–14 | Response validation and serialisation | `schemas/settlement.py:BalancesResponse` |
| 17–19 | Rendering | `frontend/src/pages/SettlementPages.jsx:BalancesPage` |

For a request with a body (e.g. creating an expense), one more step happens before the router
function runs: FastAPI parses the JSON into the Pydantic model `ExpenseCreate`, running all
field and model validators. If validation fails, the router never runs and the client gets
**422 Unprocessable Content**.

# Chapter 3 — Development Lifecycle

## 3.1 How the requirements were identified

The requirements came from the project brief and from walking through the roommate scenario
step by step: *who* does *what*, and *what can go wrong*. Each "what can go wrong" became a
validation rule or a test — for example "someone enters a custom split that doesn't add up"
became a Pydantic model validator and the test `test_invalid_custom_split_total_is_rejected`.

## 3.2 Functional requirements

| ID | Requirement |
|---|---|
| FR1 | Users can register with name, email and password; emails are unique (case-insensitive). |
| FR2 | Users can log in and receive a token; protected endpoints require it. |
| FR3 | Users can create groups; the creator is the admin. |
| FR4 | Admins can add registered users to a group by email; duplicates are rejected. |
| FR5 | Members can view group details, members, expenses, balances and settlements. |
| FR6 | Members can add expenses with equal or custom splits. |
| FR7 | The payer of an expense or a group admin can edit or delete it. |
| FR8 | Expense history supports filtering and pagination. |
| FR9 | The system shows each member's net balance. |
| FR10 | The system suggests repayments that settle the group. |
| FR11 | Members can record repayments that do not exceed the outstanding amounts. |
| FR12 | Each user sees a dashboard summarising their groups. |
| FR13 | A member can leave (or be removed) only when their balance is zero. |

## 3.3 Non-functional requirements

| ID | Requirement | How it is met |
|---|---|---|
| NFR1 | Monetary correctness | Integer paise everywhere; CHECK constraints; tests that totals sum to zero |
| NFR2 | Security appropriate to a student project | bcrypt, JWT, membership checks, no secrets in code, safe error messages |
| NFR3 | Data integrity | Foreign keys, unique and check constraints, transactions |
| NFR4 | Usability | Responsive layout, loading/empty/error states, live split preview |
| NFR5 | Maintainability | Small layered codebase, type hints, docstrings, pinned dependencies |
| NFR6 | Testability | Pure functions for algorithms; API tests against a real PostgreSQL test DB |
| NFR7 | Documented API | Automatic Swagger UI at `/docs` |

## 3.4 Technology selection and justification

| Choice | Why | Alternatives considered |
|---|---|---|
| React + Vite | Component model, huge ecosystem, fast dev server | Plain HTML/JS (too manual), Angular (heavier) |
| JavaScript (not TypeScript) | Required by the brief; lower learning curve for the team | TypeScript |
| Tailwind CSS | Consistent design tokens without writing many CSS files | Bootstrap, CSS modules |
| FastAPI | Type-hint based validation, automatic OpenAPI docs, dependency injection | Flask (more manual), Django (more than needed) |
| PostgreSQL | Relational data with strong integrity guarantees, CHECK constraints, row locking | MySQL (similar), MongoDB (no joins/foreign keys — poor fit) |
| SQLAlchemy 2 | Mature ORM, explicit sessions/transactions, typed models | Raw SQL (more boilerplate), Django ORM (needs Django) |
| Alembic | Versioned, reviewable schema migrations | `create_all()` at startup (no history, cannot alter tables) |
| PyJWT + bcrypt | Small, focused, well-known libraries | passlib (unmaintained with new bcrypt), python-jose |

## 3.5 Development phases

The project followed the eight phases from the brief. The actual order of work is recorded in
`docs/DEVELOPMENT_LOG.md`; in summary:

1. **Requirements and scope** — the tables above.
2. **Architecture and schema** — six tables, ER diagram, folder structure.
3. **Backend foundation** — config, database session, models, Alembic migration, auth.
4. **Core features** — groups, expenses, splitting, balances, settlement algorithm,
   settlement recording.
5. **Dashboard, filters, pagination, error handling.**
6. **Frontend** — layouts, 14 screens, API integration, responsive design.
7. **Testing and fixes** — 97 backend and 13 frontend tests; bugs found during manual
   testing were fixed (Chapter 19.8).
8. **Documentation** — README, this guide, test report, screenshots, repository preparation.

## 3.6 Team responsibility split

The code is organised so three people can work in parallel:

| Member | Area | Main files |
|---|---|---|
| Sarvesh (sarvesh-s-g) | Database design (schema, ER diagram, constraints, indexes, models, migrations) and backend: FastAPI, auth, APIs, balance and settlement logic, backend tests | `backend/app/`, `backend/alembic/`, `backend/tests/` |
| Sharanagouda (sharanagoudabiradar) | Frontend: React app, authentication, groups, expenses, dashboard, balances and settlement screens, API integration | `frontend/src/` |
| Gollal (MsGOLLAL) | Frontend and backend support: frontend test suite, development seed data, Docker PostgreSQL setup, dashboard API tests | `frontend/src/test/`, `backend/scripts/`, `docker-compose.yml`, `backend/tests/test_dashboard.py` |

The contract between frontend and backend is the API (Chapter 17). As long as the JSON shapes
in `schemas/` stay stable, both sides can change independently.

## 3.7 Testing and finalisation

Backend tests run against a real PostgreSQL database rebuilt from the Alembic migration, so
they exercise the real constraints. Frontend tests use Vitest with Testing Library. Finally
the whole application was run locally, every page was exercised in a browser, and the
screenshots in `docs/screenshots/` were captured from that run.

# Chapter 4 — Python Fundamentals Used in This Project

This chapter covers only the Python features that appear in the SettleUp backend, each with
an example from the real code.

## 4.1 Variables and data types

Python variables are names bound to objects; the type belongs to the object, not the name.
SettleUp uses a small set of types:

| Type | Example in SettleUp |
|---|---|
| `int` | `amount_paise = 120000`; database ids |
| `str` | names, emails, `"equal"`/`"custom"` |
| `bool` | `is_member` in a balance row |
| `None` | optional `notes` |
| `date`, `datetime` | `expense_date`, `created_at` (from the `datetime` module) |
| `list`, `dict`, `set`, `tuple` | participants, balances, member ids, settlement triples |

Python `int` has **arbitrary precision** — it never overflows — and integer arithmetic is
exact. That is why all money is an `int` of paise. A `float` such as `0.1 + 0.2` evaluates to
`0.30000000000000004`, which is unacceptable for money.

Constants are written in upper case by convention:

```python
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
MAX_AMOUNT_PAISE = 1_000_000_000   # underscores are just digit separators
```

## 4.2 Functions

A function packages logic behind a name and parameters. `split_equally` is a pure function: it
depends only on its arguments and has no side effects, which makes it easy to test.

```python
def split_equally(amount_paise: int, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        raise ValueError("At least one participant is required")
    if amount_paise <= 0:
        raise ValueError("Amount must be positive")

    ordered = sorted(user_ids)
    count = len(ordered)
    base_share, remainder = divmod(amount_paise, count)

    shares: dict[int, int] = {}
    for index, user_id in enumerate(ordered):
        shares[user_id] = base_share + (1 if index < remainder else 0)
    return shares
```

Concepts shown: parameters with type hints, guard clauses that raise early, the built-in
`divmod()` (quotient and remainder in one call), tuple unpacking (`a, b = ...`),
`enumerate()` to get an index while looping, and a conditional expression
`(1 if index < remainder else 0)`.

Keyword arguments and defaults are used widely, e.g. in the test helper
`add_expense(client, group_id, headers, **overrides)` where `**overrides` collects any extra
keyword arguments into a dictionary.

## 4.3 Classes and objects

A class is a blueprint; an object is an instance. Every ORM model is a class:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    ...
    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
```

`User(Base)` means **inheritance**: `User` inherits behaviour from SQLAlchemy's declarative
`Base`. `__repr__` is a *dunder* (double-underscore) method that controls how the object
prints in logs and the debugger.

The balance service uses a **dataclass**, which auto-generates `__init__` and `__repr__`, and
a **property**, which looks like an attribute but is computed:

```python
@dataclass
class BalanceRow:
    user_id: int
    name: str
    is_member: bool
    total_paid_paise: int = 0
    total_share_paise: int = 0
    settlements_paid_paise: int = 0
    settlements_received_paise: int = 0

    @property
    def net_balance_paise(self) -> int:
        return (self.total_paid_paise - self.total_share_paise
                + self.settlements_paid_paise - self.settlements_received_paise)
```

Because `net_balance_paise` is computed, it can never disagree with its four inputs.

## 4.4 Modules and imports

Each `.py` file is a module; a folder with `__init__.py` is a package. `app/models/__init__.py`
re-exports all models so other code can write `from app.models import User, Group` and so
that importing the package registers every table on `Base.metadata` (Alembic relies on this).

```python
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.expense import Expense, ExpenseSplit
from app.models.settlement import Settlement
```

Absolute imports (`from app.services.split_service import split_equally`) are used everywhere,
which keeps import paths unambiguous.

## 4.5 Exception handling

Errors are signalled with exceptions and handled with `try`/`except`/`finally`.

Raising — the router stops processing and FastAPI turns this into an HTTP response:

```python
if user is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No registered user has that email")
```

Catching a database error and translating it:

```python
db.add(user)
try:
    db.commit()
except IntegrityError:
    db.rollback()
    raise HTTPException(status.HTTP_409_CONFLICT, detail="Email is already registered")
```

Guaranteed cleanup with `finally` — the session is always closed, even after an error:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

Catching several exception types at once in `decode_access_token`:
`except (jwt.PyJWTError, ValueError, KeyError): return None`.

## 4.6 Type hints

Type hints document what a function expects and returns. Python does not enforce them at
runtime by itself, but **FastAPI and Pydantic read them** to validate and convert data, and
SQLAlchemy reads `Mapped[...]` to build columns.

```python
def get_membership(db: Session, group_id: int, user_id: int) -> GroupMember | None: ...
notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

`X | None` means "an `X` or `None`" (Python 3.10+ syntax). `list[int]` and `dict[int, int]`
describe container contents. `Literal["equal", "custom"]` restricts a string to exact values.

## 4.7 Lists, dictionaries, sets and comprehensions

* **List comprehension** — build the response list from ORM rows:

  ```python
  return [MemberOut(user_id=r.id, name=r.name, email=r.email, role=r.role, joined_at=r.joined_at)
          for r in rows]
  ```

* **Dict comprehension** — turn SQL result rows into a lookup table:

  ```python
  return {user_id: int(total) for user_id, total in db.execute(statement).all()}
  ```

* **Set operations** — find participants who are not members, and every user who appears in
  any record of a group:

  ```python
  outsiders = set(participant_ids) - members
  all_ids = member_ids | paid.keys() | owed.keys() | settled_out.keys() | settled_in.keys()
  ```

* **`dict.get(key, default)`** — a user with no payments has no key in `paid`, so
  `paid.get(user_id, 0)` supplies zero.

* **Generator expressions** inside `sum()`/`any()`:
  `sum(s.share_amount_paise for s in splits)`, `any(m.role == ROLE_ADMIN for m in others)`.

## 4.8 Decorators

A decorator wraps or registers a function. SettleUp uses:

| Decorator | Purpose |
|---|---|
| `@router.get(...)`, `@router.post(...)` | Register a function as an HTTP endpoint |
| `@app.exception_handler(IntegrityError)` | Register a global error handler |
| `@field_validator("email")`, `@model_validator(mode="after")` | Pydantic validation hooks |
| `@classmethod` | Required by Pydantic field validators |
| `@property` | Computed attribute (`net_balance_paise`, `changes_split`) |
| `@dataclass` | Auto-generate `__init__` for `BalanceRow` |
| `@lru_cache` | Build `Settings` once and reuse it (`config.py:get_settings`) |
| `@pytest.fixture`, `@pytest.mark.parametrize` | Test fixtures and data-driven tests |

## 4.9 Async and await

FastAPI supports both `async def` and plain `def` endpoints. **SettleUp uses plain `def`
endpoints throughout.** The reason is that the database layer (SQLAlchemy `Session` with the
psycopg driver in synchronous mode) is blocking. When an endpoint is a normal `def`,
FastAPI runs it in a worker thread pool, so a slow database call does not block the event
loop. Using `async def` with a blocking session would be a mistake, because the blocking call
would freeze the event loop for every other request.

An async version would require `AsyncSession`, an async driver and `await` on every query.
That is a valid design, but it adds complexity that a student-scale app does not need.
(Interview tip: be ready to explain this choice; it is a common question.)

## 4.10 Generators and `yield`

`get_db()` is a generator: code before `yield` runs before the endpoint, the yielded value is
injected into the endpoint, and code after `yield` (the `finally`) runs after the response
is produced. FastAPI drives this lifecycle automatically.

## 4.11 Dependency injection (the concept)

*Dependency injection* means a function receives the things it needs as parameters instead of
creating them itself. In SettleUp, endpoints declare what they need and FastAPI provides it:

```python
def list_members(group_id: int,
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)): ...
```

The endpoint never opens a database connection or parses a token itself. This keeps endpoints
short, makes the rules consistent, and lets tests swap dependencies if needed. Chapter 5.9
explains how FastAPI implements it.

# Chapter 5 — FastAPI in Detail

## 5.1 What FastAPI is

FastAPI is a Python web framework for building APIs. It sits on **Starlette** (the HTTP/ASGI
toolkit) and **Pydantic** (data validation). Its central idea is that ordinary Python type
hints declare the API: from `def get_group(group_id: int, ...)` FastAPI knows the path
parameter must be an integer, converts it, validates it, and documents it.

## 5.2 Why it was selected

* Validation and documentation come from one source of truth (type hints + Pydantic models).
* Swagger UI is generated automatically — useful for testing and for teammates.
* The dependency-injection system is a clean way to express authentication and authorisation.
* It is small enough for students to understand in full.

## 5.3 Application initialisation (`app/main.py`)

```python
API_PREFIX = "/api/v1"

app = FastAPI(
    title="SettleUp API",
    description="Group expense management and settlement platform. "
    "Log in via /auth/login, then click **Authorize** and paste the access_token.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,  # we send the JWT in a header, not in cookies
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
...
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(groups.router, prefix=API_PREFIX)
app.include_router(expenses.router, prefix=API_PREFIX)
app.include_router(settlements.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
```

Line by line:

1. `FastAPI(...)` creates the ASGI application; the title and description appear in Swagger.
2. `add_middleware(CORSMiddleware, ...)` wraps every request: it answers browser *preflight*
   `OPTIONS` requests and adds `Access-Control-Allow-Origin` headers for allowed origins.
3. `include_router(..., prefix="/api/v1")` mounts each router's paths under the versioned
   prefix, so `@router.post("/register")` in a router with `prefix="/auth"` becomes
   `POST /api/v1/auth/register`.

Notice what is **not** here: no `Base.metadata.create_all()`. Tables are created only by
Alembic migrations.

## 5.4 Routers

Routers group related endpoints. Each router file creates an `APIRouter` with a prefix and a
tag (the tag groups endpoints in Swagger):

```python
router = APIRouter(prefix="/groups", tags=["Groups"])

@router.get("/{group_id}/members", response_model=list[MemberOut])
def list_members(group_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    require_group_member(db, group_id, current_user)
    return _members_out(db, group_id)
```

The settlements router even puts a path parameter in its prefix:
`APIRouter(prefix="/groups/{group_id}", tags=["Balances & Settlements"])`, so every endpoint
in it receives `group_id`.

## 5.5 Path parameters

`{group_id}` in the path plus `group_id: int` in the function signature makes FastAPI extract
the value and convert it. `GET /api/v1/groups/abc` fails with 422 before the function runs.

## 5.6 Query parameters

Parameters that are not in the path and are simple types become query parameters. The expense
list declares them with `Query(...)` to add validation and documentation:

```python
def list_expenses(
    group_id: int,
    category: Category | None = Query(default=None),
    member_id: int | None = Query(default=None, description="Expenses this user paid for or shares in"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ...
```

`ge=1` means "greater than or equal to 1", `le=100` "less than or equal to 100". `Category`
is a `Literal`, so `?category=invalid` is rejected with 422. Dates are parsed from
`YYYY-MM-DD` strings automatically.

## 5.7 Request bodies and Pydantic schemas

A parameter whose type is a Pydantic model is read from the JSON body:

```python
@router.post("/groups/{group_id}/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(group_id: int, payload: ExpenseCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
```

`ExpenseCreate` declares the fields and constraints:

```python
class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200, examples=["Groceries"])
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE, examples=[120000])
    paid_by: int
    category: Category = "other"
    expense_date: date
    notes: str | None = Field(default=None, max_length=1000)
    split_type: SplitType
    participant_ids: list[int] | None = None
    splits: list[SplitIn] | None = None

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be blank")
        return value

    @model_validator(mode="after")
    def check_split(self):
        validate_split_definition(self.amount_paise, self.split_type, self.participant_ids, self.splits)
        return self
```

* `Field(gt=0)` rejects zero and negative amounts.
* `amount_paise: int` rejects `100.5` (Pydantic will not silently truncate a float with a
  fractional part) — tested by `test_float_amount_rejected`.
* `@field_validator` runs on one field; `@model_validator(mode="after")` runs after all fields
  are parsed and can check rules involving several fields, such as "custom shares must add
  up to the amount".

## 5.8 Response models

`response_model=ExpenseOut` tells FastAPI to validate and filter the returned data through
`ExpenseOut`. Two benefits: the Swagger docs show the exact response shape, and fields not in
the schema can never leak. `UserOut` has no `password_hash` field, so even if a router
returned the ORM `User` object directly (as `read_me` does), the hash would be dropped.

```python
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)   # read from ORM attributes
    id: int
    name: str
    email: EmailStr
    created_at: datetime
```

## 5.9 Dependency injection in FastAPI

`Depends(f)` tells FastAPI: "before calling this endpoint, call `f`, and pass its result in."
Dependencies can depend on other dependencies, forming a graph that FastAPI resolves per
request (and caches within that request, so `get_db` is called once even if two dependencies
need it).

```python
bearer_scheme = HTTPBearer(auto_error=False, description="Paste the access_token from /auth/login")

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status_code=401, detail="Could not validate credentials",
                                 headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
```

Resolution order for a protected endpoint: `bearer_scheme` (reads the header) → `get_db`
(opens a session) → `get_current_user` (uses both) → endpoint. Group checks such as
`require_group_member(db, group_id, user)` are plain functions called inside the endpoint,
because they need the `group_id` path parameter *and* return the membership row the endpoint
then uses (for example to check the role).

## 5.10 Middleware

Middleware wraps every request and response. SettleUp uses one: `CORSMiddleware`. It runs
before routing, so even an error response carries the correct CORS headers and the browser
can read the error message.

## 5.11 HTTP methods and status codes in SettleUp

| Method | Used for | Success code |
|---|---|---|
| GET | Read (groups, expenses, balances, dashboard) | 200 OK |
| POST | Create (register, group, member, expense, settlement), login | 201 Created (login: 200) |
| PATCH | Partial update of an expense | 200 OK |
| DELETE | Delete an expense, remove a member | 204 No Content |

Error codes used: 400 (business rule violated), 401 (not authenticated), 403 (authenticated
but not allowed), 404 (not found *or* not a member), 409 (conflict/duplicate), 422 (invalid
input), 500 (unexpected error, generic message).

## 5.12 Error handling

Three levels:

1. **`HTTPException`** raised in routers and dependencies for expected problems.
2. **Validation errors** (422), with a custom handler that returns only `loc`, `msg` and
   `type` — FastAPI's default would echo the submitted input, which for registration would
   include the password:

   ```python
   @app.exception_handler(RequestValidationError)
   def validation_error_handler(request: Request, exc: RequestValidationError):
       errors = [
           {"loc": list(err.get("loc", [])), "msg": err.get("msg", "Invalid value"), "type": err.get("type")}
           for err in exc.errors()
       ]
       return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": errors})
   ```

3. **Global handlers** for `IntegrityError` (→ 409, generic message, details only in the server
   log) and any other `Exception` (→ 500 "Internal server error"). Stack traces and SQL are
   never sent to the client.

## 5.13 Automatic Swagger documentation

FastAPI generates an OpenAPI 3 document at `/openapi.json` and two UIs: Swagger at `/docs`
and ReDoc at `/redoc`. Because `get_current_user` uses `HTTPBearer`, Swagger shows an
**Authorize** button: log in with `POST /api/v1/auth/login`, copy `access_token`, click
Authorize, paste it, and every "Try it out" call will send the header. The OpenAPI document
can also be imported into Postman (*Import → Link → http://localhost:8000/openapi.json*).

# Chapter 6 — REST API Fundamentals

## 6.1 What is an API?

An API (Application Programming Interface) is a contract that lets one program use another.
A *web* API exposes that contract over HTTP. SettleUp's frontend is one client of the API;
Swagger, Postman, curl and the pytest suite are others — they all use the same contract.

## 6.2 Client–server architecture

The **client** (browser running React) sends requests; the **server** (FastAPI) processes
them and returns responses. The server is the single source of truth and enforces all rules;
the client can never be trusted, because anyone can send HTTP requests without using the UI.
This is why SettleUp validates custom splits on the client (for quick feedback) **and** on
the server (for correctness).

## 6.3 REST principles applied

| Principle | In SettleUp |
|---|---|
| Resources identified by URLs | `/groups/1`, `/expenses/17`, `/groups/1/settlements` |
| Standard methods | GET reads, POST creates, PATCH updates, DELETE removes |
| Representations | JSON bodies |
| Stateless requests | Every request carries its own JWT; the server keeps no session |
| Hierarchy expresses ownership | Expenses are created under a group: `POST /groups/{id}/expenses` |
| Versioning | `/api/v1` prefix allows a future `/api/v2` without breaking clients |

Pragmatic choices: an expense is addressed as `/expenses/{id}` (not
`/groups/{gid}/expenses/{id}`) because its id is globally unique — the server looks up the
group from the expense and checks membership. Computed views such as `/balances` and
`/settlements/suggested` are read-only resources.

## 6.4 HTTP request and response

A request has a method, URL, headers and optional body:

```http
POST /api/v1/groups/1/expenses HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{"description": "Groceries", "amount_paise": 120000, "paid_by": 1,
 "category": "groceries", "expense_date": "2026-11-02",
 "split_type": "equal", "participant_ids": [1, 2, 3, 4]}
```

A response has a status line, headers and optional body:

```http
HTTP/1.1 201 Created
content-type: application/json

{"id": 17, "group_id": 1, "description": "Groceries", "amount_paise": 120000, ...}
```

## 6.5 GET, POST, PUT, PATCH and DELETE

* **GET** — read; *safe* (no changes) and *idempotent*.
* **POST** — create or perform an action; not idempotent (two POSTs create two expenses).
* **PUT** — replace a whole resource; idempotent. *SettleUp does not use PUT.*
* **PATCH** — change part of a resource. `PATCH /expenses/{id}` with `{"notes": "x"}`
  changes only the notes; fields not sent are untouched (the router checks
  `payload.model_fields_set` to know which fields were actually sent).
* **DELETE** — remove; idempotent in effect (a second DELETE returns 404 but the state is
  the same).

## 6.6 JSON

JSON is the data format of every request and response. JSON numbers have no integer/float
distinction and JavaScript stores them as 64-bit floats, which represent integers exactly up
to 2^53 − 1 ≈ 9 × 10^15. The largest allowed amount (₹1 crore = 10^9 paise) is far below that,
so paise survive the trip through JSON and JavaScript exactly.

## 6.7 Headers

| Header | Direction | Purpose |
|---|---|---|
| `Content-Type: application/json` | both | Body format |
| `Authorization: Bearer <jwt>` | request | Authentication |
| `WWW-Authenticate: Bearer` | response (401) | Tells the client which scheme to use |
| `Origin` / `Access-Control-Allow-Origin` | request / response | CORS |

## 6.8 Authentication headers

SettleUp uses the **Bearer** scheme: whoever bears (holds) a valid token is treated as its
owner. The header looks like `Authorization: Bearer eyJhbGciOiJIUzI1NiIs...`. Because
possession is enough, tokens must be kept secret, sent only over HTTPS in production, and
expire (here after `ACCESS_TOKEN_EXPIRE_MINUTES`, default 120).

## 6.9 Request validation and response validation

* **Request validation** — Pydantic checks types, ranges and custom rules before the endpoint
  runs (422 on failure). Business rules that need the database (is the payer a member? does
  the settlement exceed the debt?) are checked in the router (400/403/404).
* **Response validation** — `response_model` guarantees the output matches the documented
  schema and strips any extra fields.

## 6.10 HTTP status codes mapped to SettleUp

| Code | Meaning | Example |
|---|---|---|
| 200 | OK | `GET /groups/1/balances` |
| 201 | Created | `POST /groups/1/expenses` |
| 204 | No Content | `DELETE /expenses/17` |
| 400 | Bad Request (business rule) | Settlement larger than the debt |
| 401 | Unauthorized (no/invalid token) | `GET /groups` without a token |
| 403 | Forbidden (not allowed) | Non-admin tries to add a member |
| 404 | Not Found | Expense id that does not exist *or* that belongs to someone else's group |
| 409 | Conflict | Registering an email that already exists |
| 422 | Unprocessable Content (invalid input) | Custom shares that do not add up |
| 500 | Server error | Unexpected exception (generic message only) |

# Chapter 7 — PostgreSQL and Database Fundamentals

## 7.1 What is a relational database?

A relational database stores data in **tables** (relations). Each table has a fixed set of
**columns** (attributes) and any number of **rows** (tuples). Tables are linked by storing
the key of one row in another row. You ask questions with **SQL**, a declarative language:
you describe *what* you want and the database decides *how* to fetch it.

The relational model gives three things SettleUp relies on:

1. **Structure** — every expense has exactly the columns the schema defines.
2. **Integrity** — the database itself rejects data that breaks the rules (a split for a
   non-existent expense, a negative amount, a duplicate membership).
3. **Ad-hoc querying** — any question ("how much did Kiran spend on food in October?") can be
   answered by combining tables with joins and aggregates, without changing the code that
   stores the data.

## 7.2 Why PostgreSQL?

* **Strong integrity features**: foreign keys, unique constraints, CHECK constraints, and
  transactional DDL (a failed migration is rolled back completely).
* **Correct transactions** with MVCC (multi-version concurrency control) and row-level locks
  (`SELECT ... FOR UPDATE`), which SettleUp uses when recording settlements.
* **Rich SQL**: window functions, CTEs, `to_char`/`date_trunc` for date grouping, and good
  query planning.
* Open source, widely used in industry, excellent documentation.

**Why not MongoDB?** SettleUp's data is naturally relational: users ↔ groups is
many-to-many, expenses ↔ participants is many-to-many, and balances need joins and sums across
those relationships. A document database would either duplicate data (participants embedded in
expenses *and* expenses embedded in users) or reimplement joins in application code, and it
would not enforce "a split must reference an existing expense" for us.

## 7.3 Tables, rows and columns

```sql
SELECT id, name, email FROM users;
```

| id | name | email |
|---|---|---|
| 1 | Sarvesh | sarvesh@example.com |
| 2 | Rahul | rahul@example.com |

`users` is the table, `id`/`name`/`email` are columns, and each line is a row. Row order is
not guaranteed unless you write `ORDER BY`.

## 7.4 Data types used by SettleUp

| PostgreSQL type | Used for | Why |
|---|---|---|
| `SERIAL` (`INTEGER` + sequence) | All primary keys | Auto-incrementing 32-bit ids; enough for ~2.1 billion rows |
| `VARCHAR(n)` | name (100), email (255), description (200), role (20), category (30), split_type (10) | Bounded text; the limit documents and enforces the expected size |
| `TEXT` | `expenses.notes` | Unbounded optional free text |
| `BIGINT` | All `*_paise` columns | 64-bit integer: exact, up to 9.2 × 10^18 paise |
| `DATE` | `expense_date`, `settled_at` | A calendar day, no time zone needed |
| `TIMESTAMP WITH TIME ZONE` | `created_at`, `updated_at`, `joined_at` | An exact instant, stored in UTC |

**Why not `NUMERIC(12,2)` for money?** `NUMERIC` is also exact and would be a valid choice.
SettleUp uses integer paise because the same representation then works identically in
PostgreSQL (`BIGINT`), Python (`int`) and JavaScript (`number`, exact below 2^53), and all
arithmetic is plain integer arithmetic with no rounding modes to choose. `FLOAT`/`REAL`/
`DOUBLE PRECISION` are never acceptable for money because they are binary approximations.

## 7.5 Primary keys

A primary key uniquely identifies each row; it is implicitly `NOT NULL` and `UNIQUE`, and
PostgreSQL builds a unique B-tree index on it.

```sql
CREATE TABLE users (
    id SERIAL NOT NULL,
    ...
    PRIMARY KEY (id)
);
```

SettleUp uses **surrogate keys** (meaningless integers) rather than **natural keys** (like
email). If a user later changes their email, nothing that references them has to change.

## 7.6 Foreign keys

A foreign key says "this column's value must exist as a primary key in another table".

```sql
CREATE TABLE expenses (
    ...
    group_id INTEGER NOT NULL,
    paid_by  INTEGER NOT NULL,
    FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE,
    FOREIGN KEY(paid_by)  REFERENCES users  (id) ON DELETE RESTRICT
);
```

* Inserting an expense with `group_id = 999` fails if group 999 does not exist.
* `ON DELETE CASCADE`: deleting a group deletes its expenses automatically.
* `ON DELETE RESTRICT`: deleting a user who paid an expense is refused, because the
  financial history would otherwise become meaningless.

This guarantee is called **referential integrity**.

## 7.7 Unique constraints

```sql
UNIQUE (email)                                                   -- users
CONSTRAINT uq_group_members_group_user UNIQUE (group_id, user_id) -- group_members
CONSTRAINT uq_expense_splits_expense_user UNIQUE (expense_id, user_id) -- expense_splits
```

A **composite** unique constraint applies to the *combination*: user 2 may be in groups 1 and
3, but cannot appear twice in group 1. The application checks for duplicates first to return
a friendly message, but the constraint is what makes it *impossible* — even if two requests
race each other.

## 7.8 NOT NULL constraints

Every column except `expenses.notes` is `NOT NULL`. An expense without an amount or a payer
is meaningless, so the database refuses it rather than storing a half-record.

## 7.9 CHECK constraints

CHECK constraints enforce row-level rules:

```sql
CONSTRAINT ck_expenses_amount_positive CHECK (amount_paise > 0)
CONSTRAINT ck_expenses_split_type CHECK (split_type IN ('equal', 'custom'))
CONSTRAINT ck_expenses_category CHECK (category IN ('food', 'groceries', 'rent', 'utilities',
                                                    'transport', 'entertainment', 'shopping', 'other'))
CONSTRAINT ck_expense_splits_share_positive CHECK (share_amount_paise > 0)
CONSTRAINT ck_group_members_role CHECK (role IN ('admin', 'member'))
CONSTRAINT ck_settlements_amount_positive CHECK (amount_paise > 0)
CONSTRAINT ck_settlements_different_users CHECK (paid_by <> paid_to)
```

The test `test_database_check_constraint_blocks_bad_rows` bypasses the API and inserts a
negative amount with raw SQL; PostgreSQL rejects it. This is **defence in depth**: Pydantic
validates first, the router validates business rules, and the database guarantees the
invariant no matter which code path writes the data.

What a CHECK cannot do: compare rows. "The splits of an expense must add up to its amount"
involves many rows, so it is enforced in application code inside the same transaction
(Chapter 16).

## 7.10 Relationships

| Kind | Meaning | SettleUp example |
|---|---|---|
| One-to-one | Each A has at most one B and vice versa | *Not used.* (A `user_profiles` table split from `users` would be one.) |
| One-to-many | One A has many B; each B has one A | One group → many expenses; one expense → many splits; one user → many groups created |
| Many-to-many | Many A relate to many B | Users ↔ groups (via `group_members`); users ↔ expenses as participants (via `expense_splits`) |

A many-to-many relationship always needs a **junction table** whose rows pair one A with one
B. The junction table can also carry attributes of the pairing — `group_members.role` and
`joined_at`, `expense_splits.share_amount_paise`.

## 7.11 Indexes

An index is a separate data structure (by default a B-tree) that lets PostgreSQL find rows by
a column value without scanning the whole table — like the index at the back of a book.
Indexes speed up reads but cost disk space and slow down writes slightly, so only columns that
are actually searched, joined or sorted on are indexed.

SettleUp's indexes and the queries they serve:

| Index | Serves |
|---|---|
| PK indexes on every `id` | Lookups by id, joins on foreign keys pointing to them |
| `users (email)` (unique) | Login and "add member by email" |
| `uq_group_members_group_user (group_id, user_id)` | "Is user X in group Y?" (every permission check) and "members of group Y" (leading column) |
| `ix_group_members_user_id (user_id)` | "Which groups does user X belong to?" (group list, dashboard) |
| `ix_groups_created_by` | Foreign key lookups from users |
| `ix_expenses_group_id_expense_date (group_id, expense_date)` | Expense history of a group filtered/sorted by date; balance sums per group |
| `ix_expenses_paid_by` | Totals paid by a user; foreign key checks |
| `uq_expense_splits_expense_user (expense_id, user_id)` | Splits of an expense (leading column), and uniqueness |
| `ix_expense_splits_user_id` | A user's shares (dashboard, member filter) |
| `ix_settlements_group_id_settled_at (group_id, settled_at)` | Settlement history and sums per group |

**How a composite index works.** A B-tree on `(group_id, expense_date)` is sorted first by
`group_id`, then by `expense_date` within each group. It can answer:

* `WHERE group_id = 1` (uses the leading column),
* `WHERE group_id = 1 AND expense_date >= '2026-11-01'` (range on the second column),
* `WHERE group_id = 1 ORDER BY expense_date DESC` (rows are already in order).

It **cannot** efficiently answer `WHERE expense_date = '2026-11-01'` alone, because dates are
scattered across groups — the *leftmost prefix* rule. That is also why there is no separate
index on `group_members.group_id`: the unique index `(group_id, user_id)` already starts with
it.

Inspect a plan with `EXPLAIN`:

```sql
EXPLAIN SELECT * FROM expenses WHERE group_id = 1 ORDER BY expense_date DESC LIMIT 20;
```

(With only a few rows PostgreSQL may still choose a sequential scan, because reading one small
page is cheaper than using an index. Index choice is a cost-based decision.)

## 7.12 Joins

A join combines rows from two tables where a condition matches.

**INNER JOIN** — only matching rows. Members of group 1 with their names:

```sql
SELECT u.id, u.name, u.email, gm.role, gm.joined_at
FROM users u
JOIN group_members gm ON gm.user_id = u.id
WHERE gm.group_id = 1
ORDER BY gm.joined_at, u.id;
```

**LEFT (OUTER) JOIN** — all rows from the left table, with NULLs where the right side has no
match. The dashboard uses this to show "my share" of each recent expense, which is NULL when I
was not a participant:

```sql
SELECT e.id, e.description, e.amount_paise,
       COALESCE(es.share_amount_paise, 0) AS my_share
FROM expenses e
LEFT JOIN expense_splits es
       ON es.expense_id = e.id AND es.user_id = :me      -- condition in ON, not WHERE!
WHERE e.group_id IN (SELECT group_id FROM group_members WHERE user_id = :me)
ORDER BY e.expense_date DESC, e.id DESC
LIMIT 8;
```

Putting `es.user_id = :me` in the `WHERE` clause instead of the `ON` clause would silently
turn the LEFT JOIN into an INNER JOIN and hide expenses I am not part of.

**Self-joins / multiple joins to the same table** — settlements reference `users` twice:

```sql
SELECT s.id, payer.name AS paid_by_name, receiver.name AS paid_to_name, s.amount_paise
FROM settlements s
JOIN users payer    ON payer.id = s.paid_by
JOIN users receiver ON receiver.id = s.paid_to
WHERE s.group_id = 1;
```

## 7.13 Aggregate functions

Aggregates collapse many rows into one value: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`.

```sql
SELECT COUNT(id), COALESCE(SUM(amount_paise), 0)
FROM expenses WHERE group_id = 1;
```

`SUM` over zero rows returns `NULL`, not 0 — hence `COALESCE(..., 0)` in the group details
endpoint.

## 7.14 GROUP BY

`GROUP BY` produces one aggregate row per group of equal values. The heart of the balance
calculation is four GROUP BY queries, e.g. how much each user paid in group 1:

```sql
SELECT paid_by, SUM(amount_paise)
FROM expenses
WHERE group_id = 1
GROUP BY paid_by;
```

Every column in the `SELECT` list must either be in `GROUP BY` or inside an aggregate.

## 7.15 HAVING

`WHERE` filters rows *before* grouping; `HAVING` filters groups *after* aggregation. For
example, members whose total share in group 1 exceeds ₹5,000:

```sql
SELECT es.user_id, SUM(es.share_amount_paise) AS total_share
FROM expense_splits es
JOIN expenses e ON e.id = es.expense_id
WHERE e.group_id = 1
GROUP BY es.user_id
HAVING SUM(es.share_amount_paise) > 500000;
```

(SettleUp's code does not need `HAVING`; this query is an example on the real schema.)

## 7.16 Subqueries

A subquery is a query inside another query. SettleUp uses them in two places:

* **Dashboard** — "expenses in any group I belong to":
  `WHERE e.group_id IN (SELECT group_id FROM group_members WHERE user_id = :me)`
* **Member filter** — "expenses this member paid for *or* shares in":

  ```sql
  SELECT * FROM expenses
  WHERE group_id = 1
    AND (paid_by = :member
         OR id IN (SELECT expense_id FROM expense_splits WHERE user_id = :member))
  ORDER BY expense_date DESC, id DESC
  LIMIT 20 OFFSET 0;
  ```

The group list also uses a subquery in the `FROM` clause (a *derived table*) to count members
per group, then joins to it.

## 7.17 Transactions

A transaction groups several statements into one all-or-nothing unit:

```sql
BEGIN;
INSERT INTO expenses (group_id, paid_by, description, amount_paise, category, split_type, expense_date)
VALUES (1, 1, 'Groceries', 120000, 'groceries', 'equal', '2026-11-02') RETURNING id;   -- say 17
INSERT INTO expense_splits (expense_id, user_id, share_amount_paise) VALUES
  (17, 1, 30000), (17, 2, 30000), (17, 3, 30000), (17, 4, 30000);
COMMIT;
```

If anything fails before `COMMIT` — a constraint violation, a crash, a lost connection — the
whole transaction is rolled back and **no** partial expense remains. Chapter 16 covers how
SettleUp uses transactions.

## 7.18 ACID properties

| Property | Meaning | In SettleUp |
|---|---|---|
| **Atomicity** | All statements in a transaction succeed, or none do | An expense and its splits are committed together |
| **Consistency** | A transaction moves the database from one valid state to another; constraints always hold | CHECK/FK/UNIQUE constraints are verified; violating commits are rejected |
| **Isolation** | Concurrent transactions do not see each other's uncommitted work | PostgreSQL's default *Read Committed* level; plus an explicit row lock for settlements |
| **Durability** | Once committed, data survives crashes | PostgreSQL's write-ahead log (WAL) is flushed on commit |

## 7.19 Normalisation

Normalisation organises tables so that each fact is stored once, which prevents *update
anomalies* (changing a fact in one place but not another).

**First Normal Form (1NF)** — every column holds a single atomic value; no repeating groups.
*Violation:* an `expenses.participants` column containing `"1,2,3,4"`. SettleUp instead has
one `expense_splits` row per participant.

**Second Normal Form (2NF)** — 1NF, and every non-key column depends on the *whole* key
(matters for composite keys). *Violation:* if `expense_splits` had key `(expense_id, user_id)`
and also stored `expense_description`, that column would depend only on `expense_id`. SettleUp
keeps the description in `expenses` only.

**Third Normal Form (3NF)** — 2NF, and no non-key column depends on another non-key column
(no transitive dependencies). *Violation:* storing `payer_name` in `expenses` — it depends on
`paid_by`, not on the expense id. SettleUp stores only `paid_by` and joins to `users` for the
name, so renaming a user updates every screen automatically.

**Derived data is not stored.** A `balance` column on `group_members` would violate the
"store each fact once" principle: the balance is a function of expenses, splits and
settlements. Storing it would create a second source of truth that could disagree with the
first. SettleUp computes it on demand.

**Deliberate exception (and why it is acceptable):** `expenses.amount_paise` equals the sum of
its splits, so strictly it is derivable. It is kept because it is the user-entered fact ("the
bill was ₹1,200"), splits are derived *from* it, and the application guarantees they match
inside the same transaction. It also makes "total spending" queries a single-table SUM.

# Chapter 8 — Complete Database Schema

The schema is created by one Alembic migration,
`backend/alembic/versions/0001_create_initial_schema.py` (revision `1eafb6ed5e01`). The SQL
below was generated from that migration with `alembic upgrade head --sql` and is saved in
`docs/schema.sql`.

## 8.1 Why money is stored as integer paise

* Floating-point numbers are binary fractions; most decimal amounts (₹0.10) cannot be stored
  exactly, and rounding errors accumulate when adding many of them.
* Integers are exact. ₹125.50 is stored as `12550`. Sums, differences and comparisons are
  exact; the only place a "rounding" decision is needed is when dividing (equal splits), and
  that is handled explicitly by distributing the remainder paise (Chapter 13.6).
* `BIGINT` (not `INTEGER`) is used so that even very large totals cannot overflow
  (`INTEGER` tops out at about ₹2.1 crore in paise; `BIGINT` at about ₹92 quadrillion).
* The API exchanges paise too; the frontend converts what the user types ("125.50") to paise
  with string operations, never with floating-point multiplication (`utils/money.js`).

## 8.2 Table `users`

**Purpose:** one row per registered account.

```sql
CREATE TABLE users (
    id SERIAL NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (email)
);
```

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | Surrogate key |
| `name` | VARCHAR(100) | NOT NULL | Display name, trimmed by the schema validator |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | Stored lower-case so uniqueness is case-insensitive |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt hash (60 chars, e.g. `$2b$12$...`); never returned by the API |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` | Set by the database |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()` | SQLAlchemy sets it on ORM updates (`onupdate=func.now()`) |

Example row: `(1, 'Sarvesh', 'sarvesh@example.com', '$2b$12$…', '2026-11-20 11:25:03+00', …)`

Referenced by: `groups.created_by`, `group_members.user_id`, `expenses.paid_by`,
`expense_splits.user_id`, `settlements.paid_by`, `settlements.paid_to` — all with
`ON DELETE RESTRICT`, so a user with any history cannot be deleted. (The app has no
delete-account feature.)

## 8.3 Table `groups`

**Purpose:** a set of people who share expenses.

```sql
CREATE TABLE groups (
    id SERIAL NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);
CREATE INDEX ix_groups_created_by ON groups (created_by);
```

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `name` | VARCHAR(100) | NOT NULL | Group names need not be unique ("Room 204" can exist in many hostels) |
| `created_by` | INTEGER | NOT NULL, FK → users.id RESTRICT | Who created it (they start as admin) |
| `created_at`, `updated_at` | TIMESTAMPTZ | NOT NULL | |

`created_by` records history; current permissions come from `group_members.role`, because the
creator might later leave and hand admin rights to someone else.

Note: `groups` is a reserved-ish word in some SQL dialects but is a legal table name in
PostgreSQL; SQLAlchemy quotes identifiers when necessary.

## 8.4 Table `group_members`

**Purpose:** the junction table of the many-to-many relationship users ↔ groups, plus each
member's role and join time.

```sql
CREATE TABLE group_members (
    id SERIAL NOT NULL,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_group_members_role CHECK (role IN ('admin', 'member')),
    FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT uq_group_members_group_user UNIQUE (group_id, user_id)
);
CREATE INDEX ix_group_members_user_id ON group_members (user_id);
```

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | Surrogate key (a composite PK `(group_id, user_id)` would also work) |
| `group_id` | INTEGER | NOT NULL, FK → groups CASCADE | Deleting a group removes its memberships |
| `user_id` | INTEGER | NOT NULL, FK → users RESTRICT | |
| `role` | VARCHAR(20) | NOT NULL, CHECK in ('admin','member') | |
| `joined_at` | TIMESTAMPTZ | NOT NULL, default now() | Used to order members and choose who is promoted when the last admin leaves |
| | | UNIQUE (group_id, user_id) | No duplicate memberships |

Example rows for Room 204: `(1, 1, 1, 'admin', …)`, `(2, 1, 2, 'member', …)`,
`(3, 1, 3, 'member', …)`, `(4, 1, 4, 'member', …)`.

## 8.5 Table `expenses`

**Purpose:** one row per bill: who paid, how much, when, what for, and how it is split.

```sql
CREATE TABLE expenses (
    id SERIAL NOT NULL,
    group_id INTEGER NOT NULL,
    paid_by INTEGER NOT NULL,
    description VARCHAR(200) NOT NULL,
    amount_paise BIGINT NOT NULL,
    category VARCHAR(30) NOT NULL,
    split_type VARCHAR(10) NOT NULL,
    notes TEXT,
    expense_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_expenses_category CHECK (category IN ('food', 'groceries', 'rent', 'utilities',
        'transport', 'entertainment', 'shopping', 'other')),
    CONSTRAINT ck_expenses_split_type CHECK (split_type IN ('equal', 'custom')),
    CONSTRAINT ck_expenses_amount_positive CHECK (amount_paise > 0),
    FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE,
    FOREIGN KEY(paid_by) REFERENCES users (id) ON DELETE RESTRICT
);
CREATE INDEX ix_expenses_group_id_expense_date ON expenses (group_id, expense_date);
CREATE INDEX ix_expenses_paid_by ON expenses (paid_by);
```

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `group_id` | INTEGER | NOT NULL, FK → groups CASCADE | |
| `paid_by` | INTEGER | NOT NULL, FK → users RESTRICT | Must be a group member (checked by the API) |
| `description` | VARCHAR(200) | NOT NULL | Trimmed, non-blank |
| `amount_paise` | BIGINT | NOT NULL, CHECK > 0 | API also caps at ₹1 crore |
| `category` | VARCHAR(30) | NOT NULL, CHECK in list | Same list as the Pydantic `Category` literal |
| `split_type` | VARCHAR(10) | NOT NULL, CHECK in ('equal','custom') | Remembers how the user split it, so the edit form can re-open in the same mode |
| `notes` | TEXT | nullable | Only optional column in the schema |
| `expense_date` | DATE | NOT NULL | When the expense happened (may differ from `created_at`) |
| `created_at`, `updated_at` | TIMESTAMPTZ | NOT NULL | |

Example: `(17, 1, 1, 'Groceries', 120000, 'groceries', 'equal', NULL, '2026-11-02', …)`

**Why category is a CHECK and not a separate table:** the list is small and fixed, and a CHECK
keeps the schema to six tables as the brief asks. If users needed custom categories, a
`categories` table with a foreign key would be the better design.

## 8.6 Table `expense_splits`

**Purpose:** one row per participant of an expense, with the exact share they owe.

```sql
CREATE TABLE expense_splits (
    id SERIAL NOT NULL,
    expense_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    share_amount_paise BIGINT NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_expense_splits_share_positive CHECK (share_amount_paise > 0),
    FOREIGN KEY(expense_id) REFERENCES expenses (id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT uq_expense_splits_expense_user UNIQUE (expense_id, user_id)
);
CREATE INDEX ix_expense_splits_user_id ON expense_splits (user_id);
```

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `expense_id` | INTEGER | NOT NULL, FK → expenses CASCADE | Deleting an expense deletes its splits |
| `user_id` | INTEGER | NOT NULL, FK → users RESTRICT | Must be a group member (API) |
| `share_amount_paise` | BIGINT | NOT NULL, CHECK > 0 | Zero shares are pointless; leave the person out instead |
| | | UNIQUE (expense_id, user_id) | A person appears at most once per expense |

Rules enforced by the application inside the creating transaction: at least one split per
expense, and `SUM(share_amount_paise) = expenses.amount_paise`.

The payer is usually also a participant (they ate the groceries too), so they get a split row
like everyone else; their net effect is `amount − own share`.

## 8.7 Table `settlements`

**Purpose:** a record that one member repaid another (outside the app).

```sql
CREATE TABLE settlements (
    id SERIAL NOT NULL,
    group_id INTEGER NOT NULL,
    paid_by INTEGER NOT NULL,
    paid_to INTEGER NOT NULL,
    amount_paise BIGINT NOT NULL,
    settled_at DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_settlements_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT ck_settlements_different_users CHECK (paid_by <> paid_to),
    FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE,
    FOREIGN KEY(paid_by) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY(paid_to) REFERENCES users (id) ON DELETE RESTRICT
);
CREATE INDEX ix_settlements_group_id_settled_at ON settlements (group_id, settled_at);
```

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `group_id` | INTEGER | NOT NULL, FK → groups CASCADE | Settlements are per group |
| `paid_by` | INTEGER | NOT NULL, FK → users | The debtor who paid |
| `paid_to` | INTEGER | NOT NULL, FK → users | The creditor who received |
| `amount_paise` | BIGINT | NOT NULL, CHECK > 0 | Must not exceed outstanding amounts (API, under lock) |
| `settled_at` | DATE | NOT NULL | Day the payment happened (defaults to today) |
| `created_at` | TIMESTAMPTZ | NOT NULL | When it was recorded |
| | | CHECK paid_by <> paid_to | You cannot repay yourself |

Example: `(4, 3, 8, 6, 30000, '2026-11-10', …)` — Aman (8) paid Rahul (6) ₹300.

There is no `updated_at` and no edit/delete endpoint: a settlement is treated as an immutable
financial record. A wrong settlement would be corrected by recording a new one (or, as future
scope, a reversal feature).

## 8.8 Summary of constraints and indexes

| Table | PK | FKs (on delete) | UNIQUE | CHECK | Extra indexes |
|---|---|---|---|---|---|
| users | id | — | email | — | — |
| groups | id | created_by→users (RESTRICT) | — | — | created_by |
| group_members | id | group_id→groups (CASCADE), user_id→users (RESTRICT) | (group_id, user_id) | role | user_id |
| expenses | id | group_id→groups (CASCADE), paid_by→users (RESTRICT) | — | amount>0, split_type, category | (group_id, expense_date), paid_by |
| expense_splits | id | expense_id→expenses (CASCADE), user_id→users (RESTRICT) | (expense_id, user_id) | share>0 | user_id |
| settlements | id | group_id→groups (CASCADE), paid_by/paid_to→users (RESTRICT) | — | amount>0, paid_by<>paid_to | (group_id, settled_at) |

**Cascade policy in one sentence:** things that *belong to* a group or an expense are deleted
with it (CASCADE); references to *people* block deletion (RESTRICT) so financial history is
never silently lost.

## 8.9 How the schema avoids duplication and stays consistent

* Each fact lives in exactly one place: names in `users`, membership in `group_members`, who
  owes what of a bill in `expense_splits`.
* Balances are computed, never stored.
* Foreign keys make orphan rows impossible; unique constraints make duplicate memberships and
  duplicate participants impossible; CHECKs make negative money and self-payments impossible.
* Multi-row invariants (splits sum to amount; settlement does not exceed debt) are enforced in
  the API inside a single transaction.

# Chapter 9 — Entity Relationship Diagram

## 9.1 The diagram

```mermaid
erDiagram
    users {
        int id PK
        varchar name
        varchar email UK
        varchar password_hash
        timestamptz created_at
        timestamptz updated_at
    }
    groups {
        int id PK
        varchar name
        int created_by FK
        timestamptz created_at
        timestamptz updated_at
    }
    group_members {
        int id PK
        int group_id FK
        int user_id FK
        varchar role
        timestamptz joined_at
    }
    expenses {
        int id PK
        int group_id FK
        int paid_by FK
        varchar description
        bigint amount_paise
        varchar category
        varchar split_type
        text notes
        date expense_date
        timestamptz created_at
        timestamptz updated_at
    }
    expense_splits {
        int id PK
        int expense_id FK
        int user_id FK
        bigint share_amount_paise
    }
    settlements {
        int id PK
        int group_id FK
        int paid_by FK
        int paid_to FK
        bigint amount_paise
        date settled_at
        timestamptz created_at
    }
    users ||--o{ groups : "creates (created_by)"
    users ||--o{ group_members : "has memberships"
    groups ||--|{ group_members : "has members"
    groups ||--o{ expenses : "contains"
    users ||--o{ expenses : "pays (paid_by)"
    expenses ||--|{ expense_splits : "is split into"
    users ||--o{ expense_splits : "owes share"
    groups ||--o{ settlements : "records"
    users ||--o{ settlements : "pays (paid_by)"
    users ||--o{ settlements : "receives (paid_to)"
```

Cardinality notation (crow's foot): `||` exactly one, `o{` zero or more, `|{` one or more.

## 9.2 Relationship by relationship

**users → groups (creates), one-to-many.** A user can create zero or more groups; each group
has exactly one creator (`groups.created_by`, NOT NULL).

**users ↔ groups (membership), many-to-many via `group_members`.** A user can belong to many
groups and a group has many users. Each `group_members` row is one (user, group) pair with a
role. A group always has at least one member through the API (the creator is added in the
same transaction, and the last member cannot leave), shown as `|{` on the group side.

**groups → expenses, one-to-many.** Every expense belongs to exactly one group; a group may
have none.

**users → expenses (pays), one-to-many.** Each expense has exactly one payer.

**expenses → expense_splits, one-to-many (one-or-more).** Every expense has at least one split
(enforced by the API, `|{`). Deleting the expense deletes its splits.

**users ↔ expenses (participates), many-to-many via `expense_splits`.** A user participates in
many expenses; an expense has many participants. The junction row carries the
`share_amount_paise`.

**groups → settlements, one-to-many**, and **users → settlements twice** (as payer and as
receiver). Two foreign keys to the same table are normal; they represent two different roles.

## 9.3 Why `group_members` is a junction table

Alternatives and why they fail:

* *A `group_ids` array/CSV column in `users`* — violates 1NF; cannot have a foreign key to
  `groups`; "members of group 5" needs a scan of all users; nowhere to put role or join date;
  concurrent updates to the same array overwrite each other.
* *A `group_id` column in `users`* — a user could belong to only one group.
* *A `member_ids` column in `groups`* — same problems mirrored.

A junction table gives one row per membership, real foreign keys, a UNIQUE constraint against
duplicates, indexes in both directions, and a place for relationship attributes (`role`,
`joined_at`).

## 9.4 Why `expense_splits` is a separate table

If participants were stored in one column of `expenses` (e.g. `"1:30000,2:30000,…"` or a JSON
array):

* the database could not check that each user exists (no FK),
* it could not stop the same person appearing twice (no UNIQUE),
* "how much does Kiran owe in total" would require parsing text in SQL instead of a simple
  `SUM ... GROUP BY user_id`,
* custom amounts per person would be awkward and unvalidated.

With a table, each share is a typed, constrained, indexed row, and balances are standard
aggregate queries.

## 9.5 Worked example of the relationships

Room 204 (group 1), the ₹1,200 grocery expense (id 17) paid by Sarvesh (user 1):

| Table | Rows created |
|---|---|
| groups | `(1, 'Room 204', created_by=1)` |
| group_members | `(g=1,u=1,'admin')`, `(1,2,'member')`, `(1,3,'member')`, `(1,4,'member')` |
| expenses | `(17, group_id=1, paid_by=1, 'Groceries', 120000, 'groceries', 'equal', …)` |
| expense_splits | `(17,1,30000)`, `(17,2,30000)`, `(17,3,30000)`, `(17,4,30000)` |

Later, Rahul (2) repays Sarvesh (1) ₹300, which adds one row to `settlements`:
`(group_id=1, paid_by=2, paid_to=1, amount_paise=30000, settled_at='2026-11-10')`.

Following the keys: settlement → group 1 → members; expense 17 → group 1 and payer 1;
splits → expense 17 and users 1–4. Every arrow in the ER diagram is one of these foreign keys.

# Chapter 10 — SQLAlchemy ORM

## 10.1 What ORM means

An **Object-Relational Mapper** maps database tables to classes and rows to objects. Instead
of writing `INSERT INTO users ...` you create a `User(...)` object and add it to a session;
instead of reading tuples you get `User` objects with attributes. The ORM generates
parameterised SQL, tracks which objects changed, and writes them in the right order.

## 10.2 Why SQLAlchemy

* It is the standard Python ORM, independent of any web framework.
* SQLAlchemy 2.x has a typed, explicit style (`Mapped[...]`, `select()`), so the code reads
  close to SQL and editors understand the types.
* It does not hide transactions: you call `commit()` and `rollback()` yourself.
* It has two layers — Core (SQL expression language) and ORM — and SettleUp uses both: ORM
  objects for writes and simple reads, Core-style `select(column, func.sum(...))` for
  aggregates.

## 10.3 Engine, session factory and Base (`app/database.py`)

```python
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    """Parent class of every ORM model. Base.metadata describes all tables."""
```

* **Engine** — holds the connection *pool* and knows the dialect (PostgreSQL via
  `postgresql+psycopg://...`). `pool_pre_ping=True` tests a pooled connection before using it,
  so a database restart does not break the next request.
* **Session** — a unit of work: it holds the objects you are working with and one database
  transaction. A new session is created per HTTP request by `get_db()` and closed afterwards.
* `autoflush=False` — SQL is not sent automatically before every query; it is sent on
  `flush()`/`commit()`. This makes the order of SQL predictable.
* `expire_on_commit=False` — after `commit()` objects keep their loaded attribute values, so
  the router can still build the response from them without reloading.
* **Base** — every model inherits from it; `Base.metadata` is the collection of `Table`
  definitions Alembic compares against the database.

## 10.4 Models and columns

```python
class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_expenses_amount_positive"),
        CheckConstraint("split_type IN ('equal', 'custom')", name="ck_expenses_split_type"),
        CheckConstraint("category IN ('food', 'groceries', 'rent', 'utilities', 'transport', "
                        "'entertainment', 'shopping', 'other')", name="ck_expenses_category"),
        Index("ix_expenses_group_id_expense_date", "group_id", "expense_date"),
        Index("ix_expenses_paid_by", "paid_by"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    paid_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    split_type: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), onupdate=func.now())
```

How each piece maps to PostgreSQL:

| Python | PostgreSQL |
|---|---|
| `__tablename__ = "expenses"` | `CREATE TABLE expenses` |
| `Mapped[int]` + `primary_key=True` | `id SERIAL NOT NULL, PRIMARY KEY (id)` |
| `ForeignKey("groups.id", ondelete="CASCADE")` | `FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE` |
| `String(200)` | `VARCHAR(200)` |
| `BigInteger` | `BIGINT` |
| `Mapped[str | None]` / `nullable=True` | column allows NULL |
| `server_default=func.now()` | `DEFAULT now()` (set by the database) |
| `onupdate=func.now()` | SQLAlchemy adds `updated_at=now()` to ORM UPDATEs |
| `default="other"` | Python-side default when the attribute is not set |
| `CheckConstraint`, `UniqueConstraint`, `Index` in `__table_args__` | named constraints and indexes |

## 10.5 `ForeignKey` and `relationship()`

`ForeignKey` defines the *column-level* link in the database. `relationship()` defines the
*object-level* navigation in Python. They are independent: the database only knows about the
foreign key; `relationship()` is how SQLAlchemy lets you write `expense.splits` or
`expense.payer.name`.

```python
class Expense(Base):
    group: Mapped["Group"] = relationship(back_populates="expenses")
    payer: Mapped["User"] = relationship()
    splits: Mapped[list["ExpenseSplit"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", passive_deletes=True,
        order_by="ExpenseSplit.user_id",
    )

class ExpenseSplit(Base):
    expense: Mapped["Expense"] = relationship(back_populates="splits")
    user: Mapped["User"] = relationship()
```

* `back_populates` links the two sides: appending a split to `expense.splits` also sets
  `split.expense`.
* `cascade="all, delete-orphan"` — when the expense is added, its splits are added; when it
  is deleted, they are deleted; and a split removed from the list (`expense.splits.clear()`)
  is deleted. This is what makes "replace all splits" during an edit work.
* `passive_deletes=True` — SQLAlchemy relies on the database's `ON DELETE CASCADE` instead of
  loading every child row just to delete it.
* `order_by` — splits always come back sorted by user id.

Settlements need `foreign_keys=` because there are two foreign keys to `users` and SQLAlchemy
cannot guess which one a relationship uses:

```python
payer: Mapped["User"] = relationship(foreign_keys=[paid_by])
receiver: Mapped["User"] = relationship(foreign_keys=[paid_to])
```

## 10.6 Querying

SQLAlchemy 2 uses `select()`:

```python
# one object by primary key (uses the identity map; may not hit the DB if already loaded)
user = db.get(User, user_id)

# one object by a condition -> SELECT ... WHERE email = %(email_1)s
existing = db.scalar(select(User).where(User.email == payload.email))

# a list of scalar values
member_ids = set(db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == group_id)).all())

# tuples of columns, including aggregates
rows = db.execute(select(Expense.paid_by, func.sum(Expense.amount_paise))
                  .where(Expense.group_id == group_id)
                  .group_by(Expense.paid_by)).all()
```

`db.scalar()` returns the first column of the first row (or `None`), `db.scalars()` iterates
the first column, and `db.execute()` returns full rows.

All values are sent as **bound parameters** (`%(email_1)s`), never pasted into the SQL string,
which is why SQL injection is not possible through these queries.

## 10.7 Adding records

```python
group = Group(name=payload.name, created_by=current_user.id)
group.members.append(GroupMember(user_id=current_user.id, role=ROLE_ADMIN))
db.add(group)
db.commit()
```

`db.add()` puts the object into the session (state *pending*). On `commit()` SQLAlchemy
flushes: it INSERTs the group, reads back its generated `id` (`RETURNING groups.id`), uses it
as `group_members.group_id`, INSERTs the membership, then COMMITs. The developer never
handles the new id manually.

## 10.8 Updating records

Change attributes on a loaded object and commit:

```python
setattr(expense, field, value)   # e.g. expense.notes = "Big Bazaar"
expense.paid_by = new_paid_by
db.commit()                       # UPDATE expenses SET notes=..., updated_at=now() WHERE id=...
```

The session tracks which attributes changed ("dirty" objects) and updates only those columns.

## 10.9 Deleting records

```python
db.delete(expense)
db.commit()
```

The captured SQL for `DELETE /expenses/{id}` is:

```sql
DELETE FROM expense_splits WHERE expense_splits.id = %(id)s::INTEGER   -- once per split row
DELETE FROM expenses WHERE expenses.id = %(id)s::INTEGER
```

The endpoint had already loaded the splits (with `selectinload`), so the ORM's
`cascade="all, delete-orphan"` deletes them itself before the parent. `passive_deletes=True`
only applies to children that are *not* loaded: then SQLAlchemy skips loading them and lets
PostgreSQL's `ON DELETE CASCADE` remove them. Either way, everything happens in one
transaction.

## 10.10 Commits, rollbacks and transactions in the session

* A session starts a transaction implicitly on its first SQL statement.
* `db.commit()` flushes pending changes and commits the transaction.
* `db.rollback()` discards everything since the last commit.
* `db.flush()` sends pending SQL **without** committing — used in the expense update to delete
  old splits before inserting new ones, inside the same transaction.
* If an exception escapes an endpoint, `get_db()` calls `rollback()`; if the endpoint returns
  without committing, `close()` also discards the work. Either way, nothing half-done is
  ever committed.

## 10.11 Loading strategies used in the project

By default relationships are **lazy-loaded**: `expense.payer` triggers a `SELECT` the first
time it is accessed. In a list of 20 expenses that means 1 query for the list + 20 for payers
+ 20 for splits + more for split users — the classic **N+1 query problem**.

SettleUp avoids it with `selectinload`:

```python
select(Expense).where(...).options(
    selectinload(Expense.payer),
    selectinload(Expense.splits).selectinload(ExpenseSplit.user),
)
```

`selectinload` runs one extra query per relationship using `WHERE id IN (...)`. The captured
SQL for a page of expenses is exactly four statements (expenses, their splits, the payers,
the split users), regardless of the page size — see Chapter 11.5.

## 10.12 How models correspond to tables (summary)

| Model class | Table | Relationships defined |
|---|---|---|
| `User` | `users` | `memberships` → GroupMember |
| `Group` | `groups` | `creator`, `members`, `expenses`, `settlements` |
| `GroupMember` | `group_members` | `group`, `user` |
| `Expense` | `expenses` | `group`, `payer`, `splits` |
| `ExpenseSplit` | `expense_splits` | `expense`, `user` |
| `Settlement` | `settlements` | `group`, `payer`, `receiver` |

## 10.13 Alembic migrations

Alembic keeps the database schema in step with the models through versioned migration
scripts:

```powershell
alembic revision --autogenerate -m "create initial schema"   # compare models with DB, write a script
alembic upgrade head                                         # apply all pending migrations
alembic downgrade -1                                         # undo the last migration
alembic upgrade head --sql                                   # print the SQL instead of running it
```

`alembic/env.py` imports `app.models` (so all tables are registered on `Base.metadata`) and
reads `DATABASE_URL` from the same settings as the app. Autogenerated scripts are reviewed
before committing — autogenerate cannot detect everything (for example, renamed columns look
like a drop plus an add). The table `alembic_version` stores which revision the database is at.

# Chapter 11 — Database Queries Used in SettleUp

The SQL below is what SQLAlchemy actually sent to PostgreSQL, captured with an engine event
listener while calling the real endpoints (parameter placeholders such as `%(group_id_1)s`
are filled in by the driver). Some queries are lightly re-indented for readability.

## 11.1 User registration lookup

```sql
SELECT users.id, users.name, users.email, users.password_hash, users.created_at, users.updated_at
FROM users
WHERE users.email = %(email_1)s::VARCHAR;
-- then, if no row was found:
INSERT INTO users (name, email, password_hash) VALUES (%(name)s, %(email)s, %(password_hash)s)
RETURNING users.id, users.created_at, users.updated_at;
```

1. **What:** checks whether the (lower-cased) email exists, then inserts the user.
2. **Why:** to give a clear 409 error for duplicates. The UNIQUE constraint still protects
   against two simultaneous registrations; that case is caught as `IntegrityError`.
3. **Tables:** `users` (uses the unique index on `email`).
4. **Returns:** zero or one user row; the INSERT returns generated values.

## 11.2 Fetching group members

```sql
SELECT users.id, users.name, users.email, group_members.role, group_members.joined_at
FROM users JOIN group_members ON group_members.user_id = users.id
WHERE group_members.group_id = %(group_id_1)s::INTEGER
ORDER BY group_members.joined_at, users.id;
```

1. **What:** all members of a group with their role and join time.
2. **Why:** members page, group details, payer/participant pickers in the expense form.
3. **Tables:** `group_members` ⋈ `users`.
4. **Returns:** one row per member, oldest member first.

The **membership check** that guards almost every endpoint is:

```sql
SELECT group_members.id, group_members.group_id, group_members.user_id, group_members.role, group_members.joined_at
FROM group_members
WHERE group_members.group_id = %(group_id_1)s::INTEGER AND group_members.user_id = %(user_id_1)s::INTEGER;
```

It is answered directly from the unique index `(group_id, user_id)`.

## 11.3 Listing my groups (with member counts)

```sql
SELECT groups.id, groups.name, groups.created_by, groups.created_at, groups.updated_at,
       group_members.role, anon_1.member_count
FROM groups
JOIN group_members ON group_members.group_id = groups.id
JOIN (SELECT group_members.group_id AS group_id, count(group_members.id) AS member_count
      FROM group_members GROUP BY group_members.group_id) AS anon_1
  ON anon_1.group_id = groups.id
WHERE group_members.user_id = %(user_id_1)s::INTEGER
ORDER BY groups.created_at DESC, groups.id DESC;
```

1. **What:** the groups I belong to, my role in each, and how many members each has.
2. **Why:** the Groups page.
3. **Tables:** `groups`, `group_members` (twice: once for "me", once in the derived table).
4. **Returns:** one row per group. (The router then computes my balance per group with the
   balance queries in 11.7 — one set per group, acceptable at this scale; see Chapter 23.)

## 11.4 Adding an expense

Captured SQL (psycopg starts the transaction implicitly; `COMMIT` is sent by `db.commit()`):

```sql
INSERT INTO expenses (group_id, paid_by, description, amount_paise, category, split_type, notes, expense_date)
VALUES (%(group_id)s::INTEGER, %(paid_by)s::INTEGER, %(description)s::VARCHAR, %(amount_paise)s::BIGINT,
        %(category)s::VARCHAR, %(split_type)s::VARCHAR, %(notes)s::VARCHAR, %(expense_date)s::DATE)
RETURNING expenses.id, expenses.created_at, expenses.updated_at;

INSERT INTO expense_splits (expense_id, user_id, share_amount_paise)
SELECT p0::INTEGER, p1::INTEGER, p2::BIGINT
FROM (VALUES (%(expense_id__0)s::INTEGER, %(user_id__0)s::INTEGER, %(share_amount_paise__0)s::BIGINT, 0),
             (%(expense_id__1)s::INTEGER, %(user_id__1)s::INTEGER, %(share_amount_paise__1)s::BIGINT, 1),
             (%(expense_id__2)s::INTEGER, %(user_id__2)s::INTEGER, %(share_amount_paise__2)s::BIGINT, 2),
             (%(expense_id__3)s::INTEGER, %(user_id__3)s::INTEGER, %(share_amount_paise__3)s::BIGINT, 3))
     AS imp_sen(p0, p1, p2, sen_counter)
ORDER BY sen_counter
RETURNING expense_splits.id, expense_splits.id AS id__1;
```

The second statement is SQLAlchemy's *insertmanyvalues* batching: all four splits go in one
round trip, and the `sen_counter` column keeps the returned ids in the same order as the
objects. Written by hand, it is equivalent to
`INSERT INTO expense_splits (expense_id, user_id, share_amount_paise) VALUES (17,1,30000), (17,2,30000), (17,3,30000), (17,4,30000);`

1. **What:** stores the bill and every participant's share.
2. **Why:** this is the core write of the application.
3. **Tables:** `expenses`, `expense_splits`.
4. **Returns:** the generated ids; the router then reloads the expense with its payer and
   splits for the response.

## 11.5 Fetching expense history (filters + pagination)

With `?category=food&member_id=4&page=1&page_size=20`:

```sql
SELECT count(expenses.id) AS count_1
FROM expenses
WHERE expenses.group_id = %(group_id_1)s::INTEGER
  AND expenses.category = %(category_1)s::VARCHAR
  AND (expenses.paid_by = %(paid_by_1)s::INTEGER
       OR expenses.id IN (SELECT expense_splits.expense_id FROM expense_splits
                          WHERE expense_splits.user_id = %(user_id_1)s::INTEGER));

SELECT expenses.id, expenses.group_id, expenses.paid_by, expenses.description, expenses.amount_paise,
       expenses.category, expenses.split_type, expenses.notes, expenses.expense_date,
       expenses.created_at, expenses.updated_at
FROM expenses
WHERE <same conditions>
ORDER BY expenses.expense_date DESC, expenses.id DESC
LIMIT %(param_1)s::INTEGER OFFSET %(param_2)s::INTEGER;

-- selectinload: splits, payers and split users for exactly the expenses on this page
SELECT expense_splits.expense_id, expense_splits.id, expense_splits.user_id, expense_splits.share_amount_paise
FROM expense_splits WHERE expense_splits.expense_id IN (%(primary_keys_1)s, %(primary_keys_2)s)
ORDER BY expense_splits.user_id;
SELECT users.* FROM users WHERE users.id IN (...);   -- payers
SELECT users.* FROM users WHERE users.id IN (...);   -- split participants
```

1. **What:** a filtered page of expenses, newest first, plus the total count for the pager.
2. **Why:** the group's Expenses tab.
3. **Tables:** `expenses`, `expense_splits` (subquery and eager load), `users`.
4. **Returns:** `{items, total, page, page_size}`. `ORDER BY expense_date DESC, id DESC`
   gives a stable order even when several expenses share a date.

`OFFSET` pagination is simple and fine for hundreds of rows; for very large histories
*keyset pagination* (`WHERE (expense_date, id) < (:last_date, :last_id)`) would be faster.

## 11.6 Joining expenses and users

The recent-expenses part of the dashboard joins four tables:

```sql
SELECT expenses.*, groups.name, users.name AS name_1,
       coalesce(expense_splits.share_amount_paise, 0) AS coalesce_1
FROM expenses
JOIN groups ON groups.id = expenses.group_id
JOIN users ON users.id = expenses.paid_by
LEFT OUTER JOIN expense_splits
       ON expense_splits.expense_id = expenses.id AND expense_splits.user_id = %(user_id_1)s::INTEGER
WHERE expenses.group_id IN (SELECT group_members.group_id FROM group_members
                            WHERE group_members.user_id = %(user_id_2)s::INTEGER)
ORDER BY expenses.expense_date DESC, expenses.id DESC
LIMIT 8;
```

1. **What:** the 8 latest expenses across my groups, with group name, payer name, and my share.
2. **Why:** dashboard "Recent expenses".
3. **Tables:** `expenses`, `groups`, `users`, `expense_splits`, `group_members`.
4. **Returns:** up to 8 rows; `my_share` is 0 when I was not a participant (LEFT JOIN +
   COALESCE).

## 11.7 Calculating individual contributions, owed shares and balances

`balance_service.compute_group_balances()` runs these four aggregate queries for one group:

```sql
-- (a) total PAID by each user
SELECT expenses.paid_by, sum(expenses.amount_paise) AS sum_1
FROM expenses WHERE expenses.group_id = %(group_id_1)s::INTEGER
GROUP BY expenses.paid_by;

-- (b) total OWED (share) by each user: splits joined to their expense to filter by group
SELECT expense_splits.user_id, sum(expense_splits.share_amount_paise) AS sum_1
FROM expense_splits JOIN expenses ON expenses.id = expense_splits.expense_id
WHERE expenses.group_id = %(group_id_1)s::INTEGER
GROUP BY expense_splits.user_id;

-- (c) settlements PAID by each user
SELECT settlements.paid_by, sum(settlements.amount_paise) AS sum_1
FROM settlements WHERE settlements.group_id = %(group_id_1)s::INTEGER
GROUP BY settlements.paid_by;

-- (d) settlements RECEIVED by each user
SELECT settlements.paid_to, sum(settlements.amount_paise) AS sum_1
FROM settlements WHERE settlements.group_id = %(group_id_1)s::INTEGER
GROUP BY settlements.paid_to;
```

followed by the current member ids and the names of everyone involved:

```sql
SELECT group_members.user_id FROM group_members WHERE group_members.group_id = %(group_id_1)s::INTEGER;
SELECT users.id, users.name FROM users WHERE users.id IN (%(id_1_1)s, %(id_1_2)s, ...);
```

Python then combines the four dictionaries:
`net = paid − owed + settled_out − settled_in` for each user.

1. **What:** each member's contribution, share, repayments and net balance.
2. **Why:** Balances tab, settlement suggestions, settlement validation, member removal
   check, dashboard.
3. **Tables:** `expenses`, `expense_splits`, `settlements`, `group_members`, `users`.
4. **Returns:** one `BalanceRow` per user who is a member or appears in any record.

The same result can be produced by a **single SQL query** using a `UNION ALL` of signed
amounts — a good interview discussion point (this query is valid on the real schema, but the
application uses the four simpler queries above because they are easier to read and test):

```sql
SELECT user_id, SUM(delta) AS net_balance_paise
FROM (
    SELECT paid_by AS user_id,  amount_paise        AS delta FROM expenses WHERE group_id = 1
    UNION ALL
    SELECT es.user_id,         -es.share_amount_paise         FROM expense_splits es
           JOIN expenses e ON e.id = es.expense_id WHERE e.group_id = 1
    UNION ALL
    SELECT paid_by,             amount_paise                  FROM settlements WHERE group_id = 1
    UNION ALL
    SELECT paid_to,            -amount_paise                  FROM settlements WHERE group_id = 1
) t
GROUP BY user_id
ORDER BY user_id;
```

## 11.8 Retrieving settlement history

```sql
SELECT settlements.id, settlements.group_id, settlements.paid_by, settlements.paid_to,
       settlements.amount_paise, settlements.settled_at, settlements.created_at
FROM settlements
WHERE settlements.group_id = %(group_id_1)s::INTEGER
ORDER BY settlements.settled_at DESC, settlements.id DESC;
-- + selectinload of payer and receiver users (WHERE users.id IN (...))
```

1. **What:** every repayment in a group, newest first.
2. **Why:** History tab.
3. **Tables:** `settlements`, `users` (twice, as payer and receiver).
4. **Returns:** list of settlements with both names.

## 11.9 Monthly expense summaries

```sql
SELECT to_char(expenses.expense_date, 'YYYY-MM') AS to_char_1, sum(expenses.amount_paise) AS sum_1
FROM expenses
WHERE expenses.group_id IN (SELECT group_members.group_id FROM group_members
                            WHERE group_members.user_id = %(user_id_1)s::INTEGER)
  AND expenses.expense_date >= %(expense_date_1)s::DATE          -- first day, 5 months ago
GROUP BY to_char(expenses.expense_date, 'YYYY-MM');

SELECT to_char(expenses.expense_date, 'YYYY-MM') AS to_char_1, sum(expense_splits.share_amount_paise) AS sum_1
FROM expenses JOIN expense_splits ON expense_splits.expense_id = expenses.id
WHERE expenses.group_id IN (...my groups...)
  AND expense_splits.user_id = %(user_id_2)s::INTEGER
  AND expenses.expense_date >= %(expense_date_1)s::DATE
GROUP BY to_char(expenses.expense_date, 'YYYY-MM');
```

1. **What:** total spending per month in my groups, and my share per month.
2. **Why:** the dashboard bar chart.
3. **Tables:** `expenses`, `group_members` (subquery), `expense_splits`.
4. **Returns:** `('2026-11', 2418000)`-style pairs; months with no expenses are filled with 0
   in Python so the chart always shows six months.

## 11.10 Category-wise spending

```sql
SELECT expenses.category, sum(expenses.amount_paise) AS total
FROM expenses
WHERE expenses.group_id IN (SELECT group_members.group_id FROM group_members
                            WHERE group_members.user_id = %(user_id_1)s::INTEGER)
GROUP BY expenses.category
ORDER BY sum(expenses.amount_paise) DESC;
```

1. **What:** total spending per category across my groups, largest first.
2. **Why:** dashboard donut chart and legend.
3. **Tables:** `expenses`, `group_members`.
4. **Returns:** one row per category that has at least one expense.

## 11.11 Settlement validation with a row lock

```sql
SELECT groups.id FROM groups WHERE groups.id = %(id_1)s::INTEGER FOR UPDATE;
-- ...the four balance queries from 11.7...
INSERT INTO settlements (group_id, paid_by, paid_to, amount_paise, settled_at)
VALUES (...) RETURNING settlements.id, settlements.created_at;
COMMIT;   -- releases the lock
```

Explained in Chapter 16.6.

# Chapter 12 — Authentication and Authorisation

**Authentication** answers *"who are you?"* (prove identity: password at login, then a token).
**Authorisation** answers *"what are you allowed to do?"* (membership and role checks on
each resource). SettleUp handles them in different places:

| Concern | Where | Failure |
|---|---|---|
| Authentication | `dependencies/auth.py:get_current_user` (every protected endpoint) | 401 |
| Membership authorisation | `require_group_member`, `_get_expense_for_member` | 404 |
| Role authorisation | `require_group_admin`, `_require_can_modify`, settlement party check | 403 |

## 12.1 Registration workflow

```mermaid
sequenceDiagram
    participant B as Browser
    participant API as POST /auth/register
    participant DB as PostgreSQL
    B->>API: {name, email, password}
    API->>API: Pydantic: name non-blank, email valid (lower-cased), password 8-72 bytes
    API->>DB: SELECT user WHERE email = ?
    alt email exists
        API-->>B: 409 Email is already registered
    else new email
        API->>API: bcrypt hash (random salt, cost 12)
        API->>DB: INSERT users (name, email, password_hash)
        API-->>B: 201 {id, name, email, created_at}
    end
```

```python
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(name=payload.name, email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email is already registered")
    db.refresh(user)
    return user
```

The frontend's `register()` then calls `login()` automatically, so a new user lands on the
dashboard already signed in.

## 12.2 Password hashing

```python
def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
```

* A **hash** is one-way: you cannot get the password back from it.
* **bcrypt** is deliberately slow (cost factor 12 by default ≈ 2^12 rounds), which makes
  brute-force guessing of stolen hashes expensive.
* `gensalt()` creates a random **salt** per password, stored inside the hash string
  (`$2b$12$<22-char salt><31-char hash>`). Two users with the same password get different
  hashes, which defeats pre-computed "rainbow tables".
* `checkpw` re-hashes the candidate with the stored salt and compares in constant time.
* bcrypt only uses the first 72 bytes of input, so the schema rejects longer passwords
  instead of silently ignoring the extra characters.

## 12.3 Password verification at login

```python
@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))
```

The same message is used for "no such email" and "wrong password", so an attacker cannot use
the login form to discover which emails are registered (tested by
`test_login_unknown_email_gives_same_error`).

## 12.4 JWT and its structure

A JSON Web Token is three Base64URL-encoded parts separated by dots:
`header.payload.signature`.

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 . eyJzdWIiOiI1IiwiaWF0IjoxNz…  . 4fG8…signature…
         header                                 payload
```

* **Header**: `{"alg": "HS256", "typ": "JWT"}`
* **Payload (claims)** created by SettleUp: `{"sub": "5", "iat": <issued-at>, "exp": <expiry>}`
  — `sub` (subject) is the user id as a string.
* **Signature**: `HMAC-SHA256(base64(header) + "." + base64(payload), JWT_SECRET_KEY)`.

The payload is **encoded, not encrypted** — anyone can read it — so it must not contain
secrets. What the signature guarantees is that it was issued by someone who knows the secret
key and has not been modified: changing one character makes verification fail (tested by
`test_invalid_or_tampered_token_is_rejected`).

## 12.5 Token generation

```python
def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

The secret key comes from the environment (`JWT_SECRET_KEY` in `.env`), never from the code.
The default in `config.py` is clearly labelled as development-only.

## 12.6 Token validation

```python
def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
```

`jwt.decode` verifies the signature, checks `exp` (expired tokens raise
`ExpiredSignatureError`, a subclass of `PyJWTError`), and requires `sub` and `exp` to be
present. `algorithms=[...]` is an allow-list, which prevents "algorithm confusion" attacks
such as a token claiming `"alg": "none"`.

## 12.7 Bearer authentication and the FastAPI dependency

```mermaid
sequenceDiagram
    participant B as Browser (Axios)
    participant D as get_current_user
    participant DB as PostgreSQL
    participant E as Endpoint
    B->>D: Authorization: Bearer <jwt>
    D->>D: HTTPBearer extracts token (None if header missing)
    D->>D: decode_access_token -> user_id or None
    alt missing / invalid / expired
        D-->>B: 401 Could not validate credentials
    else valid
        D->>DB: SELECT user by id
        alt user deleted
            D-->>B: 401
        else
            D->>E: current_user
        end
    end
```

`HTTPBearer(auto_error=False)` returns `None` instead of raising its own 403 when the header
is missing, so SettleUp can respond with a consistent **401** plus
`WWW-Authenticate: Bearer`.

## 12.8 Protected endpoints

Every endpoint except `POST /auth/register`, `POST /auth/login` and `GET /health` declares
`current_user: User = Depends(get_current_user)`. Forgetting it is the most dangerous mistake
a developer could make, which is why `test_protected_route_requires_token` calls several
endpoints without a token and expects 401.

## 12.9 Group membership verification

```python
def require_group_member(db: Session, group_id: int, user: User) -> GroupMember:
    membership = get_membership(db, group_id, user.id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return membership
```

**Why 404 and not 403?** If outsiders received 403 for existing groups and 404 for missing
ones, they could probe ids to learn which groups exist. Returning 404 for both reveals
nothing. Members who lack a *role* get 403, because they already know the group exists.

**What happens when a user tries to access another group's expense?**
`GET /api/v1/expenses/17` by a user who is not in group 1:

1. `get_current_user` succeeds — the user is authenticated.
2. `_get_expense_for_member` loads expense 17, finds `group_id = 1`, and looks up the caller's
   membership in group 1 — none.
3. It raises `404 Expense not found` — the same response as for an id that does not exist.
4. No expense data is ever serialised.

The walkthrough in Chapter 21 shows this exact response from the running app, and
`test_non_member_cannot_create_or_read_expenses` tests create, list, read and delete.

## 12.10 Admin permission checks

```python
def require_group_admin(db: Session, group_id: int, user: User) -> GroupMember:
    membership = require_group_member(db, group_id, user)
    if membership.role != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only a group admin can perform this action")
    return membership
```

Permission matrix:

| Action | Who may do it |
|---|---|
| View group, members, expenses, balances, settlements | Any member |
| Add a member | Admin |
| Remove another member | Admin |
| Leave the group | The member themself (balance must be zero; not the last member) |
| Create an expense | Any member (payer and participants must be members) |
| Edit / delete an expense | The expense's payer, or an admin |
| Record a settlement | The payer, the receiver, or an admin |

## 12.11 Frontend side of authentication

* `AuthContext` stores the user and exposes `login`, `register`, `logout`.
* The token is saved in `localStorage` under `settleup_token` and attached by the Axios
  request interceptor.
* On page load, if a token exists, `AuthContext` calls `GET /auth/me`; if that fails the token
  is discarded.
* If any API call returns 401 while a token is stored, the response interceptor deletes the
  token and fires a `settleup:logout` event; `AuthContext` listens and logs the user out.
* `ProtectedRoute` redirects anonymous visitors to `/login` and remembers where they were
  going.
* **Logout** simply forgets the token. JWTs are stateless, so the server cannot revoke one
  before it expires — a documented limitation (Chapter 23).

Storing the token in `localStorage` is simple but readable by any JavaScript on the page, so an
XSS bug could leak it. React escapes rendered text by default, which reduces XSS risk; an
httpOnly cookie would be the stronger choice for a production system.

# Chapter 13 — Expense Creation Workflow

This chapter follows one expense from the form to the database: **Sarvesh creates a ₹1,200
grocery expense shared equally by the four roommates.**

## 13.1 Frontend form (`components/ExpenseForm.jsx`)

The form keeps its fields in React state. As Sarvesh types "1200" the amount is converted to
paise and the per-person preview updates instantly using the same algorithm as the backend:

```javascript
const amountPaise = rupeesToPaise(form.amount)           // "1200" -> 120000
const equalPreview = useMemo(
  () => previewEqualSplit(amountPaise ?? 0, [...participants]),
  [amountPaise, participants],
)
```

`rupeesToPaise` never multiplies a float by 100; it splits the string at the decimal point:

```javascript
export function rupeesToPaise(text) {
  if (text === null || text === undefined) return null
  const cleaned = String(text).trim().replace(/,/g, '')
  if (!RUPEES_PATTERN.test(cleaned)) return null            // /^\d{1,8}(\.\d{0,2})?$/
  const [rupees, paise = ''] = cleaned.split('.')
  return parseInt(rupees, 10) * 100 + parseInt(paise.padEnd(2, '0'), 10)
}
```

On submit, `buildPayload()` validates (description present, amount valid, at least one
participant; for custom splits the shares must add up) and produces the exact JSON the
backend expects.

## 13.2 Axios request

```javascript
// pages/ExpensePages.jsx
const expense = await withMessage(expensesApi.create(group.id, payload))

// api/api.js
create: (groupId, body) => data(client.post(`/groups/${groupId}/expenses`, body)),
```

The interceptor adds the JWT. The request is:

```http
POST /api/v1/groups/1/expenses
Authorization: Bearer eyJ...
Content-Type: application/json

{"description":"Groceries","amount_paise":120000,"paid_by":1,"category":"groceries",
 "expense_date":"2026-11-02","notes":null,"split_type":"equal","participant_ids":[1,2,3,4]}
```

## 13.3 FastAPI router

`routers/expenses.py:create_expense` is selected by method + path. `group_id=1` is converted
to `int`.

## 13.4 JWT validation

`Depends(get_current_user)` runs first (Chapter 12.7). Sarvesh's token is valid, so
`current_user` is his `User` object.

## 13.5 Pydantic validation

The body is parsed into `ExpenseCreate`. Field constraints run (`amount_paise > 0`,
`description` 1–200 chars, `category` in the allowed list, `expense_date` is a real date),
then `check_split` runs `validate_split_definition`:

```python
def validate_split_definition(amount_paise, split_type, participant_ids, splits) -> None:
    if split_type == "equal":
        if not participant_ids:
            raise ValueError("Select at least one participant for an equal split")
        if len(set(participant_ids)) != len(participant_ids):
            raise ValueError("A participant is listed more than once")
        if amount_paise < len(participant_ids):
            raise ValueError("Amount is too small to split between that many people")
    else:  # custom
        if not splits:
            raise ValueError("Provide at least one share for a custom split")
        user_ids = [s.user_id for s in splits]
        if len(set(user_ids)) != len(user_ids):
            raise ValueError("A participant is listed more than once")
        total = sum(s.share_amount_paise for s in splits)
        if total != amount_paise:
            raise ValueError(
                f"Custom shares add up to {total} paise but the expense is {amount_paise} paise"
            )
```

Any `ValueError` becomes a 422 response and the endpoint never runs.

## 13.6 Group membership validation

```python
require_group_member(db, group_id, current_user)            # caller must be in the group
participant_ids = (payload.participant_ids if payload.split_type == "equal"
                   else [s.user_id for s in payload.splits])
_check_people_are_members(db, group_id, payload.paid_by, participant_ids)
```

`_check_people_are_members` loads the member ids once and uses set difference to find
outsiders; any outsider (or a non-member payer) gives **400**.

## 13.7 Expense split generation

```python
shares = _build_shares(payload.amount_paise, payload.split_type, payload.participant_ids, payload.splits)
# equal  -> split_equally(120000, [1, 2, 3, 4]) -> {1: 30000, 2: 30000, 3: 30000, 4: 30000}
```

**Handling remainders.** ₹100.00 among three people is 10000 paise ÷ 3 = 3333 remainder 1.
`divmod` gives `base_share = 3333`, `remainder = 1`; the first `remainder` users in ascending
id order get one extra paisa: `{5: 3334, 6: 3333, 7: 3333}`. The shares always sum to the
amount, differ by at most one paisa, and the same input always gives the same output
(deterministic). The test `test_shares_always_add_up_to_amount` checks this for many amounts
and group sizes.

## 13.8 Expense model creation and the database transaction

```python
expense = Expense(
    group_id=group_id, paid_by=payload.paid_by, description=payload.description,
    amount_paise=payload.amount_paise, category=payload.category,
    split_type=payload.split_type, notes=payload.notes, expense_date=payload.expense_date,
)
expense.splits = [ExpenseSplit(user_id=uid, share_amount_paise=amt) for uid, amt in shares.items()]
db.add(expense)
db.commit()
```

Attaching the splits to `expense.splits` means one `db.add()` covers all five objects. On
`commit()` SQLAlchemy:

1. INSERTs the expense and reads back `id = 17` (`RETURNING`),
2. fills `expense_id = 17` into every split,
3. INSERTs the four splits in one batched statement,
4. COMMITs.

## 13.9 Commit — and what if something fails?

All five INSERTs are in the same transaction. If the split insert fails (for example a CHECK
constraint), PostgreSQL aborts the transaction, SQLAlchemy raises, `get_db()` rolls back,
and the expense row is gone too. There is never an expense without its splits.

## 13.10 Response generation

```python
return expense_to_out(_load_expense(db, expense.id))
```

The expense is reloaded with `selectinload` for the payer and split users, converted to
`ExpenseOut` (adding `paid_by_name` and each `user_name`), validated by `response_model`, and
sent as **201 Created**. (The real response is shown in Chapter 21.)

## 13.11 Dashboard and screen updates

The Add Expense page navigates to `/expenses/17` and calls `reloadGroup()` so the group
header (expense count, total spent) is refreshed. Every other screen — balances,
suggestions, dashboard — fetches fresh data when it is opened, and because balances are
computed from the stored rows, they reflect the new expense immediately with no extra code.

# Chapter 14 — Balance Calculation

## 14.1 The formula

> **Net balance = Total paid − Total share owed + Settlements paid − Settlements received**

In code (`balance_service.BalanceRow`):

```python
@property
def net_balance_paise(self) -> int:
    return (self.total_paid_paise - self.total_share_paise
            + self.settlements_paid_paise - self.settlements_received_paise)
```

* **Positive** → the group owes this member money (they should receive).
* **Negative** → this member owes the group.
* **Zero** → settled.

## 14.2 Intuition for each term

* *Total paid*: money you put in for the group. Increases your balance.
* *Total share*: the part of the group's spending that was for you. Decreases it.
* *Settlements paid*: when you repay someone, you have put more money in — your debt shrinks,
  so your balance goes **up** (towards zero).
* *Settlements received*: when someone repays you, you have been compensated, so your
  balance goes **down** (towards zero).

## 14.3 Worked example (real numbers from the walkthrough)

| | Paid | Share | Settl. paid | Settl. received | **Net** |
|---|---:|---:|---:|---:|---:|
| Sarvesh | 1,200.00 | 733.34 | 0 | 0 | **+466.66** |
| Rahul | 1,000.00 | 633.33 | 0 | 0 | **+366.67** |
| Kiran | 0.00 | 533.33 | 0 | 0 | **−533.33** |
| Aman | 100.00 | 400.00 | 0 | 0 | **−300.00** |
| **Sum** | 2,300.00 | 2,300.00 | 0 | 0 | **0.00** |

After Aman records a ₹300 payment to Rahul: Aman `−300 + 300 = 0`; Rahul `366.67 − 300 = +66.67`.

## 14.4 How each amount is retrieved

Four `GROUP BY` queries (Chapter 11.7) return dictionaries such as
`paid = {5: 120000, 6: 100000, 8: 10000}`. Users with no rows simply have no key, and
`dict.get(user_id, 0)` supplies zero. The set of users considered is
`current members ∪ everyone appearing in any record`, so a former member who still has
history is included (marked `is_member: false`).

## 14.5 Why the balances always sum to zero

* Every expense adds `amount` to the payer's *paid* and adds shares totalling exactly `amount`
  to the participants' *owed*. Net effect on the sum: `+amount − amount = 0`.
* Every settlement adds `x` to one person's *settlements paid* and `x` to another's
  *settlements received*. Net effect: `+x − x = 0`.

So the sum is zero by construction, **provided** every expense's splits add up to its amount —
which is exactly the invariant the API enforces. The tests `test_balances_follow_the_formula`
and `test_rounding_balances_still_sum_to_zero` assert it. The settlement algorithm also
checks it and raises if ever violated.

## 14.6 Edge cases

| Case | Behaviour |
|---|---|
| New group, no expenses | Every member has 0; suggestions list is empty |
| Member who paid nothing and owes nothing | Appears with 0 |
| Expense where the payer is not a participant | Payer gets `+amount`; participants share `−amount` |
| Remainder paise | Distributed deterministically; sum still exact |
| Expense edited or deleted | Balances change immediately because they are recomputed |
| Expense edited after a settlement | Balances may flip sign (someone could now be owed); this is mathematically correct and the next suggestion plan reflects it |
| Former member with history | Included in the list, `is_member = false`; their balance had to be 0 to leave, but later edits could change it (documented limitation) |
| Very large amounts | `BIGINT` and Python `int` cannot overflow at realistic values |

## 14.7 Why balances are computed, not stored

A stored `balance` column would have to be updated in every place that changes an expense,
split or settlement — create, edit, delete — and a single missed update or a crash between
two writes would leave it wrong forever. Computing from the source records removes that
whole class of bugs. The cost is a few aggregate queries per request, which on indexed
columns is negligible for groups of this size.

# Chapter 15 — Settlement Optimisation Algorithm

## 15.1 Problem statement

Given each member's net balance (summing to zero), produce a list of payments
*(debtor → creditor, amount)* such that, after all payments, every balance is zero — using as
few payments as reasonably possible.

Naively, every debt could be paid along the original expense lines, which can mean dozens of
small transfers. Working from **net balances** already collapses everything each person owes
or is owed into one number; the algorithm then only has to match debtors with creditors.

## 15.2 Inputs and outputs

* **Input:** `balances: dict[int, int]` — user id → net balance in paise (sum must be 0).
* **Output:** `list[tuple[int, int, int]]` — `(debtor_id, creditor_id, amount_paise)`, every
  amount > 0.

## 15.3 Step-by-step

1. Split users into **creditors** (balance > 0) and **debtors** (balance < 0; store the
   positive amount owed). Users at zero are ignored.
2. Sort both lists by amount, largest first; ties are broken by user id so the output is
   deterministic.
3. Take the current debtor *i* and current creditor *j*. Pay `min(debt_left[i], credit_left[j])`.
4. Subtract the payment from both. If the debtor reaches zero, move to the next debtor; if the
   creditor reaches zero, move to the next creditor (both can happen at once).
5. Repeat until either list is exhausted. Because the totals are equal, both run out together.

## 15.4 Pseudocode

```text
function SUGGEST(balances):
    assert sum(balances) == 0
    C <- [(u, b) for (u, b) in balances if b > 0] sorted by (-b, u)
    D <- [(u, -b) for (u, b) in balances if b < 0] sorted by (-b, u)
    i <- 0; j <- 0; payments <- []
    while i < |D| and j < |C|:
        x <- min(D[i].left, C[j].left)
        payments.append((D[i].user, C[j].user, x))
        D[i].left -= x;  C[j].left -= x
        if D[i].left == 0: i <- i + 1
        if C[j].left == 0: j <- j + 1
    return payments
```

## 15.5 Actual Python implementation (`services/settlement_service.py`)

```python
def suggest_settlements(balances: dict[int, int]) -> list[tuple[int, int, int]]:
    if sum(balances.values()) != 0:
        raise ValueError("Balances must sum to zero")

    creditors = sorted(
        ((user_id, amount) for user_id, amount in balances.items() if amount > 0),
        key=lambda item: (-item[1], item[0]),
    )
    debtors = sorted(
        ((user_id, -amount) for user_id, amount in balances.items() if amount < 0),
        key=lambda item: (-item[1], item[0]),
    )

    payments: list[tuple[int, int, int]] = []
    i = j = 0
    debt_left = [amount for _, amount in debtors]
    credit_left = [amount for _, amount in creditors]

    while i < len(debtors) and j < len(creditors):
        amount = min(debt_left[i], credit_left[j])
        payments.append((debtors[i][0], creditors[j][0], amount))
        debt_left[i] -= amount
        credit_left[j] -= amount
        if debt_left[i] == 0:
            i += 1
        if credit_left[j] == 0:
            j += 1

    return payments
```

The function is **pure** (no database, no I/O), so it is tested directly with many inputs
(Chapter 19). The router supplies balances from `compute_group_balances` and adds names.

## 15.6 Dry run — the example from the problem statement

Balances: Sarvesh +450, Rahul +50, Kiran −150, Aman −350 (rupees).

Sorted creditors: Sarvesh 450, Rahul 50. Sorted debtors: Aman 350, Kiran 150.

| Step | Debtor (left) | Creditor (left) | Payment | After |
|---|---|---|---|---|
| 1 | Aman (350) | Sarvesh (450) | Aman → Sarvesh **350** | Aman 0 → next debtor; Sarvesh 100 |
| 2 | Kiran (150) | Sarvesh (100) | Kiran → Sarvesh **100** | Kiran 50; Sarvesh 0 → next creditor |
| 3 | Kiran (50) | Rahul (50) | Kiran → Rahul **50** | both 0 → done |

Result: 3 payments, totalling ₹500 = total debt. This exact plan is asserted by
`test_example_from_problem_statement` and, end-to-end through the API, by
`test_suggested_settlements_match_example`.

## 15.7 Why greedy matching works (correctness)

* **Every payment is valid**: it goes from someone who owes to someone who is owed, and never
  exceeds either remaining amount, so no one overshoots past zero.
* **It terminates**: every iteration brings at least one participant to exactly zero and
  advances a pointer, so there are at most `|D| + |C|` iterations.
* **It ends with everyone at zero**: the total remaining debt always equals the total remaining
  credit (both start equal because balances sum to zero, and each payment reduces both by the
  same amount). If the loop ended with a debtor still owing, there would have to be credit left
  too, so the loop would not have ended. Hence both lists are exhausted together.
* **At most n − 1 payments** for n people with non-zero balances: each payment settles at least
  one person, and the final payment settles two (the last debtor and the last creditor).

## 15.8 Is it optimal? (honest answer)

**Not always.** Finding the true minimum number of payments is NP-hard in general: the minimum
equals *n − k*, where *k* is the largest number of disjoint subgroups whose balances each sum
to zero (each such subgroup can be settled internally with one fewer payment than its size).
Finding that partition is related to the subset-sum problem.

A concrete counter-example is in the test suite (`test_known_case_where_greedy_is_not_minimal`):

* Three people owe ₹600 each; creditors are owed ₹300, ₹600 and ₹900.
* Greedy makes **5** payments.
* **4** are enough: D1 → C600 (600), D2 → C900 (600), D3 → C900 (300), D3 → C300 (300) —
  because {−600, +600} and {−600, −600, +300, +900} are both zero-sum subgroups.

So the accurate claim is: *the greedy plan is always correct, uses at most n − 1 payments,
is often optimal in practice, but is not guaranteed to be the global minimum.* The test file
includes a small brute-force solver used only to verify this on tiny inputs.

## 15.9 Why this algorithm suits SettleUp

* Groups are small (a handful of people), so plans are short either way.
* It is simple enough to explain, prove and test completely.
* It is deterministic: the same balances always give the same suggestions, so the UI does not
  "jump around" between page loads.
* Integer paise mean there are no rounding leftovers; every plan settles to exactly zero.

## 15.10 Time and space complexity

* Building the two lists: O(n). Sorting: **O(n log n)**.
* The loop: each iteration advances at least one pointer → at most `|D| + |C| ≤ n` iterations
  → O(n).
* Total time **O(n log n)**; extra space **O(n)** for the two lists and the output (≤ n − 1
  payments).
* The database work to compute balances (four indexed GROUP BY queries) dominates in practice.

## 15.11 Edge cases

| Input | Output | Test |
|---|---|---|
| `{}` (empty group) | `[]` | `test_empty_group_returns_no_payments` |
| all zeros | `[]` | `test_everyone_settled_returns_no_payments` |
| one debtor, one creditor | one payment | `test_single_debtor_single_creditor` |
| one creditor, many debtors | each debtor pays the creditor | `test_one_creditor_many_debtors` |
| one debtor, many creditors | debtor pays each creditor, largest first | `test_one_debtor_many_creditors` |
| odd paise | exact settlement | `test_odd_paise_amounts` |
| balances not summing to zero | `ValueError` | `test_unbalanced_input_is_rejected` |
| 25 random groups of 2–12 people | all settle, ≤ n − 1 payments, all amounts > 0 | `test_random_groups_always_settle_with_at_most_n_minus_1_payments` |

## 15.12 How suggestions relate to recorded settlements

Suggestions are **not stored**; they are recomputed from current balances on every request.
When a member records a payment, balances change and the next request returns a new, shorter
plan. A user may also record a payment that differs from the suggestion (for example a partial
payment) — it only has to respect the outstanding amounts (Chapter 16.6).

# Chapter 16 — Database Transactions and Consistency

## 16.1 What a transaction is

A transaction is a sequence of database operations treated as one unit: either all of them
take effect (`COMMIT`) or none do (`ROLLBACK`). PostgreSQL wraps every statement in a
transaction; a session can group many statements into one.

## 16.2 ACID recap in SettleUp terms

* **Atomic** — an expense and its four splits are committed together.
* **Consistent** — no commit can leave a negative amount, a dangling foreign key, or a duplicate
  membership.
* **Isolated** — another request does not see a half-inserted expense.
* **Durable** — once the API returned 201, the expense survives a server restart.

## 16.3 Commit and rollback in the code

* `db.commit()` is called explicitly at the end of every write endpoint.
* `get_db()` rolls back if an exception escapes and always closes the session.
* Where a constraint violation is expected (duplicate email or membership), the router catches
  `IntegrityError`, calls `db.rollback()`, and returns 409.

## 16.4 Why an expense and its splits must be saved atomically

Suppose the expense row were committed and then the server crashed before the splits were
saved. The group would have an expense of ₹1,200 that nobody owes: the payer's balance would
jump by +₹1,200 while nobody's went down, so the balances would no longer sum to zero and
every suggestion would be wrong. Because both are in one transaction, this state can never be
committed.

**What happens if saving a split fails?** For example, a bug produced a split with share 0:

1. The expense INSERT succeeds *inside* the open transaction (not yet visible to others).
2. The split INSERT violates `ck_expense_splits_share_positive`; PostgreSQL raises an error and
   marks the transaction as aborted.
3. SQLAlchemy raises `IntegrityError`; the global handler returns 409 and `get_db()` rolls back.
4. The expense INSERT is undone. The database is exactly as before.

The same reasoning applies to **editing** an expense: the old splits are deleted, `flush()` sends
those DELETEs, the new splits are inserted, and only then is the transaction committed.
Flushing in the middle does not commit; it just orders the SQL so the
`UNIQUE (expense_id, user_id)` constraint is not hit by an old and a new row for the same person.

```python
expense.splits.clear()
db.flush()
expense.splits.extend(ExpenseSplit(user_id=uid, share_amount_paise=amt) for uid, amt in shares.items())
...
db.commit()
```

## 16.5 Isolation at a practical level

PostgreSQL's default isolation level is **Read Committed**: each statement sees data committed
before *that statement* started. It prevents dirty reads (seeing uncommitted data) but allows a
transaction to see different data in two consecutive statements if another transaction commits
in between, and it allows two transactions to read the same rows and then both act on what they
read (a *lost update* / *write skew* risk). Stronger levels (Repeatable Read, Serializable) exist
but make conflicting transactions fail and require retry logic.

## 16.6 Why settlement creation needs validation *and* transaction safety

The rule: a settlement may not exceed what the payer owes or what the receiver is owed.

**The race without locking.** Aman owes ₹350. He double-clicks "Save repayment", sending two
requests for ₹350 at the same moment:

1. Request A computes balances → Aman owes 350 → OK.
2. Request B computes balances → Aman still owes 350 (A has not committed) → OK.
3. Both insert; Aman has now "paid" ₹700 and his balance is +₹350. Wrong.

**The fix used in SettleUp:** lock the group's row before validating.

```python
# Lock this group's row until COMMIT. A second settlement request for the same
# group waits here, so both requests cannot validate against the same old
# balances and together over-settle a debt.
db.execute(select(Group.id).where(Group.id == group_id).with_for_update())

balances = {r.user_id: r.net_balance_paise for r in compute_group_balances(db, group_id)}
owes = -balances.get(payload.paid_by, 0)
is_owed = balances.get(payload.paid_to, 0)
if owes <= 0:  ...400
if is_owed <= 0: ...400
limit = min(owes, is_owed)
if payload.amount_paise > limit: ...400 "Maximum allowed is Rs ..."
db.add(Settlement(...))
db.commit()  # releases the row lock
```

`SELECT ... FOR UPDATE` takes a row-level lock on `groups.id = :group_id`. Request B blocks at
that statement until A commits. Under Read Committed, B's following queries then see A's
committed settlement, so B computes "Aman owes 0" and is rejected with 400. Settlements in
*different* groups do not block each other because they lock different rows.

**Honest scope of this guarantee:** the locking logic follows standard PostgreSQL semantics and
the validation rules are tested, but **no automated concurrent test** was written for this race.
Also, expense creation does not take the same lock, so an expense added at the same instant as
a settlement is validated against slightly older balances; that cannot over-settle beyond the
amounts shown, but it is a documented simplification.

## 16.7 How other concurrent requests behave

| Situation | What happens |
|---|---|
| Two people add expenses to the same group simultaneously | Independent INSERTs; both succeed; balances include both |
| Two registrations with the same email at once | One wins; the other hits the UNIQUE constraint → caught → 409 |
| Two admins add the same member at once | UNIQUE (group_id, user_id) → one gets 409 |
| Two people edit the same expense at once | Each edit is atomic; the last commit wins (no optimistic locking). A clash on split rows could surface as 409 via the IntegrityError handler. Not covered by automated tests. |
| Member removed while someone else adds an expense for them | Not prevented by a lock; the removal check uses the balance at that moment. Documented limitation. |

## 16.8 Consistency rules and where they are enforced

| Rule | Database | API |
|---|---|---|
| Amounts positive | CHECK | Pydantic `gt=0` |
| Category / split type / role valid | CHECK | Pydantic `Literal` |
| No duplicate membership / participant | UNIQUE | explicit check (friendly message) |
| References exist | FOREIGN KEY | membership checks |
| Payer ≠ receiver | CHECK | Pydantic model validator |
| Splits sum to amount | — (multi-row) | Pydantic + `custom_shares` / `split_equally`, same transaction |
| Settlement ≤ outstanding | — (depends on aggregates) | router, under `FOR UPDATE` lock |
| Balances sum to zero | — | follows from the two rules above; asserted in tests |

# Chapter 17 — Complete API Reference

Base URL: `http://localhost:8000/api/v1`. All bodies are JSON. All money values are integers
in paise. For authenticated endpoints send `Authorization: Bearer <access_token>`.

Common error responses (not repeated in every section):

| Status | Body | When |
|---|---|---|
| 401 | `{"detail": "Could not validate credentials"}` | Missing, malformed, tampered or expired token; user no longer exists |
| 422 | `{"detail": [{"loc": ["body","amount_paise"], "msg": "Input should be greater than 0", "type": "greater_than"}]}` | Body, path or query validation failed |
| 500 | `{"detail": "Internal server error"}` | Unexpected error (details only in the server log) |

In the curl examples, `$TOKEN` is the access token from login. On Windows PowerShell use
`curl.exe` (plain `curl` is an alias for `Invoke-WebRequest`), or use Swagger UI / Postman.

---

## 17.1 POST /auth/register

* **Purpose:** create an account.
* **Auth:** none.
* **Body:** `{"name": "Sarvesh", "email": "sarvesh@example.com", "password": "Password@123"}`
* **Validation:** name 1–100 chars, trimmed, not blank; valid email (stored lower-case);
  password 8–72 bytes.
* **Success 201:**
  `{"id": 5, "name": "Sarvesh", "email": "sarvesh@example.com", "created_at": "2026-11-20T12:01:17.693276Z"}`
* **Database:** `SELECT users WHERE email=?`; `INSERT INTO users`.
* **Errors:** 409 `Email is already registered`; 422 invalid fields (the response never echoes
  the submitted password).
* **Example:**

  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" \
       -d '{"name":"Sarvesh","email":"sarvesh@example.com","password":"Password@123"}'
  ```

## 17.2 POST /auth/login

* **Purpose:** exchange email + password for a JWT.
* **Auth:** none.
* **Body:** `{"email": "sarvesh@example.com", "password": "Password@123"}`
* **Success 200:**
  `{"access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer", "user": {"id": 5, "name": "Sarvesh", "email": "...", "created_at": "..."}}`
* **Validation:** email format; password 1–72 chars; bcrypt verification.
* **Database:** `SELECT users WHERE email=?`.
* **Errors:** 401 `Incorrect email or password` (same for unknown email and wrong password).
* **Example:**
  `curl -X POST .../auth/login -H "Content-Type: application/json" -d '{"email":"sarvesh@example.com","password":"Password@123"}'`

## 17.3 GET /auth/me

* **Purpose:** return the logged-in user's profile.
* **Auth:** required. **Authorisation:** the token's own user only.
* **Success 200:** `{"id": 5, "name": "Sarvesh", "email": "...", "created_at": "..."}`
* **Database:** `SELECT users WHERE id = :sub`.
* **Errors:** 401.
* **Example:** `curl http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"`

## 17.4 POST /groups

* **Purpose:** create a group; the caller becomes its admin.
* **Auth:** required. **Authorisation:** any logged-in user.
* **Body:** `{"name": "Room 204"}` (1–100 chars, not blank).
* **Success 201:** a `GroupDetail` (same shape as 17.6) with one member, the caller, as admin.
* **Database:** one transaction: `INSERT INTO groups ... RETURNING id`;
  `INSERT INTO group_members (group_id, user_id, role) VALUES (:id, :me, 'admin')`.
* **Errors:** 401, 422.
* **Example:** `curl -X POST .../groups -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"Room 204"}'`

## 17.5 GET /groups

* **Purpose:** list the groups the caller belongs to.
* **Auth:** required. **Authorisation:** results are filtered to the caller's memberships.
* **Success 200:**

  ```json
  [{"id": 1, "name": "Room 204", "created_by": 1, "created_at": "...",
    "member_count": 4, "my_role": "admin", "my_balance_paise": 4199012}]
  ```

* **Database:** join of `groups`, `group_members` and a member-count derived table
  (Chapter 11.3), then the balance queries per group for `my_balance_paise`.
* **Errors:** 401.
* **Example:** `curl .../groups -H "Authorization: Bearer $TOKEN"`

## 17.6 GET /groups/{group_id}

* **Purpose:** group details with members and totals.
* **Auth:** required. **Authorisation:** member of the group.
* **Path:** `group_id` integer.
* **Success 200:**

  ```json
  {"id": 1, "name": "Room 204", "created_by": 1, "creator_name": "Sarvesh",
   "created_at": "...", "my_role": "admin", "member_count": 4, "expense_count": 13,
   "total_spending_paise": 10846950,
   "members": [{"user_id": 1, "name": "Sarvesh", "email": "sarvesh@example.com",
                "role": "admin", "joined_at": "..."}, ...]}
  ```

* **Database:** membership check; `SELECT count(id), coalesce(sum(amount_paise),0) FROM expenses WHERE group_id=?`; members join (11.2).
* **Errors:** 404 `Group not found` (missing group *or* not a member).
* **Example:** `curl .../groups/1 -H "Authorization: Bearer $TOKEN"`

## 17.7 POST /groups/{group_id}/members

* **Purpose:** add an already-registered user by email.
* **Auth:** required. **Authorisation:** admin of the group.
* **Body:** `{"email": "rahul@example.com"}`
* **Success 201:** `{"user_id": 2, "name": "Rahul", "email": "rahul@example.com", "role": "member", "joined_at": "..."}`
* **Validation:** email format; user exists; not already a member.
* **Database:** `SELECT users WHERE email=?`; membership lookup; `INSERT INTO group_members`.
* **Errors:** 403 not admin; 404 group not found / `No registered user has that email`;
  409 `User is already a member of this group` (also when an admin adds themselves).
* **Example:** `curl -X POST .../groups/1/members -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"email":"rahul@example.com"}'`

## 17.8 GET /groups/{group_id}/members

* **Purpose:** list members (ordered by join time).
* **Auth:** required. **Authorisation:** member.
* **Success 200:** list of `MemberOut` (see 17.7).
* **Database:** query 11.2.
* **Errors:** 404.
* **Example:** `curl .../groups/1/members -H "Authorization: Bearer $TOKEN"`

## 17.9 DELETE /groups/{group_id}/members/{user_id}

* **Purpose:** remove a member (admin) or leave the group (self).
* **Auth:** required. **Authorisation:** admin, or the caller removing themself.
* **Validation:** target is a member; group has more than one member; target's net balance
  in this group is exactly 0. If the target is the only admin, the earliest-joined remaining
  member is promoted to admin in the same transaction.
* **Success:** 204 No Content.
* **Database:** membership lookups; balance queries; optional `UPDATE group_members SET role='admin'`; `DELETE FROM group_members WHERE id=?`.
* **Errors:** 400 `The last member cannot leave the group`; 400 `This member has an unsettled
  balance. Settle up before removing them.`; 403 non-admin removing someone else; 404 group
  not found / `Member not found in this group`.
* **Example:** `curl -X DELETE .../groups/1/members/4 -H "Authorization: Bearer $TOKEN"`

## 17.10 POST /groups/{group_id}/expenses

* **Purpose:** record an expense and its split.
* **Auth:** required. **Authorisation:** member; payer and every participant must be members.
* **Body (equal split):**

  ```json
  {"description": "Groceries", "amount_paise": 120000, "paid_by": 1, "category": "groceries",
   "expense_date": "2026-11-02", "notes": null, "split_type": "equal",
   "participant_ids": [1, 2, 3, 4]}
  ```

* **Body (custom split):** replace the last two fields with
  `"split_type": "custom", "splits": [{"user_id": 1, "share_amount_paise": 40000}, ...]`.
* **Validation:** description 1–200 chars, not blank; `0 < amount_paise ≤ 1,000,000,000`;
  category one of `food, groceries, rent, utilities, transport, entertainment, shopping,
  other`; valid date; notes ≤ 1000 chars; equal: ≥1 participant, no duplicates,
  `amount ≥ participants`; custom: ≥1 share, each share > 0, no duplicates, shares sum
  exactly to the amount.
* **Success 201:** `ExpenseOut`:

  ```json
  {"id": 17, "group_id": 3, "description": "Groceries", "amount_paise": 120000,
   "category": "groceries", "split_type": "equal", "notes": null, "expense_date": "2026-11-02",
   "paid_by": 5, "paid_by_name": "Sarvesh",
   "splits": [{"user_id": 5, "user_name": "Sarvesh", "share_amount_paise": 30000}, ...],
   "created_at": "2026-11-20T12:01:44.812728Z", "updated_at": "2026-11-20T12:01:44.812728Z"}
  ```

* **Database:** one transaction with `INSERT INTO expenses` and a batched
  `INSERT INTO expense_splits` (Chapter 11.4).
* **Errors:** 400 `The payer must be a member of the group` / `These participants are not group
  members: [..]`; 404 group not found; 422 validation (e.g. `Custom shares add up to 40000
  paise but the expense is 100000 paise`).
* **Example:**

  ```bash
  curl -X POST .../groups/1/expenses -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"description":"Groceries","amount_paise":120000,"paid_by":1,"category":"groceries","expense_date":"2026-11-02","split_type":"equal","participant_ids":[1,2,3,4]}'
  ```

## 17.11 GET /groups/{group_id}/expenses

* **Purpose:** paginated, filterable expense history.
* **Auth:** required. **Authorisation:** member.
* **Query parameters:**

  | Name | Type | Default | Meaning |
  |---|---|---|---|
  | `category` | one of the 8 categories | — | exact category |
  | `member_id` | int | — | expenses this user paid for **or** has a share in |
  | `from_date`, `to_date` | `YYYY-MM-DD` | — | inclusive date range on `expense_date` |
  | `page` | int ≥ 1 | 1 | page number |
  | `page_size` | 1–100 | 20 | items per page |

* **Success 200:** `{"items": [ExpenseOut, ...], "total": 13, "page": 1, "page_size": 20}`,
  newest first (`expense_date DESC, id DESC`).
* **Database:** `COUNT` + page query with `LIMIT/OFFSET` + eager loads (Chapter 11.5).
* **Errors:** 400 `from_date must be before to_date`; 404; 422 invalid category / page.
* **Example:** `curl ".../groups/1/expenses?category=food&page=1&page_size=10" -H "Authorization: Bearer $TOKEN"`

## 17.12 GET /expenses/{expense_id}

* **Purpose:** one expense with its splits.
* **Auth:** required. **Authorisation:** member of the expense's group.
* **Success 200:** `ExpenseOut`.
* **Database:** `SELECT expenses WHERE id=?` + eager loads; membership lookup.
* **Errors:** 404 `Expense not found` (missing *or* not a member).
* **Example:** `curl .../expenses/17 -H "Authorization: Bearer $TOKEN"`

## 17.13 PATCH /expenses/{expense_id}

* **Purpose:** partially update an expense.
* **Auth:** required. **Authorisation:** member, and either the current payer or an admin.
* **Body:** any subset of `description, category, expense_date, notes, paid_by, amount_paise,
  split_type, participant_ids, splits`. If any of `amount_paise / split_type /
  participant_ids / splits` is present, the split is rebuilt, so `split_type` and the matching
  `participant_ids` or `splits` must be sent. Fields not sent are unchanged.

  ```json
  {"description": "Groceries + snacks", "amount_paise": 90000, "split_type": "equal",
   "participant_ids": [1, 2, 3]}
  ```

* **Validation:** same rules as create; new payer and participants must be members.
* **Success 200:** updated `ExpenseOut`.
* **Database:** one transaction: `UPDATE expenses ...`; `DELETE FROM expense_splits` (old rows)
  then flush; `INSERT INTO expense_splits` (new rows); `COMMIT`.
* **Errors:** 400 member checks or `<field> cannot be null`; 403 `Only the person who paid or a
  group admin can change this expense`; 404; 422 (e.g. `split_type is required when changing
  the amount or the split`).
* **Example:** `curl -X PATCH .../expenses/17 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"notes":"Big Bazaar"}'`

## 17.14 DELETE /expenses/{expense_id}

* **Purpose:** delete an expense and its splits.
* **Auth:** required. **Authorisation:** payer or admin.
* **Success:** 204 No Content.
* **Database:** `DELETE FROM expense_splits ...; DELETE FROM expenses WHERE id=?` in one
  transaction.
* **Errors:** 403; 404.
* **Example:** `curl -X DELETE .../expenses/17 -H "Authorization: Bearer $TOKEN"`

## 17.15 GET /groups/{group_id}/balances

* **Purpose:** every member's contribution, share, repayments and net balance.
* **Auth:** required. **Authorisation:** member.
* **Success 200:**

  ```json
  {"group_id": 3, "balances": [
    {"user_id": 8, "name": "Aman", "is_member": true, "total_paid_paise": 10000,
     "total_share_paise": 40000, "settlements_paid_paise": 0,
     "settlements_received_paise": 0, "net_balance_paise": -30000}, ...]}
  ```

  Sorted by name. The `net_balance_paise` values always sum to 0.
* **Database:** Chapter 11.7.
* **Errors:** 404.
* **Example:** `curl .../groups/1/balances -H "Authorization: Bearer $TOKEN"`

## 17.16 GET /groups/{group_id}/settlements/suggested

* **Purpose:** greedy settlement plan for current balances.
* **Auth:** required. **Authorisation:** member.
* **Success 200:**

  ```json
  {"group_id": 3, "settlements": [
    {"from_user_id": 7, "from_name": "Kiran", "to_user_id": 5, "to_name": "Sarvesh", "amount_paise": 46666},
    {"from_user_id": 7, "from_name": "Kiran", "to_user_id": 6, "to_name": "Rahul", "amount_paise": 6667},
    {"from_user_id": 8, "from_name": "Aman", "to_user_id": 6, "to_name": "Rahul", "amount_paise": 30000}]}
  ```

* **Database:** balance queries only; nothing is written.
* **Errors:** 404.
* **Example:** `curl .../groups/1/settlements/suggested -H "Authorization: Bearer $TOKEN"`

## 17.17 POST /groups/{group_id}/settlements

* **Purpose:** record a repayment made outside the app.
* **Auth:** required. **Authorisation:** member, and the caller must be the payer, the
  receiver, or an admin.
* **Body:** `{"paid_by": 8, "paid_to": 6, "amount_paise": 30000, "settled_at": "2026-11-10"}`
  (`settled_at` optional, defaults to today).
* **Validation:** `paid_by ≠ paid_to` (422); `0 < amount ≤ 1,000,000,000` (422); both are
  members (400); payer currently owes (400); receiver is currently owed (400);
  `amount ≤ min(payer's debt, receiver's credit)` (400) — computed under a row lock.
* **Success 201:**
  `{"id": 4, "group_id": 3, "paid_by": 8, "paid_by_name": "Aman", "paid_to": 6, "paid_to_name": "Rahul", "amount_paise": 30000, "settled_at": "2026-11-10", "created_at": "..."}`
* **Database:** `SELECT groups.id ... FOR UPDATE`; balance queries; `INSERT INTO settlements`;
  `COMMIT` (Chapter 16.6).
* **Errors:** 400 `Payer and receiver must both be group members`, `The payer does not owe
  anything in this group`, `The receiver is not owed anything in this group`, `Amount is more
  than the outstanding balance. Maximum allowed is Rs 300.00.`; 403 `Only the payer, the
  receiver or a group admin can record this settlement`; 404.
* **Example:** `curl -X POST .../groups/3/settlements -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"paid_by":8,"paid_to":6,"amount_paise":30000}'`

## 17.18 GET /groups/{group_id}/settlements

* **Purpose:** settlement history (newest first).
* **Auth:** required. **Authorisation:** member.
* **Success 200:** list of the settlement objects shown in 17.17.
* **Database:** Chapter 11.8.
* **Errors:** 404.
* **Example:** `curl .../groups/1/settlements -H "Authorization: Bearer $TOKEN"`

## 17.19 GET /dashboard

* **Purpose:** the caller's summary across all their groups.
* **Auth:** required. **Authorisation:** only the caller's groups are included.
* **Success 200:**

  ```json
  {"group_count": 2,
   "total_group_spending_paise": 12136950, "my_total_paid_paise": 7660000,
   "my_total_share_paise": 3064322, "my_net_balance_paise": 3943590,
   "group_balances": [{"group_id": 2, "group_name": "Goa Trip", "net_balance_paise": -70000}, ...],
   "recent_expenses": [{"id": 16, "group_id": 1, "group_name": "Room 204", "description": "...",
                        "amount_paise": 100000, "category": "groceries", "paid_by_name": "Sarvesh",
                        "expense_date": "2026-11-20", "my_share_paise": 33334}, ...],
   "category_breakdown": [{"category": "rent", "total_paise": 10500000}, ...],
   "monthly_summary": [{"month": "2026-06", "total_paise": 0, "my_share_paise": 0}, ...,
                       {"month": "2026-11", "total_paise": ..., "my_share_paise": ...}],
   "suggested_settlements": [{"group_id": 1, "group_name": "Room 204", "from_user_id": 3,
                              "from_name": "Kiran", "to_user_id": 1, "to_name": "Sarvesh",
                              "amount_paise": 2029937}, ...]}
  ```

  `suggested_settlements` contains only payments where the caller is payer or receiver;
  `monthly_summary` always has six months, oldest first.
* **Database:** queries in Chapters 11.6, 11.9, 11.10 plus per-group balance queries.
* **Errors:** 401.
* **Example:** `curl .../dashboard -H "Authorization: Bearer $TOKEN"`

## 17.20 GET /health

* **Purpose:** liveness check used during setup. **Auth:** none.
* **Success 200:** `{"status": "ok"}`. It does not query the database.

## 17.21 Using Swagger UI and Postman

1. Start the backend and open `http://localhost:8000/docs`.
2. Expand **POST /api/v1/auth/login** → *Try it out* → enter credentials → *Execute*.
3. Copy `access_token`, click **Authorize** (top right), paste it, *Authorize*.
4. Every endpoint can now be called from the page.

For Postman: *Import → Link* → `http://localhost:8000/openapi.json`, then set the collection's
*Authorization* to *Bearer Token* with `{{token}}`.

# Chapter 18 — Frontend and Backend Integration

## 18.1 React components and pages

| Screen (route) | Component | Backend calls |
|---|---|---|
| Login (`/login`) | `AuthPages.jsx:LoginPage` | `POST /auth/login` |
| Registration (`/register`) | `AuthPages.jsx:RegisterPage` | `POST /auth/register`, then login |
| Dashboard (`/dashboard`) | `DashboardPage.jsx` | `GET /dashboard` |
| Groups list (`/groups`) | `GroupsPages.jsx:GroupsPage` | `GET /groups` |
| Create group (`/groups/new`) | `GroupsPages.jsx:CreateGroupPage` | `POST /groups` |
| Group details / expense history (`/groups/:id`) | `GroupLayout` + `GroupExpensesPage.jsx` | `GET /groups/:id`, `GET /groups/:id/expenses` |
| Group members (`/groups/:id/members`) | `MembersPage.jsx` | `POST`/`DELETE` members |
| Add expense (`/groups/:id/expenses/new`) | `ExpensePages.jsx:AddExpensePage` + `ExpenseForm` | `POST /groups/:id/expenses` |
| Edit expense (`/expenses/:id/edit`) | `ExpensePages.jsx:EditExpensePage` + `ExpenseForm` | `GET /expenses/:id`, `GET /groups/:gid`, `PATCH /expenses/:id` |
| Expense details (`/expenses/:id`) | `ExpensePages.jsx:ExpenseDetailPage` | `GET /expenses/:id`, `DELETE /expenses/:id` |
| Balance overview (`/groups/:id/balances`) | `SettlementPages.jsx:BalancesPage` | `GET /groups/:id/balances` |
| Suggested settlements + record (`/groups/:id/settle`) | `SettlementPages.jsx:SettleUpPage` | `GET .../settlements/suggested`, `POST .../settlements` |
| Settlement history (`/groups/:id/settlements`) | `SettlementPages.jsx:SettlementHistoryPage` | `GET .../settlements` |
| Profile (`/profile`) | `ProfilePage.jsx` | `GET /groups` (user comes from context) |

Reusable pieces live in `components/ui.jsx` (Button, Card, Field, Spinner, LoadingState,
ErrorAlert, EmptyState, StatCard, Avatar, BalanceAmount, CategoryBadge, PageHeader).

## 18.2 React Router

`App.jsx` defines all routes. Two *layout routes* wrap groups of pages:

```jsx
<Route element={<ProtectedRoute />}>
  <Route element={<Layout />}>
    <Route path="/dashboard" element={<DashboardPage />} />
    ...
    <Route path="/groups/:groupId" element={<GroupLayout />}>
      <Route index element={<GroupExpensesPage />} />
      <Route path="members" element={<MembersPage />} />
      <Route path="balances" element={<BalancesPage />} />
      <Route path="settle" element={<SettleUpPage />} />
      <Route path="settlements" element={<SettlementHistoryPage />} />
      <Route path="expenses/new" element={<AddExpensePage />} />
    </Route>
    ...
```

`ProtectedRoute` checks authentication once for every page inside it; `Layout` draws the
navigation bar; `GroupLayout` loads the group once and passes it to whichever tab is active:

```jsx
<Outlet context={{ group, reloadGroup }} />
// in a tab:
const { group, reloadGroup } = useOutletContext()
```

## 18.3 Axios and the API base URL

`api/client.js` creates one Axios instance:

```javascript
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const client = axios.create({ baseURL: API_BASE_URL, timeout: 15000,
                              headers: { 'Content-Type': 'application/json' } })
```

`VITE_` variables are injected by Vite at build time from `frontend/.env`. `api/api.js` wraps
every endpoint in a small function so URLs are written once:

```javascript
export const settlementsApi = {
  balances: (groupId) => data(client.get(`/groups/${groupId}/balances`)),
  suggested: (groupId) => data(client.get(`/groups/${groupId}/settlements/suggested`)),
  list: (groupId) => data(client.get(`/groups/${groupId}/settlements`)),
  create: (groupId, body) => data(client.post(`/groups/${groupId}/settlements`, body)),
}
```

Query parameters are passed as an object and Axios encodes them:
`expensesApi.list(group.id, { category: 'food', page: 2, page_size: 10 })`.

## 18.4 Authentication token storage and interceptors

```javascript
client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginCall = error.config?.url?.includes('/auth/login')
    if (error.response?.status === 401 && getToken() && !isLoginCall) {
      setToken(null)
      window.dispatchEvent(new Event('settleup:logout'))
    }
    return Promise.reject(error)
  },
)
```

`getToken`/`setToken` wrap `localStorage` in `try/catch` so the app still works (without
persistence) if storage is blocked.

## 18.5 Protected routes

```jsx
export default function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <LoadingState label="Checking your session…" />
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
```

After login, `LoginPage` navigates to `location.state.from`, so a user who opened a deep link
returns to it. Route protection in the browser is only for user experience; real protection
is on the server.

## 18.6 Form handling

Forms are *controlled components*: each input's `value` comes from state and `onChange`
updates state. `ExpenseForm` adds:

* live equal-split preview and a custom-split "left to assign" counter,
* client-side checks that mirror the backend rules (for instant feedback),
* conversion of rupee strings to paise before sending,
* `noValidate` on the `<form>` so the app shows its own consistent messages.

## 18.7 Loading, empty and error states

Every data-fetching page follows the same pattern:

```jsx
const [data, setData] = useState(null)
const [error, setError] = useState('')
const load = useCallback(() => {
  setError('')
  dashboardApi.get().then(setData).catch((err) => setError(getErrorMessage(err)))
}, [])
useEffect(load, [load])

if (error) return <ErrorAlert message={error} onRetry={load} />
if (!data) return <LoadingState label="Loading dashboard…" />
```

Empty states (no groups, no expenses, nothing to settle) use `EmptyState` with a call to
action.

## 18.8 Error handling

`utils/format.js:getErrorMessage()` converts any Axios error into one sentence:

* network failure → "Cannot reach the server. Is the backend running?"
* `{"detail": "..."}` → the string itself,
* a 422 list → `"amount_paise: Input should be greater than 0"` (field path + message).

Buttons show a spinner and are disabled while a request is in flight, which also prevents most
accidental double submissions.

## 18.9 Dashboard data fetching

The dashboard makes **one** request (`GET /dashboard`); the backend assembles all numbers.
This keeps the page simple and avoids many round trips. Charts use Recharts with animations
turned off (`isAnimationActive={false}`) so they render completely even in background tabs and
screenshots. The y-axis converts paise to rupees only for display.

## 18.10 Responsive design

Tailwind's responsive prefixes (`sm:`, `md:`, `lg:`) change layouts by screen width: stat cards
go from 1 to 2 to 4 columns, the navigation collapses into a menu button below `md`, tables
scroll horizontally on small screens, and the expense form stacks its two cards vertically.
`docs/screenshots/15_mobile_dashboard.png` and `16_mobile_group.png` show the 390-px layout.

# Chapter 19 — Testing and Debugging

## 19.1 Types of testing used

| Type | What it checks | In SettleUp |
|---|---|---|
| Unit tests | One function in isolation | `test_settlement_algorithm.py`, `test_split_service.py`, `money.test.js` |
| Integration / API tests | Router + validation + ORM + real database together | `test_auth.py`, `test_groups.py`, `test_expenses.py`, `test_balances_settlements.py`, `test_dashboard.py` |
| Database tests | Constraints and cascades in PostgreSQL itself | `test_database_check_constraint_blocks_bad_rows`, `test_delete_expense_removes_splits`, `test_password_is_stored_hashed` |
| Component tests | React UI logic with a mocked API | `flows.test.jsx` |
| Manual end-to-end | Whole stack in a browser | Chapter 21 walkthrough, screenshots |

## 19.2 Pytest and fixtures

Pytest discovers `test_*.py` files and `test_*` functions; plain `assert` statements are
rewritten to show helpful failure messages. **Fixtures** provide reusable setup:

```python
@pytest.fixture(scope="session")
def migrated_db():
    """Drop everything and run 'alembic upgrade head' on the test database."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    yield

@pytest.fixture
def client(migrated_db):
    with TestClient(app) as test_client:
        yield test_client
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
```

* `migrated_db` runs **once per test session** and builds the schema with the real migration,
  so the migration itself is tested.
* `client` gives each test a `TestClient` (calls the app in-process, no server needed) and
  empties every table afterwards, so tests are independent.
* `make_user` registers and logs in a user and returns auth headers; `roommates` builds the
  four-person *Room 204* group used by many tests.

## 19.3 The test database

`conftest.py` reads `TEST_DATABASE_URL` and sets `DATABASE_URL` to it **before** importing the
app, so the application under test talks to `settleup_test`, never the development database.
Using real PostgreSQL rather than SQLite matters: SQLite would not behave the same way for
`FOR UPDATE`, some CHECK/foreign-key behaviour, `to_char`, or `BIGINT` semantics.

## 19.4 Example tests from the project

Balance formula with the problem-statement numbers:

```python
def test_balances_follow_the_formula(client, roommates):
    gid = setup_example(client, roommates)
    balances = balances_by_name(client, gid, roommates["Kiran"]["headers"])
    assert balances == {"Sarvesh": 45000, "Rahul": 5000, "Kiran": -15000, "Aman": -35000}
    assert sum(balances.values()) == 0
```

Property-style test of the algorithm on 25 random groups:

```python
@pytest.mark.parametrize("seed", range(25))
def test_random_groups_always_settle_with_at_most_n_minus_1_payments(seed):
    rng = random.Random(seed)
    size = rng.randint(2, 12)
    values = [rng.randint(-50_000, 50_000) for _ in range(size - 1)]
    values.append(-sum(values))  # force the total to zero
    balances = dict(enumerate(values, start=1))
    plan = suggest_settlements(balances)
    assert all(amount > 0 for _, _, amount in plan)
    assert all(v == 0 for v in apply(balances, plan).values())
    non_zero = sum(1 for v in balances.values() if v != 0)
    assert len(plan) <= max(non_zero - 1, 0)
```

Authorisation — an outsider cannot see anything:

```python
def test_non_member_cannot_create_or_read_expenses(client, roommates, make_user):
    outsider = make_user("Outsider")
    ...
    assert client.get(f"/api/v1/groups/{gid}/expenses", headers=outsider["headers"]).status_code == 404
    assert client.get(f"/api/v1/expenses/{created['id']}", headers=outsider["headers"]).status_code == 404
    assert client.delete(f"/api/v1/expenses/{created['id']}", headers=outsider["headers"]).status_code == 404
```

Frontend — a custom split that does not add up is blocked before any request:

```javascript
it('blocks a custom split whose shares do not add up', async () => {
  const onSubmit = vi.fn()
  render(<ExpenseForm members={members} currentUserId={1} submitLabel="Save" onSubmit={onSubmit} />)
  await userEvent.type(screen.getByLabelText('Description'), 'Electricity')
  await userEvent.type(screen.getByLabelText('Amount (₹)'), '1000')
  await userEvent.click(screen.getByRole('radio', { name: 'custom' }))
  await userEvent.type(screen.getByLabelText('Sarvesh'), '400')
  await userEvent.type(screen.getByLabelText('Rahul'), '300')
  expect(screen.getByText('₹300.00 left to assign')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Shares must add up to ₹1,000.00')
  expect(onSubmit).not.toHaveBeenCalled()
})
```

## 19.5 Important edge cases covered

Duplicate email (case-insensitive), wrong password vs unknown email, missing/tampered/expired
tokens, blank names, duplicate membership (including adding yourself), unregistered email,
non-admin actions, leaving with a balance, last member leaving, only admin leaving, equal split
remainders, custom split mismatch, zero/negative/fractional amounts, duplicate participants,
non-member payer/participant, metadata-only edits, edits that change the split, payer/admin-only
edit and delete, filter combinations and pagination, settlements that exceed debt or credit,
creditor trying to pay, debtor receiving, outsider in a settlement, partial settlements,
multiple-group isolation, rounding with odd amounts, and editing an expense after which
balances must change.

## 19.6 Test results

The latest full runs (logs in `docs/test-results/`):

* **Backend:** `97 passed` (72 test functions; one of them is parametrised over 25 random
  seeds).
* **Frontend:** `13 passed` in 2 files.

`docs/TEST_REPORT.md` lists every test case with expected result, actual result and status.

## 19.7 Debugging workflow

1. **Reproduce** with the smallest request (Swagger or a failing test).
2. **Read the status code and `detail`** — 401 vs 403 vs 404 vs 422 already narrows it down.
3. **Check the server log** — unexpected errors are logged with a stack trace by the global
   handler.
4. **Inspect the SQL** — `create_engine(..., echo=True)` or an engine event listener prints
   every statement (this is how Chapter 11's SQL was captured).
5. **Inspect the data** — `psql` queries against the dev database.
6. **Write a failing test**, fix, and keep the test.

## 19.8 Problems found and fixed during development

These are real issues encountered while building and verifying this project:

| Problem | Cause | Fix |
|---|---|---|
| `ImportError: DLL load failed ... filename or extension is too long` when importing SQLAlchemy | Windows 260-character path limit; the project folder was very deep | Create the virtual environment in a short path; README tip added |
| `npm install` peer-dependency conflict | Latest `@testing-library/jest-dom` expects a newer Vitest | Pinned compatible versions (jest-dom 6 with Vitest 3) |
| Deprecation warning from Starlette's test client | Newer Starlette prefers the `httpx2` package | Switched the test dependency to `httpx2` |
| Dashboard charts empty in background tabs and screenshots | Recharts animations never finished when the tab was not visible | `isAnimationActive={false}` |
| A stray scrollbar arrow on the group tab bar | `overflow-x-auto` plus a negative bottom margin created vertical overflow | Replaced the border trick with an inset shadow and `overflow-y-hidden` |
| 422 responses echoed the request body, including passwords | FastAPI's default validation error format includes `input` | Custom `RequestValidationError` handler returning only `loc`, `msg`, `type`; test added |
| A test name claimed greedy was non-optimal on an input where it is optimal | Wrong example | Renamed; added a real counter-example found by brute-force search |

# Chapter 20 — Running the Application

## 20.1 Prerequisites

* Python 3.11+ (`python --version`)
* Node.js 20+ and npm (`node --version`)
* PostgreSQL 16 (local install) **or** Docker Desktop
* Git

## 20.2 PostgreSQL setup

**Option A — Docker** (from the repository root):

```powershell
docker compose up -d
```

This starts PostgreSQL 16 on port 5432 with user/password `postgres`/`postgres` and creates
`settleup` and `settleup_test`.

**Option B — local install:** install PostgreSQL 16, then:

```powershell
psql -U postgres -c "CREATE DATABASE settleup;" -c "CREATE DATABASE settleup_test;"
```

## 20.3 Backend: dependencies and environment variables

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

| Variable | Example | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/settleup` | Development database |
| `TEST_DATABASE_URL` | `...:5432/settleup_test` | Wiped and rebuilt by the tests |
| `JWT_SECRET_KEY` | output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` | Signs tokens |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Token lifetime |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend origins |

If PowerShell refuses to run `Activate.ps1`, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `.\.venv\Scripts\python.exe`
directly.

## 20.4 Alembic migrations

```powershell
alembic upgrade head
```

Creates the six tables. `alembic current` shows the applied revision.

## 20.5 Start the backend

```powershell
python -m scripts.seed           # optional sample data
uvicorn app.main:app --reload
```

`--reload` restarts the server when code changes. Open `http://localhost:8000/docs`.

## 20.6 Start the frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## 20.7 First use

1. **Create the first user:** *Create an account* on the login page (or log in as a seeded
   user).
2. **Create the first group:** *Groups → + New group →* "Room 204". You are taken to the
   Members tab.
3. **Add members:** enter the email of another registered user → *Add member*.
4. **Add an expense:** *+ Add expense*, fill description and amount, choose who paid, choose
   equal or custom split → *Save expense*.
5. **Check balances:** *Balances* tab.
6. **Settle:** *Settle up* tab → *Record payment* next to a suggestion → *Save repayment*.
   The balance and suggestion list update immediately.

## 20.8 Running the tests

```powershell
cd backend;  pytest -v
cd frontend; npm test
```

## 20.9 Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Cannot reach the server" in the UI | Backend not running, or `VITE_API_BASE_URL` wrong |
| Browser console shows a CORS error | Frontend origin not in `CORS_ORIGINS` |
| `connection refused` on startup | PostgreSQL not running / wrong port in `DATABASE_URL` |
| `relation "users" does not exist` | `alembic upgrade head` not run |
| Logged out unexpectedly | Token expired (default 120 minutes) |
| "filename or extension is too long" | Project path too deep on Windows; move to e.g. `C:\dev\settleup` |

# Chapter 21 — Complete Project Walkthrough

This chapter replays a real session against the running application (backend on port 8000,
PostgreSQL 16). The requests were sent with a small script; responses and rows are copied from
that run. In this database the four roommates received ids 5–8 and the group id 3, because
other data already existed.

## 21.1 Account creation

`POST /auth/register` ×4 →

```json
{"id": 5, "name": "Sarvesh", "email": "sarvesh.demo@example.com", "created_at": "2026-11-20T12:01:17.693276Z"}
```

`POST /auth/login` returns `access_token` (beginning `eyJhbGciOiJIUzI1NiIs…`), `token_type`
and `user`.

Database: four rows in `users`. Only hashes are stored:

| id | name | email | password_hash (first 29 chars) |
|---|---|---|---|
| 5 | Sarvesh | sarvesh.demo@example.com | `$2b$12$rplAHlcKxkdVcv6VRRktU.` |
| 6 | Rahul | rahul.demo@example.com | `$2b$12$6Y2z/w96czG.TPmanUTbTe` |
| 7 | Kiran | kiran.demo@example.com | `$2b$12$z0/oft5Ah6b6Tqz6EWOO5u` |
| 8 | Aman | aman.demo@example.com | `$2b$12$6uHKTD0b5EvRfVeHhyJBLe` |

## 21.2 Group creation and member addition

Sarvesh: `POST /groups {"name": "Room 204 (walkthrough)"}` → 201. Then
`POST /groups/3/members` for Rahul, Kiran and Aman → 201 each.

| groups.id | name | created_by |
|---|---|---|
| 3 | Room 204 (walkthrough) | 5 |

| group_members.id | group_id | user_id | role |
|---|---|---|---|
| 8 | 3 | 5 | admin |
| 9 | 3 | 6 | member |
| 10 | 3 | 7 | member |
| 11 | 3 | 8 | member |

## 21.3 Expense 1 — equal split

Sarvesh pays ₹1,200 for groceries for all four:

```json
{"description": "Groceries", "amount_paise": 120000, "paid_by": 5, "category": "groceries",
 "expense_date": "2026-11-02", "split_type": "equal", "participant_ids": [5, 6, 7, 8]}
```

Response 201 with `splits` of 30000 each. Database: one `expenses` row (id 17) and four
`expense_splits` rows (57–60) of 30000. Balances now: Sarvesh +90000, others −30000 each.

## 21.4 Expense 2 — custom split

Rahul pays the ₹1,000 electricity bill, split by usage 400/300/200/100:

```json
{"description": "Electricity bill", "amount_paise": 100000, "paid_by": 6, "category": "utilities",
 "expense_date": "2026-11-05", "split_type": "custom",
 "splits": [{"user_id": 5, "share_amount_paise": 40000}, {"user_id": 6, "share_amount_paise": 30000},
            {"user_id": 7, "share_amount_paise": 20000}, {"user_id": 8, "share_amount_paise": 10000}]}
```

A deliberately wrong version (only one share of ₹400) was rejected:

```json
{"detail": [{"loc": ["body"],
             "msg": "Value error, Custom shares add up to 40000 paise but the expense is 100000 paise",
             "type": "value_error"}]}
```

(The run captured in this chapter happened before the custom 422 handler was added, so the
original response also contained an `input` echo of the body; the current version returns only
`loc`, `msg` and `type`, as shown.)

## 21.5 Expense 3 — equal split with a remainder

Aman pays ₹100 for snacks shared by Sarvesh, Rahul and Kiran. 10000 ÷ 3 = 3333 rem 1, so the
lowest id (Sarvesh, 5) gets the extra paisa.

| expense_splits.id | expense_id | user_id | share_amount_paise |
|---|---|---|---|
| 65 | 19 | 5 | 3334 |
| 66 | 19 | 6 | 3333 |
| 67 | 19 | 7 | 3333 |

All rows for the group:

| expenses.id | paid_by | description | amount_paise | split_type |
|---|---|---|---|---|
| 17 | 5 | Groceries | 120000 | equal |
| 18 | 6 | Electricity bill | 100000 | custom |
| 19 | 8 | Snacks | 10000 | equal |

## 21.6 Balance calculation

`GET /groups/3/balances`:

| Member | total_paid | total_share | net_balance |
|---|---:|---:|---:|
| Aman | 10000 | 40000 | **−30000** |
| Kiran | 0 | 53333 | **−53333** |
| Rahul | 100000 | 63333 | **+36667** |
| Sarvesh | 120000 | 73334 | **+46666** |

Check: 46666 + 36667 − 53333 − 30000 = 0.

## 21.7 Suggested settlement

`GET /groups/3/settlements/suggested`:

| From | To | Amount |
|---|---|---|
| Kiran | Sarvesh | ₹466.66 (46666) |
| Kiran | Rahul | ₹66.67 (6667) |
| Aman | Rahul | ₹300.00 (30000) |

Greedy trace: creditors [Sarvesh 46666, Rahul 36667], debtors [Kiran 53333, Aman 30000].
Kiran pays Sarvesh 46666 (Sarvesh done, Kiran has 6667 left); Kiran pays Rahul 6667 (Kiran
done, Rahul has 30000 left); Aman pays Rahul 30000 (both done). Three payments for four people
— the n − 1 bound.

## 21.8 Settlement recording

Aman first tries to record ₹400 to Rahul → **400**:
`{"detail": "Amount is more than the outstanding balance. Maximum allowed is Rs 300.00."}`

Then ₹300 → **201**:

```json
{"id": 4, "group_id": 3, "paid_by": 8, "paid_by_name": "Aman", "paid_to": 6,
 "paid_to_name": "Rahul", "amount_paise": 30000, "settled_at": "2026-11-10",
 "created_at": "2026-11-20T12:02:01.356061Z"}
```

Database: one row in `settlements` — `(4, group 3, paid_by 8, paid_to 6, 30000, 2026-11-10)`.

## 21.9 Updated balance

| Member | settlements_paid | settlements_received | net_balance |
|---|---:|---:|---:|
| Aman | 30000 | 0 | **0** |
| Kiran | 0 | 0 | −53333 |
| Rahul | 0 | 30000 | +6667 |
| Sarvesh | 0 | 0 | +46666 |

New suggestions: Kiran → Sarvesh 46666, Kiran → Rahul 6667.

## 21.10 Security checks in the same run

* An outsider (registered, not a member) requesting `GET /expenses/17` → **404**
  `{"detail": "Expense not found"}`.
* `GET /groups` with no token → **401** `{"detail": "Could not validate credentials"}`.

## 21.11 Summary of database changes

| Step | users | groups | group_members | expenses | expense_splits | settlements |
|---|---|---|---|---|---|---|
| Register ×4 | +4 | | | | | |
| Create group | | +1 | +1 (admin) | | | |
| Add 3 members | | | +3 | | | |
| Expense 1 | | | | +1 | +4 | |
| Expense 2 | | | | +1 | +4 | |
| Invalid expense | (nothing — rejected before any SQL) | | | | | |
| Expense 3 | | | | +1 | +3 | |
| Over-settlement | (nothing — rejected, transaction rolled back) | | | | | |
| Settlement | | | | | | +1 |

Balances and suggestions were never stored — each request recomputed them from these rows.

# Chapter 22 — Interview Preparation

Each question has a short **answer**, a **practical example**, how it relates to **SettleUp**,
and likely **follow-ups**. Answers describe the project as implemented — do not claim features
listed under future scope.

## 22.1 Python (25 questions)

**P1. Why does SettleUp use `int` instead of `float` for money?**
- **Answer:** Floats are binary approximations; decimal fractions like 0.1 cannot be represented exactly and errors accumulate. Python `int` is exact and unbounded.
- **Example:** `0.1 + 0.2 == 0.3` is `False`; `10 + 20 == 30` is `True`.
- **SettleUp:** every amount is an `int` of paise (`amount_paise = 120000`).
- **Follow-ups:** What about `Decimal`? (Also exact; integers were chosen for one representation across DB, Python and JS.)

**P2. What does `divmod(a, b)` return and where is it used?**
- **Answer:** A tuple `(a // b, a % b)` — quotient and remainder.
- **Example:** `divmod(1000, 3) == (333, 1)`.
- **SettleUp:** `split_equally` uses it to get each person's base share and the leftover paise.
- **Follow-ups:** How are leftover paise assigned? (One each to the lowest user ids.)

**P3. What is a list comprehension?**
- **Answer:** A concise expression that builds a list from an iterable, optionally filtered.
- **Example:** `[x * 2 for x in nums if x > 0]`.
- **SettleUp:** building `MemberOut` objects from query rows; `[s.user_id for s in splits]`.
- **Follow-ups:** Dict/set comprehensions? Generator expressions and memory use?

**P4. Difference between a list, a tuple, a set and a dict?**
- **Answer:** list = ordered, mutable; tuple = ordered, immutable; set = unordered unique items with fast membership; dict = key→value mapping.
- **Example:** `(debtor, creditor, amount)` tuples; `{user_id: balance}` dicts.
- **SettleUp:** set difference finds non-member participants; dicts hold sums per user.
- **Follow-ups:** Time complexity of `x in set` vs `x in list`? (O(1) average vs O(n).)

**P5. What does `dict.get(key, default)` do?**
- **Answer:** Returns the value for `key`, or `default` if missing, without raising `KeyError`.
- **Example:** `paid.get(user_id, 0)`.
- **SettleUp:** users with no payments have no key in the aggregated dictionaries.
- **Follow-ups:** `defaultdict` vs `get`?

**P6. What is a decorator?**
- **Answer:** A callable that takes a function (or class) and returns a modified or registered version; `@d` above `def f` means `f = d(f)`.
- **Example:** `@lru_cache` caches results.
- **SettleUp:** `@router.post(...)`, `@field_validator`, `@property`, `@dataclass`, `@pytest.fixture`.
- **Follow-ups:** Write a simple timing decorator. What does `functools.wraps` do?

**P7. What is `@property`?**
- **Answer:** Turns a method into a read-only computed attribute.
- **Example:** `row.net_balance_paise` (no parentheses).
- **SettleUp:** `BalanceRow.net_balance_paise`, `ExpenseUpdate.changes_split`.
- **Follow-ups:** Setter properties? Cost of recomputation?

**P8. What is a dataclass and why use it for `BalanceRow`?**
- **Answer:** `@dataclass` generates `__init__`, `__repr__` and `__eq__` from annotated fields.
- **Example:** `BalanceRow(user_id=1, name="Sarvesh", is_member=True)`.
- **SettleUp:** a lightweight container for per-user totals before conversion to Pydantic.
- **Follow-ups:** Dataclass vs Pydantic model vs NamedTuple?

**P9. What are type hints and are they enforced?**
- **Answer:** Annotations describing expected types. Python itself does not enforce them, but tools (mypy) and libraries (FastAPI, Pydantic, SQLAlchemy) read them.
- **Example:** `def get_membership(db: Session, group_id: int, user_id: int) -> GroupMember | None`.
- **SettleUp:** FastAPI converts `group_id: int` from the URL; Pydantic validates bodies.
- **Follow-ups:** `Optional[X]` vs `X | None`? What is `Literal`?

**P10. How does exception handling work in Python?**
- **Answer:** `try` runs code; `except` catches matching exceptions; `else` runs if none; `finally` always runs.
- **Example:** catching `IntegrityError` on duplicate email and returning 409.
- **SettleUp:** `get_db()` rolls back on exception and always closes the session in `finally`.
- **Follow-ups:** Why not catch bare `Exception` everywhere? Re-raising with `raise`?

**P11. What is a generator and what does `yield` do?**
- **Answer:** A function with `yield` returns an iterator that pauses at each `yield` and resumes later.
- **Example:** `def count(): yield 1; yield 2`.
- **SettleUp:** `get_db()` yields a session; code after `yield` runs after the response (cleanup).
- **Follow-ups:** Generator vs list memory use? Context managers built from generators?

**P12. What is the difference between `is` and `==`?**
- **Answer:** `==` compares values; `is` compares identity (same object).
- **Example:** `user is None` is the idiomatic None check.
- **SettleUp:** `if existing is not None: raise HTTPException(409, ...)`.
- **Follow-ups:** Why can `is` give surprising results for small ints/strings? (Interning.)

**P13. What is a module vs a package?**
- **Answer:** A module is a `.py` file; a package is a directory of modules (traditionally with `__init__.py`).
- **Example:** `app.services.split_service`.
- **SettleUp:** `app/models/__init__.py` imports all models so Alembic sees every table.
- **Follow-ups:** Circular imports and how string relationship names (`"Group"`) avoid them.

**P14. What is `lru_cache` used for in `config.py`?**
- **Answer:** Memoises a function's return value, so `get_settings()` builds `Settings` once.
- **Example:** `@lru_cache def get_settings(): return Settings()`.
- **SettleUp:** environment and `.env` are read once at startup.
- **Follow-ups:** How would tests override settings? (Environment variables before import.)

**P15. What are f-strings?**
- **Answer:** String literals prefixed with `f` that evaluate `{expressions}`.
- **Example:** `f"Rs {paise // 100}.{paise % 100:02d}"`.
- **SettleUp:** formatting the maximum allowed settlement message without floats.
- **Follow-ups:** What does `:02d` mean? (Zero-pad to width 2.)

**P16. What is `//` vs `/` vs `%`?**
- **Answer:** `/` true division (float), `//` floor division (int for ints), `%` remainder.
- **Example:** `12550 // 100 == 125`, `12550 % 100 == 50`.
- **SettleUp:** displaying paise as rupees without floating point.
- **Follow-ups:** Behaviour with negative numbers? (`-7 // 2 == -4`.)

**P17. What is `sorted(..., key=...)` and how are ties broken in the settlement algorithm?**
- **Answer:** `key` maps each item to a sort key; tuples sort element by element.
- **Example:** `key=lambda item: (-item[1], item[0])` sorts by amount descending, then id ascending.
- **SettleUp:** makes suggestions deterministic.
- **Follow-ups:** Is Python's sort stable? (Yes — Timsort.) Complexity? (O(n log n).)

**P18. What is a lambda?**
- **Answer:** An anonymous single-expression function.
- **Example:** `lambda row: (row.name.lower(), row.user_id)`.
- **SettleUp:** sort keys in balance and settlement services.
- **Follow-ups:** When to prefer `def`? (Anything non-trivial or reused.)

**P19. What does `enumerate` do?**
- **Answer:** Yields `(index, item)` pairs.
- **Example:** `for index, user_id in enumerate(ordered):`.
- **SettleUp:** the first `remainder` users get +1 paisa.
- **Follow-ups:** `zip`? `enumerate(start=1)`?

**P20. What are `*args` and `**kwargs`?**
- **Answer:** Collect extra positional arguments into a tuple and keyword arguments into a dict.
- **Example:** `def add_expense(client, group_id, headers, **overrides)`.
- **SettleUp:** test helper overrides any field of the default expense body.
- **Follow-ups:** Unpacking with `{**a, **b}`?

**P21. Is the backend code `async`? Why or why not?**
- **Answer:** No. Endpoints are plain `def`, so FastAPI runs them in a thread pool; the SQLAlchemy session is synchronous/blocking.
- **Example:** an `async def` endpoint calling a blocking DB driver would freeze the event loop.
- **SettleUp:** simpler code with correct concurrency for this scale.
- **Follow-ups:** What would change for async? (`AsyncSession`, async driver, `await` on queries.)

**P22. What is a virtual environment?**
- **Answer:** An isolated Python installation with its own packages.
- **Example:** `python -m venv .venv`.
- **SettleUp:** pinned dependencies in `requirements.txt` installed into `.venv`.
- **Follow-ups:** Why pin versions? (Reproducible builds.)

**P23. What does `set(a) - set(b)` compute?**
- **Answer:** Elements of `a` not in `b`.
- **Example:** `{1, 2, 9} - {1, 2, 3} == {9}`.
- **SettleUp:** participants who are not group members → 400 error listing them.
- **Follow-ups:** Union `|`, intersection `&` — used when collecting all user ids for balances.

**P24. What are `__repr__` and other dunder methods?**
- **Answer:** Special methods Python calls for built-in behaviour (`__init__`, `__repr__`, `__eq__`, `__len__`).
- **Example:** `User.__repr__` returns `<User id=1 email='...'>`.
- **SettleUp:** helpful debugging output for models.
- **Follow-ups:** `__str__` vs `__repr__`?

**P25. How would you make `split_equally` robust against bad input?**
- **Answer:** Validate early and raise clear errors; keep it pure for testing.
- **Example:** raises `ValueError` for empty participants or non-positive amount.
- **SettleUp:** Pydantic validates first; the function still defends itself.
- **Follow-ups:** Property-based testing (e.g. Hypothesis) for split invariants?

**P26. What is the difference between mutable and immutable default arguments?**
- **Answer:** Default values are evaluated once; a mutable default (like `[]`) is shared across calls — a classic bug.
- **Example:** `def f(x=[]): x.append(1)` grows every call.
- **SettleUp:** uses `None` defaults (`participant_ids: list[int] | None = None`) instead.
- **Follow-ups:** How does Pydantic handle `Field(default_factory=list)`?

## 22.2 FastAPI and REST (35 questions)

**F1. What is FastAPI and what is it built on?**
- **Answer:** A Python API framework on Starlette (ASGI, routing, middleware) and Pydantic (validation).
- **Example:** `app = FastAPI(title="SettleUp API")`.
- **SettleUp:** all endpoints, validation and docs.
- **Follow-ups:** ASGI vs WSGI?

**F2. What happens internally when a request reaches FastAPI?**
- **Answer:** Uvicorn parses HTTP → middleware (CORS) → router matches path/method → dependencies resolved → path/query/body parsed and validated → endpoint runs → return value validated against `response_model` → serialised to JSON → middleware → response.
- **Example:** `GET /groups/1/balances` (Chapter 2.6).
- **SettleUp:** failures at each stage map to 401/404/422.
- **Follow-ups:** Where would logging middleware go?

**F3. How does FastAPI dependency injection work?**
- **Answer:** Parameters with `Depends(func)` are resolved before the endpoint; dependencies can depend on others; results are cached per request; generator dependencies get teardown.
- **Example:** `current_user: User = Depends(get_current_user)`.
- **SettleUp:** `get_db` and `get_current_user` on every protected endpoint.
- **Follow-ups:** `dependency_overrides` in tests? Router-level dependencies?

**F4. Why are group membership checks plain functions rather than `Depends`?**
- **Answer:** They need the path's `group_id` and return the membership row used later (role checks); calling them explicitly is clear.
- **Example:** `caller = require_group_member(db, group_id, current_user)`.
- **SettleUp:** consistent 404/403 behaviour.
- **Follow-ups:** How could you write it as a dependency? (A dependency taking `group_id: int` path param.)

**F5. Path vs query parameters?**
- **Answer:** Path identifies a resource (`/groups/{group_id}`); query refines a collection (`?category=food`).
- **SettleUp:** expense filters and pagination are query parameters.
- **Follow-ups:** Validation of query params with `Query(ge=1, le=100)`.

**F6. How is the request body validated?**
- **Answer:** A Pydantic model parameter is parsed from JSON; field constraints and validators run; errors → 422.
- **Example:** `ExpenseCreate` with `amount_paise: int = Field(gt=0)`.
- **SettleUp:** custom split totals checked in a model validator.
- **Follow-ups:** `field_validator` vs `model_validator`?

**F7. What is `response_model` for?**
- **Answer:** Validates/filters output and documents it.
- **SettleUp:** `UserOut` has no `password_hash`, so it can never leak.
- **Follow-ups:** `response_model_exclude_none`? Returning ORM objects with `from_attributes=True`.

**F8. What is the difference between 401 and 403?**
- **Answer:** 401 = not authenticated (no/invalid credentials); 403 = authenticated but not allowed.
- **SettleUp:** missing token → 401; non-admin adding a member → 403.
- **Follow-ups:** Why does SettleUp use 404 for non-members?

**F9. Why 404 instead of 403 for non-members?**
- **Answer:** To avoid revealing whether a group/expense exists (prevents id enumeration).
- **SettleUp:** `require_group_member` and `_get_expense_for_member`.
- **Follow-ups:** Trade-off for debugging? (Clearer errors vs privacy.)

**F10. What is 422 and when does SettleUp return it?**
- **Answer:** Unprocessable Content — syntactically valid JSON that fails validation.
- **SettleUp:** zero amount, invalid category, custom shares not adding up, payer equals receiver.
- **Follow-ups:** Why a custom 422 handler? (Avoid echoing passwords.)

**F11. When does SettleUp return 400 vs 422?**
- **Answer:** 422 for input-shape/self-contained rules (Pydantic); 400 for business rules needing database state (non-member payer, settlement above debt).
- **Follow-ups:** Is 409 better for some 400s? (Debatable; documented choice.)

**F12. What is 409 used for?**
- **Answer:** Conflict with current state — duplicate email, duplicate membership, and database integrity errors.
- **Follow-ups:** Race conditions that produce 409 via the UNIQUE constraint.

**F13. Why 201 and 204?**
- **Answer:** 201 Created for successful creation (with body); 204 No Content for successful deletion (no body).
- **SettleUp:** `status_code=status.HTTP_201_CREATED` on POSTs; DELETE returns `Response(status_code=204)`.
- **Follow-ups:** Should 201 include a `Location` header? (REST-ideal; not implemented.)

**F14. PUT vs PATCH — which does SettleUp use and why?**
- **Answer:** PATCH: clients send only changed fields; the router checks `payload.model_fields_set`.
- **SettleUp:** editing just the notes doesn't resend the split.
- **Follow-ups:** How do you distinguish "not sent" from "sent as null"? (`model_fields_set`.)

**F15. What is idempotency?**
- **Answer:** Repeating a request has the same effect as doing it once. GET/PUT/DELETE are idempotent; POST is not.
- **SettleUp:** double-submitting "Save repayment" could create two settlements, but the row lock + debt validation rejects the second if it would over-settle; buttons are disabled while saving.
- **Follow-ups:** Idempotency keys?

**F16. What is REST?**
- **Answer:** An architectural style: resources at URLs, uniform methods, stateless requests, representations (JSON).
- **SettleUp:** `/groups/{id}/expenses`, stateless JWT auth, `/api/v1`.
- **Follow-ups:** Is SettleUp fully RESTful? (No HATEOAS links — pragmatic REST.)

**F17. Why version the API (`/api/v1`)?**
- **Answer:** To make breaking changes in `/v2` without breaking existing clients.
- **Follow-ups:** Header vs URL versioning?

**F18. What is CORS and why is it needed here?**
- **Answer:** Browsers block cross-origin requests unless the server allows the origin. The frontend (5173) and API (8000) are different origins.
- **SettleUp:** `CORSMiddleware` with `allow_origins` from `CORS_ORIGINS`.
- **Follow-ups:** Preflight `OPTIONS` requests; why not `allow_origins=["*"]` with credentials?

**F19. What is a preflight request?**
- **Answer:** An automatic `OPTIONS` request the browser sends before "non-simple" requests (e.g. JSON body, `Authorization` header) to ask permission.
- **SettleUp:** handled by `CORSMiddleware`.
- **Follow-ups:** Which headers are allowed? (`Authorization`, `Content-Type`.)

**F20. What is middleware?**
- **Answer:** Code wrapping every request/response.
- **SettleUp:** CORS only.
- **Follow-ups:** How would you add request timing or request-id logging?

**F21. How does Swagger UI get generated?**
- **Answer:** FastAPI builds an OpenAPI schema from routes, type hints and models, served at `/openapi.json`; `/docs` renders it.
- **SettleUp:** `HTTPBearer` adds the Authorize button.
- **Follow-ups:** Importing into Postman.

**F22. What is Pydantic `from_attributes`?**
- **Answer:** Lets a model read data from object attributes (ORM objects) instead of only dicts.
- **SettleUp:** `UserOut.model_validate(user)` in login.
- **Follow-ups:** What was it called in Pydantic v1? (`orm_mode`.)

**F23. How does `EmailStr` validate emails?**
- **Answer:** Uses the `email-validator` package to check syntax (and normalise).
- **SettleUp:** registration, login, add member; then lower-cased by a validator.
- **Follow-ups:** Does it verify the mailbox exists? (No.)

**F24. How are global exception handlers registered?**
- **Answer:** `@app.exception_handler(ExcType)` returning a response.
- **SettleUp:** `RequestValidationError` → trimmed 422; `IntegrityError` → 409; `Exception` → 500.
- **Follow-ups:** Why hide internal error details? (Information disclosure.)

**F25. What is the request–response lifecycle of a POST that fails validation?**
- **Answer:** Body parsing → Pydantic raises → `RequestValidationError` handler → 422; the endpoint and database are never touched.
- **SettleUp:** invalid custom split in the walkthrough.
- **Follow-ups:** Is the DB session still opened? (Dependencies may already have run; it is closed in `finally`.)

**F26. How are query parameters with `Literal` types validated?**
- **Answer:** Values outside the literal set produce 422.
- **SettleUp:** `?category=invalid` → 422 (tested).
- **Follow-ups:** Using `Enum` instead.

**F27. How does pagination work in SettleUp?**
- **Answer:** `page` and `page_size` → `OFFSET (page-1)*page_size LIMIT page_size`, plus a `COUNT` for `total`.
- **Follow-ups:** Keyset pagination for large tables; consistency when rows are inserted between pages.

**F28. How would you document error responses in OpenAPI?**
- **Answer:** `responses={404: {"model": ErrorModel}}` on the decorator.
- **SettleUp:** not added — errors are documented in this guide instead.
- **Follow-ups:** Why it helps client generation.

**F29. What is `TestClient`?**
- **Answer:** Starlette's in-process client that calls the ASGI app without a network server.
- **SettleUp:** all API tests.
- **Follow-ups:** Why `with TestClient(app)`? (Runs lifespan events.)

**F30. What is Uvicorn?**
- **Answer:** An ASGI server that runs the FastAPI app.
- **SettleUp:** `uvicorn app.main:app --reload`.
- **Follow-ups:** Workers in production (`--workers 4` / Gunicorn).

**F31. How does FastAPI handle sync endpoints concurrently?**
- **Answer:** It runs them in a thread pool so multiple requests proceed in parallel.
- **SettleUp:** all endpoints are sync.
- **Follow-ups:** Thread-pool size and DB connection pool size relationship.

**F32. What does `HTTPBearer(auto_error=False)` change?**
- **Answer:** Missing header returns `None` instead of an automatic 403, letting the app return 401.
- **Follow-ups:** `OAuth2PasswordBearer` alternative (form-based login).

**F33. How would you rate-limit login?**
- **Answer:** Middleware or a library (e.g. slowapi) keyed by IP/email, or at a reverse proxy.
- **SettleUp:** **not implemented** — future scope.
- **Follow-ups:** Account lockout trade-offs.

**F34. What are the client's responsibilities vs the server's?**
- **Answer:** Client: UX, quick validation, formatting. Server: authoritative validation, authorisation, calculations.
- **SettleUp:** split preview in the browser; real split on the server.
- **Follow-ups:** Why never trust the client?

**F35. How is the API made usable from Postman?**
- **Answer:** Import `/openapi.json`, set Bearer token auth.
- **Follow-ups:** Environment variables for base URL and token.

**F36. What is the difference between `Query`, `Path` and `Body`?**
- **Answer:** Markers telling FastAPI where a parameter comes from and adding validation/docs.
- **SettleUp:** `Query(default=20, ge=1, le=100)` for `page_size`.
- **Follow-ups:** Embedding a single body field with `Body(embed=True)`.

## 22.3 SQL and PostgreSQL (50 questions)

**S1. Why PostgreSQL instead of MongoDB?**
- **Answer:** The data is relational (many-to-many memberships and participants) and needs joins, aggregates, foreign keys, CHECKs and transactions. PostgreSQL enforces integrity in the database; MongoDB would need that logic in application code or duplicated documents.
- **Example:** "total owed by Kiran in group 1" is one JOIN + SUM.
- **SettleUp:** six normalised tables with FK/UNIQUE/CHECK constraints.
- **Follow-ups:** When would a document store fit better? (Flexible, self-contained documents with few relationships.)

**S2. What is a primary key?**
- **Answer:** A column (or set) that uniquely identifies a row; NOT NULL + UNIQUE, indexed automatically.
- **SettleUp:** `id SERIAL PRIMARY KEY` on every table.
- **Follow-ups:** Surrogate vs natural keys; composite primary keys.

**S3. What is a foreign key?**
- **Answer:** A column whose values must match a primary (or unique) key in another table.
- **SettleUp:** `expenses.group_id → groups.id`.
- **Follow-ups:** What happens on delete? (CASCADE / RESTRICT / SET NULL.)

**S4. Primary key vs foreign key?**
- **Answer:** PK identifies rows in its own table; FK references a PK elsewhere and enforces that the referenced row exists. A table has one PK but can have many FKs.
- **SettleUp:** `settlements` has one PK and three FKs.
- **Follow-ups:** Can an FK be NULL? (Yes, unless NOT NULL — all of SettleUp's are NOT NULL.)

**S5. What is a UNIQUE constraint and how is it different from a PK?**
- **Answer:** Ensures no duplicate values; a table can have many; allows NULLs (PostgreSQL treats NULLs as distinct by default).
- **SettleUp:** `users.email`, `(group_id, user_id)`, `(expense_id, user_id)`.
- **Follow-ups:** `NULLS NOT DISTINCT` (PostgreSQL 15+).

**S6. What is a CHECK constraint? Give examples.**
- **Answer:** A boolean condition every row must satisfy.
- **SettleUp:** `amount_paise > 0`, `paid_by <> paid_to`, `role IN ('admin','member')`.
- **Follow-ups:** Why can't CHECK enforce "splits sum to amount"? (Cross-row.)

**S7. What does NOT NULL do?**
- **Answer:** Rejects missing values.
- **SettleUp:** all columns except `expenses.notes`.
- **Follow-ups:** NULL semantics in comparisons (`NULL = NULL` is unknown).

**S8. What are data types used for money and why BIGINT?**
- **Answer:** BIGINT paise: exact integer arithmetic, no overflow at realistic values (INTEGER would cap at ≈₹2.1 crore).
- **Follow-ups:** NUMERIC vs BIGINT; never FLOAT.

**S9. TIMESTAMP vs TIMESTAMPTZ vs DATE?**
- **Answer:** TIMESTAMPTZ stores an absolute instant (UTC internally); TIMESTAMP has no zone; DATE is a calendar day.
- **SettleUp:** `created_at` TIMESTAMPTZ; `expense_date` and `settled_at` DATE.
- **Follow-ups:** Why is DATE right for "when the bill happened"?

**S10. What is a JOIN? Types?**
- **Answer:** Combines rows of two tables on a condition. INNER (matches only), LEFT/RIGHT (all of one side), FULL (all of both), CROSS (Cartesian).
- **SettleUp:** INNER for members (11.2); LEFT for "my share" on the dashboard (11.6).
- **Follow-ups:** Difference of putting a condition in ON vs WHERE for LEFT JOIN.

**S11. Why does the dashboard use a LEFT JOIN?**
- **Answer:** To keep expenses where the user has no split row; their share becomes NULL → `COALESCE(..., 0)`.
- **Follow-ups:** What breaks if `user_id = :me` is moved to WHERE? (Turns into an inner join.)

**S12. What are aggregate functions?**
- **Answer:** Functions over many rows returning one value: COUNT, SUM, AVG, MIN, MAX.
- **SettleUp:** SUM for balances, COUNT for pagination totals.
- **Follow-ups:** COUNT(*) vs COUNT(column) (NULL handling).

**S13. What does GROUP BY do?**
- **Answer:** Groups rows by column values so aggregates are computed per group.
- **SettleUp:** `SELECT paid_by, SUM(amount_paise) ... GROUP BY paid_by`.
- **Follow-ups:** Rule: selected columns must be grouped or aggregated.

**S14. WHERE vs HAVING?**
- **Answer:** WHERE filters rows before grouping; HAVING filters groups after aggregation.
- **Example:** members whose total share > ₹5,000: `HAVING SUM(share_amount_paise) > 500000`.
- **Follow-ups:** Can HAVING be used without GROUP BY? (Yes, treats all rows as one group.)

**S15. Why `COALESCE(SUM(x), 0)`?**
- **Answer:** SUM of no rows is NULL.
- **SettleUp:** group total spending when a group has no expenses.
- **Follow-ups:** `COALESCE` vs `IFNULL`/`NVL` in other databases.

**S16. What is a subquery? Correlated vs non-correlated?**
- **Answer:** A query inside another. Non-correlated runs independently; correlated references the outer row.
- **SettleUp:** `group_id IN (SELECT group_id FROM group_members WHERE user_id = :me)` (non-correlated).
- **Follow-ups:** Rewrite as a JOIN or `EXISTS`.

**S17. IN vs EXISTS?**
- **Answer:** Both test membership in a subquery; `EXISTS` stops at the first match and handles NULLs more predictably; PostgreSQL often plans them similarly (semi-join).
- **SettleUp:** member filter uses `id IN (SELECT expense_id ...)`.
- **Follow-ups:** `NOT IN` with NULLs pitfall.

**S18. What is a derived table?**
- **Answer:** A subquery in FROM treated like a table.
- **SettleUp:** member counts per group joined into the group list (11.3).
- **Follow-ups:** CTEs (`WITH`) as a readable alternative.

**S19. What is a CTE?**
- **Answer:** `WITH name AS (SELECT ...) SELECT ... FROM name` — a named subquery; can be recursive.
- **Example:** compute per-user deltas in a CTE, then SUM.
- **SettleUp:** not used in code; the single-query balance example could be written as a CTE.
- **Follow-ups:** Are CTEs materialised in PostgreSQL 12+? (Inlined unless `MATERIALIZED`.)

**S20. What is UNION vs UNION ALL?**
- **Answer:** UNION removes duplicates (extra sort/hash); UNION ALL keeps all rows.
- **SettleUp:** the single-query balance (11.7) must use UNION ALL — two identical deltas are both real money.
- **Follow-ups:** Column count/type rules.

**S21. Write SQL for each member's net balance in one query.**
- **Answer:** UNION ALL signed deltas (paid +, share −, settlements paid +, received −), then `GROUP BY user_id` (Chapter 11.7).
- **Follow-ups:** Include members with no activity? (LEFT JOIN from group_members.)

**S22. What is an index?**
- **Answer:** A data structure (B-tree by default) that speeds lookups/sorts on columns at the cost of storage and write time.
- **SettleUp:** `ix_expenses_group_id_expense_date`, `ix_group_members_user_id`, etc.
- **Follow-ups:** Hash, GIN, BRIN index types.

**S23. How does a composite index work?**
- **Answer:** Sorted by the first column, then the second within it. Usable for queries on a leftmost prefix.
- **SettleUp:** `(group_id, expense_date)` serves "group 1 ordered by date"; `(group_id, user_id)` serves membership checks and "members of group".
- **Follow-ups:** Would `(expense_date, group_id)` serve the same queries? (No.)

**S24. Why not index every column?**
- **Answer:** Each index slows INSERT/UPDATE/DELETE and uses space; unused indexes are pure cost.
- **SettleUp:** indexes only on filtered/joined/sorted columns.
- **Follow-ups:** How to find unused indexes? (`pg_stat_user_indexes`.)

**S25. Does PostgreSQL index foreign keys automatically?**
- **Answer:** No — only PKs and UNIQUE constraints get automatic indexes.
- **SettleUp:** explicit indexes added on FK columns used in queries (`user_id`, `paid_by`, `created_by`).
- **Follow-ups:** Why FK indexes matter for deletes on the parent.

**S26. What is EXPLAIN / EXPLAIN ANALYZE?**
- **Answer:** Shows the query plan (and with ANALYZE, actual timings by running it).
- **Follow-ups:** Seq Scan vs Index Scan vs Bitmap Heap Scan; why the planner may ignore an index on tiny tables.

**S27. What is a transaction?**
- **Answer:** A unit of work that commits or rolls back entirely.
- **SettleUp:** expense + splits; settlement validation + insert.
- **Follow-ups:** Savepoints.

**S28. What are ACID properties?**
- **Answer:** Atomicity, Consistency, Isolation, Durability (Chapter 7.18).
- **Follow-ups:** Which one does WAL provide? (Durability, and helps atomicity.)

**S29. What isolation levels does PostgreSQL support?**
- **Answer:** Read Committed (default), Repeatable Read, Serializable (Read Uncommitted behaves as Read Committed).
- **SettleUp:** default Read Committed + explicit `FOR UPDATE` where needed.
- **Follow-ups:** Phantom reads; serialization failures and retries.

**S30. What does `SELECT ... FOR UPDATE` do?**
- **Answer:** Locks the selected rows until the transaction ends; other transactions trying to lock/update them wait.
- **SettleUp:** locks the group row while validating and inserting a settlement.
- **Follow-ups:** `NOWAIT`, `SKIP LOCKED`; deadlocks.

**S31. What is MVCC?**
- **Answer:** Multi-Version Concurrency Control: writers create new row versions; readers see a consistent snapshot without blocking writers.
- **Follow-ups:** VACUUM and dead tuples.

**S32. What is a deadlock and how could SettleUp hit one?**
- **Answer:** Two transactions each wait for a lock the other holds. PostgreSQL detects it and aborts one.
- **SettleUp:** each settlement locks a single group row, so two settlements cannot deadlock with each other.
- **Follow-ups:** Consistent lock ordering as prevention.

**S33. What does ON DELETE CASCADE do? RESTRICT?**
- **Answer:** CASCADE deletes child rows with the parent; RESTRICT refuses to delete a parent with children.
- **SettleUp:** group → expenses/settlements/memberships CASCADE; user references RESTRICT.
- **Follow-ups:** SET NULL; NO ACTION vs RESTRICT timing.

**S34. What is SERIAL? Identity columns?**
- **Answer:** SERIAL = INTEGER with a sequence default. `GENERATED ... AS IDENTITY` is the SQL-standard newer alternative.
- **SettleUp:** SERIAL (generated by SQLAlchemy for `Mapped[int]` PKs).
- **Follow-ups:** Gaps in sequences (rolled-back inserts, deletes) — visible in the walkthrough ids.

**S35. Why do ids have gaps?**
- **Answer:** Sequences are not transactional; rolled-back inserts and deleted rows leave gaps.
- **SettleUp:** expense ids jumped because test/demo rows were created and deleted.
- **Follow-ups:** Never use ids as counts.

**S36. What is `RETURNING`?**
- **Answer:** PostgreSQL clause returning values from inserted/updated rows.
- **SettleUp:** SQLAlchemy uses `RETURNING expenses.id, created_at, updated_at` to get generated values.
- **Follow-ups:** Saves a round trip vs `SELECT currval`.

**S37. How do you get monthly totals?**
- **Answer:** Group by a month expression: `to_char(expense_date, 'YYYY-MM')` or `date_trunc('month', expense_date)`.
- **SettleUp:** dashboard monthly chart (11.9).
- **Follow-ups:** Filling empty months (generate_series vs application code — SettleUp fills in Python).

**S38. How do you get the top category by spending?**
- **Answer:** `SELECT category, SUM(amount_paise) FROM expenses WHERE ... GROUP BY category ORDER BY 2 DESC LIMIT 1;`
- **Follow-ups:** Ties (`RANK()` window function).

**S39. What are window functions? Give an example on this schema.**
- **Answer:** Aggregates over a "window" of rows without collapsing them.
- **Example:** running total per group: `SUM(amount_paise) OVER (PARTITION BY group_id ORDER BY expense_date)`.
- **SettleUp:** not used in code — good extension for a "spending over time" chart.
- **Follow-ups:** ROW_NUMBER vs RANK vs DENSE_RANK.

**S40. How does LIMIT/OFFSET pagination work and what are its drawbacks?**
- **Answer:** Skips OFFSET rows then returns LIMIT; deep pages still scan skipped rows, and inserts between requests shift pages.
- **SettleUp:** OFFSET pagination with stable ordering (`expense_date DESC, id DESC`).
- **Follow-ups:** Keyset (seek) pagination.

**S41. How do parameterised queries prevent SQL injection?**
- **Answer:** Values are sent separately from the SQL text, so they can never be interpreted as SQL.
- **SettleUp:** every SQLAlchemy query binds parameters (`%(email_1)s`).
- **Follow-ups:** Where could injection still happen? (Building SQL strings with f-strings — not done.)

**S42. What is a schema in PostgreSQL?**
- **Answer:** A namespace for tables inside a database (default `public`).
- **SettleUp:** tests `DROP SCHEMA public CASCADE` then re-run migrations.
- **Follow-ups:** Multi-tenant designs with schemas.

**S43. What is the difference between DELETE, TRUNCATE and DROP?**
- **Answer:** DELETE removes rows (row by row, fires triggers, can filter); TRUNCATE empties tables fast; DROP removes the table itself.
- **SettleUp:** tests TRUNCATE all tables `RESTART IDENTITY CASCADE` after each test.
- **Follow-ups:** Is TRUNCATE transactional in PostgreSQL? (Yes.)

**S44. What is a view?**
- **Answer:** A stored query that behaves like a table.
- **Example:** `CREATE VIEW member_balances AS <UNION ALL balance query>`.
- **SettleUp:** not used; balances are computed in the service.
- **Follow-ups:** Materialised views and refresh.

**S45. How would you find users who are in no group?**
- **Answer:** `SELECT u.* FROM users u LEFT JOIN group_members gm ON gm.user_id = u.id WHERE gm.id IS NULL;` (anti-join) or `NOT EXISTS`.
- **Follow-ups:** Performance with indexes on `group_members.user_id`.

**S46. How would you find expenses whose splits do not add up (data audit)?**
- **Answer:**
  `SELECT e.id FROM expenses e JOIN expense_splits s ON s.expense_id = e.id GROUP BY e.id, e.amount_paise HAVING SUM(s.share_amount_paise) <> e.amount_paise;`
- **SettleUp:** should always return zero rows.
- **Follow-ups:** Could a trigger enforce it? (A deferred constraint trigger could.)

**S47. What is a trigger?**
- **Answer:** A function the database runs automatically on INSERT/UPDATE/DELETE.
- **SettleUp:** none; `updated_at` is set by SQLAlchemy's `onupdate`.
- **Follow-ups:** Pros/cons of business logic in triggers.

**S48. How does PostgreSQL guarantee durability?**
- **Answer:** Changes are written to the write-ahead log and flushed to disk on COMMIT before success is reported; after a crash the WAL is replayed.
- **Follow-ups:** `synchronous_commit`, replication.

**S49. What is connection pooling?**
- **Answer:** Reusing open database connections instead of opening one per request.
- **SettleUp:** SQLAlchemy's engine pool (`pool_pre_ping=True`).
- **Follow-ups:** PgBouncer; pool size vs worker count.

**S50. How would you back up and restore the database?**
- **Answer:** `pg_dump -Fc settleup > settleup.dump` and `pg_restore -d settleup settleup.dump`.
- **SettleUp:** not automated (local project).
- **Follow-ups:** Point-in-time recovery with WAL archiving.

**S51. How do you see a table's definition in psql?**
- **Answer:** `\d expenses` lists columns, indexes and constraints; `\dt` lists tables.
- **Follow-ups:** Querying `information_schema.columns`.

## 22.4 Database Design and Normalisation (30 questions)

**D1. Walk me through the SettleUp schema.**
- **Answer:** users; groups (creator FK); group_members (junction users↔groups with role); expenses (group, payer); expense_splits (junction expenses↔users with share); settlements (group, payer, receiver).
- **Follow-ups:** Which tables are junction tables? Which constraints protect money?

**D2. Why do we need `expense_splits`?**
- **Answer:** Participants of an expense are a many-to-many relationship with an attribute (the share). A separate table allows FKs, uniqueness, CHECKs and simple aggregation.
- **Example:** Kiran's total share = `SUM(share_amount_paise) WHERE user_id = Kiran`.
- **Follow-ups:** What if every split were always equal? (You still need to know *who*.)

**D3. Why not store participants in a single column?**
- **Answer:** Violates 1NF; no referential integrity; no uniqueness; hard to query and update; custom amounts would be unstructured.
- **Follow-ups:** What about PostgreSQL arrays or JSONB? (Possible, but you lose FK constraints per element.)

**D4. How does a many-to-many relationship work?**
- **Answer:** Through a junction table holding FKs to both sides, one row per pair.
- **SettleUp:** `group_members(group_id, user_id)`, `expense_splits(expense_id, user_id)`.
- **Follow-ups:** Composite PK vs surrogate PK + UNIQUE.

**D5. Why does `group_members` have its own `id` instead of a composite PK?**
- **Answer:** Convention (every table has `id`) and simpler ORM handling; the UNIQUE `(group_id, user_id)` provides the same guarantee.
- **Follow-ups:** Downsides? (One more index.)

**D6. Why is `group_members` needed instead of group ids in `users`?**
- **Answer:** A user belongs to many groups; a single column can hold only one, an array breaks 1NF and FKs, and there's nowhere to put role/join date.
- **Follow-ups:** Query "members of group 5" in each design.

**D7. What is normalisation?**
- **Answer:** Structuring tables so each fact is stored once, avoiding update/insert/delete anomalies.
- **SettleUp:** names only in `users`, roles only in `group_members`, shares only in `expense_splits`.
- **Follow-ups:** Downsides? (More joins.)

**D8. Explain 1NF with SettleUp.**
- **Answer:** Atomic values, no repeating groups — one row per participant instead of a CSV column.
- **Follow-ups:** Is an email "atomic"? (For our purposes, yes.)

**D9. Explain 2NF with SettleUp.**
- **Answer:** No non-key attribute depends on part of a composite key. Expense description depends only on `expense_id`, so it lives in `expenses`, not `expense_splits`.
- **Follow-ups:** Does 2NF matter with a single-column PK? (It is automatically satisfied.)

**D10. Explain 3NF with SettleUp.**
- **Answer:** No transitive dependencies. Payer name depends on `paid_by`, so it is in `users`, not `expenses`.
- **Follow-ups:** BCNF?

**D11. Is storing `amount_paise` on `expenses` a normalisation violation?**
- **Answer:** Technically derivable from splits, but it is the primary user-entered fact; splits are derived from it and validated equal in the same transaction. A deliberate, controlled redundancy.
- **Follow-ups:** How would you detect drift? (Audit query S46.)

**D12. Why not store balances?**
- **Answer:** Derived data that would need updating on every change and could become inconsistent. Computing from source records keeps one source of truth.
- **Follow-ups:** When would you cache them? (Very large groups; with careful invalidation or materialised views.)

**D13. What is denormalisation and when is it justified?**
- **Answer:** Intentionally duplicating data for read performance; justified when reads dominate and consistency can be maintained.
- **SettleUp:** not needed at this scale.
- **Follow-ups:** Examples: counters, cached totals.

**D14. Why surrogate keys instead of email as the PK of users?**
- **Answer:** Emails can change; integers are small and stable; FKs stay simple.
- **Follow-ups:** UUIDs vs integers (UUIDs hide counts, but larger and less index-friendly).

**D15. Explain the cardinalities in the ER diagram.**
- **Answer:** users 1–N groups (creator); users N–M groups via group_members; groups 1–N expenses; users 1–N expenses (payer); expenses 1–N(≥1) splits; groups 1–N settlements; users 1–N settlements twice.
- **Follow-ups:** Which minimums are enforced by the DB vs the API? (≥1 split, ≥1 member: API.)

**D16. Why does `settlements` reference `users` twice?**
- **Answer:** Two roles: payer and receiver; each needs its own FK.
- **Follow-ups:** How does the ORM disambiguate? (`foreign_keys=[paid_by]`.)

**D17. Why is `group_id` stored on settlements?**
- **Answer:** Balances are per group, and settlements must reduce debts within a specific group.
- **Follow-ups:** Could one settlement span groups? (Not in this design — future scope.)

**D18. Why is the category a CHECK constraint and not a table?**
- **Answer:** Small fixed list; keeps the schema to six tables. A `categories` table would be better if users could define their own.
- **Follow-ups:** How to add a category later? (Migration altering the CHECK + updating the Literal.)

**D19. What cascade rules did you choose and why?**
- **Answer:** CASCADE from groups/expenses to dependent rows; RESTRICT on user references to protect financial history.
- **Follow-ups:** Soft deletes (`deleted_at`) as an alternative.

**D20. What happens to an expense if its payer leaves the group?**
- **Answer:** They can only leave with a zero balance; the expense remains (FK to users still valid) and they appear in balances as `is_member: false`.
- **Follow-ups:** Can the expense be edited later? (Yes by an admin; the new payer/participants must be current members.)

**D21. How would you add percentage splits?**
- **Answer:** Accept percentages in the API, convert to paise with the same remainder-distribution approach, and store paise in `expense_splits` (no schema change needed; maybe add `'percentage'` to the split_type CHECK).
- **Follow-ups:** Rounding rule for 33.33%?

**D22. How would you support multiple currencies?**
- **Answer:** Add a `currency` column (ISO code) on groups or expenses, store minor units, and never sum different currencies without conversion.
- **SettleUp:** not implemented.
- **Follow-ups:** Exchange-rate snapshots.

**D23. How would you model recurring expenses?**
- **Answer:** A `recurring_expenses` template table (amount, schedule, participants) and a job that creates normal expenses.
- **SettleUp:** future scope.
- **Follow-ups:** Idempotent job design.

**D24. Which indexes would you add for 10× more data?**
- **Answer:** Measure first with `EXPLAIN ANALYZE`; candidates: `(group_id, category)` for filters, `(user_id, expense_id)` covering index for shares, partial indexes.
- **Follow-ups:** Index-only scans.

**D25. Why `(group_id, expense_date)` and not two single-column indexes?**
- **Answer:** The common query filters by group and sorts/filters by date; one composite index serves both and avoids a sort.
- **Follow-ups:** Bitmap AND of two indexes as the alternative.

**D26. What is referential integrity?**
- **Answer:** Every FK value refers to an existing row.
- **SettleUp:** enforced by FKs; e.g. no split can point at a deleted expense.
- **Follow-ups:** Deferrable constraints.

**D27. How does the schema prevent duplicate membership?**
- **Answer:** UNIQUE `(group_id, user_id)`; the API also checks first for a friendly 409.
- **Follow-ups:** Race between check and insert? (Constraint catches it → 409.)

**D28. How would you audit changes to expenses?**
- **Answer:** An `expense_history` table written in the same transaction (or triggers) with old/new values, user and time.
- **SettleUp:** not implemented; only `created_at`/`updated_at`.
- **Follow-ups:** Event sourcing.

**D29. What is an ER diagram and what notation is used here?**
- **Answer:** A diagram of entities, attributes and relationships; SettleUp uses crow's-foot notation (Mermaid `erDiagram`).
- **Follow-ups:** Chen notation differences.

**D30. If you could change one thing in the schema, what?**
- **Answer (honest):** Add `created_by` to `expenses` (who *entered* it, not just who paid) to support "creator can edit" and auditing; possibly soft-deletes.
- **Follow-ups:** Migration plan for existing rows.

## 22.5 SQLAlchemy and ORM (25 questions)

**O1. What is an ORM? Pros and cons?**
- **Answer:** Maps tables to classes. Pros: less boilerplate, safer parameters, relationships. Cons: hidden queries (N+1), learning curve, complex SQL can be awkward.
- **SettleUp:** ORM for writes; `select(func.sum(...))` for aggregates.
- **Follow-ups:** When would you write raw SQL?

**O2. What is the Session?**
- **Answer:** A unit of work that tracks objects and holds a transaction.
- **SettleUp:** one per request via `get_db()`.
- **Follow-ups:** Is a Session thread-safe? (No — one per request/thread.)

**O3. What is the Engine?**
- **Answer:** The connection pool + dialect.
- **SettleUp:** `create_engine(DATABASE_URL, pool_pre_ping=True)`.
- **Follow-ups:** One engine per process.

**O4. `Mapped[...]` and `mapped_column()` — what do they do?**
- **Answer:** SQLAlchemy 2 typed declarations; the type annotation determines Python type and nullability.
- **Follow-ups:** Old `Column()` style.

**O5. ForeignKey vs relationship()?**
- **Answer:** `ForeignKey` is the database constraint/column; `relationship()` is Python navigation between objects.
- **Follow-ups:** Can you have one without the other? (Yes.)

**O6. What does `back_populates` do?**
- **Answer:** Keeps both sides of a bidirectional relationship in sync in memory.
- **SettleUp:** `Expense.splits` ↔ `ExpenseSplit.expense`.
- **Follow-ups:** `backref` (older shortcut).

**O7. What does `cascade="all, delete-orphan"` mean?**
- **Answer:** Session operations (add, delete, merge…) propagate to children; children removed from the collection are deleted.
- **SettleUp:** `expense.splits.clear()` deletes old splits during edits.
- **Follow-ups:** Difference from DB-level ON DELETE CASCADE.

**O8. What does `passive_deletes=True` do?**
- **Answer:** For children not loaded, SQLAlchemy does not load them before deleting the parent and relies on `ON DELETE CASCADE`.
- **SettleUp:** on expenses/members collections; loaded splits are still deleted by the ORM (captured SQL in 10.9).
- **Follow-ups:** Requires the DB FK to have ON DELETE CASCADE.

**O9. What is the N+1 problem and how did you avoid it?**
- **Answer:** One query for a list plus one per item for related data. Avoided with `selectinload(Expense.payer)`, `selectinload(Expense.splits).selectinload(ExpenseSplit.user)`.
- **Follow-ups:** `joinedload` vs `selectinload`.

**O10. joinedload vs selectinload?**
- **Answer:** `joinedload` uses a JOIN in the same query (can duplicate parent rows for collections); `selectinload` runs a second query with `IN (...)` — better for collections.
- **Follow-ups:** `lazy="raise"` to catch accidental lazy loads.

**O11. What is lazy loading?**
- **Answer:** Related objects load on first attribute access.
- **SettleUp:** default; eager loading used where lists are serialised.
- **Follow-ups:** Problems after the session closes (DetachedInstanceError).

**O12. What does `expire_on_commit=False` do and why use it?**
- **Answer:** Keeps loaded attributes after commit so they can be read without a new query.
- **SettleUp:** building responses right after commit.
- **Follow-ups:** Risk: stale values if the DB changed meanwhile.

**O13. What does `autoflush=False` change?**
- **Answer:** Pending changes are not automatically flushed before queries; you control when SQL is sent.
- **Follow-ups:** When autoflush helps (queries see your pending changes).

**O14. flush() vs commit()?**
- **Answer:** `flush` sends SQL within the current transaction; `commit` flushes and makes it permanent.
- **SettleUp:** expense edit flushes deletes before inserts, then commits once.
- **Follow-ups:** Can flushed data be rolled back? (Yes, until commit.)

**O15. How does SQLAlchemy get the new id after an insert?**
- **Answer:** `INSERT ... RETURNING id` on PostgreSQL during flush.
- **Follow-ups:** `db.refresh(obj)`.

**O16. What is `db.get()` vs `select().where()`?**
- **Answer:** `get` looks up by primary key and may use the identity map without querying; `select` always queries.
- **Follow-ups:** What is the identity map? (One object per row per session.)

**O17. scalar() vs scalars() vs execute()?**
- **Answer:** First column of first row / iterator over first column / full rows.
- **Follow-ups:** `.one()`, `.first()`, `.all()`.

**O18. How are aggregates written in SQLAlchemy?**
- **Answer:** `select(Expense.paid_by, func.sum(Expense.amount_paise)).where(...).group_by(Expense.paid_by)`.
- **Follow-ups:** `label()` for column names.

**O19. How do you write a subquery in SQLAlchemy?**
- **Answer:** Build a `select()` and use it in `.in_()` or `.subquery()`.
- **SettleUp:** `Expense.id.in_(select(ExpenseSplit.expense_id).where(...))`; member counts `.subquery()`.
- **Follow-ups:** `exists()`.

**O20. How does SQLAlchemy prevent SQL injection?**
- **Answer:** Bound parameters for all values.
- **Follow-ups:** `text()` with `:params` for raw SQL — still parameterised.

**O21. How do SQLAlchemy models relate to Alembic?**
- **Answer:** Alembic compares `Base.metadata` with the database to autogenerate migrations.
- **Follow-ups:** Why import all models in `env.py`?

**O22. Why not call `Base.metadata.create_all()` at startup?**
- **Answer:** It only creates missing tables — never alters them — and keeps no history. Migrations are versioned and reversible.
- **Follow-ups:** Where is `create_all` acceptable? (Throwaway prototypes.)

**O23. How do you roll back a bad migration?**
- **Answer:** `alembic downgrade -1` runs the `downgrade()` function.
- **Follow-ups:** Data migrations vs schema migrations.

**O24. How does the ORM handle `updated_at`?**
- **Answer:** `onupdate=func.now()` adds it to ORM UPDATE statements; raw SQL updates would not change it.
- **Follow-ups:** Trigger-based alternative.

**O25. How would you switch to async SQLAlchemy?**
- **Answer:** `create_async_engine("postgresql+psycopg://...")`, `AsyncSession`, `async def` endpoints, `await session.execute(...)`, and eager loading everywhere (lazy loads are not allowed in async).
- **Follow-ups:** Benefits at this scale? (Small.)

## 22.6 Authentication and Security (25 questions)

**A1. How does JWT authentication work end to end?**
- **Answer:** Login verifies the password and returns a signed token with `sub` = user id and an expiry. The client sends it as `Authorization: Bearer`. Each request, the server verifies the signature and expiry, then loads the user.
- **SettleUp:** `create_access_token`, `get_current_user`.
- **Follow-ups:** Where is the token stored on the client? (localStorage.)

**A2. What is inside the JWT?**
- **Answer:** Header `{"alg":"HS256","typ":"JWT"}`; payload `{"sub":"5","iat":…,"exp":…}`; HMAC-SHA256 signature.
- **Follow-ups:** Why not put the email or role in it? (Not needed; roles are per group and checked in the DB.)

**A3. Is a JWT encrypted?**
- **Answer:** No — Base64URL-encoded and signed. Anyone can read it; only the key holder can produce a valid signature.
- **Follow-ups:** JWE for encryption.

**A4. Authentication vs authorisation?**
- **Answer:** Who you are vs what you may do.
- **SettleUp:** `get_current_user` (401) vs membership/role checks (404/403).
- **Follow-ups:** Give an example of each failing.

**A5. How do you prevent unauthorised users from accessing group expenses?**
- **Answer:** Every group-scoped endpoint verifies membership; expense endpoints look up the expense's group and verify membership; outsiders get 404.
- **Follow-ups:** How is it tested? (`test_non_member_cannot_create_or_read_expenses`.)

**A6. Why bcrypt instead of SHA-256 for passwords?**
- **Answer:** bcrypt is slow and salted by design; SHA-256 is fast, which helps attackers brute-force.
- **Follow-ups:** Argon2, cost factor tuning.

**A7. What is a salt?**
- **Answer:** Random data mixed into each hash so identical passwords hash differently and precomputed tables don't work.
- **SettleUp:** `bcrypt.gensalt()`; salt stored inside the hash string.
- **Follow-ups:** Pepper.

**A8. Why the 72-byte password limit?**
- **Answer:** bcrypt only uses the first 72 bytes; rejecting longer input avoids silent truncation.
- **Follow-ups:** Pre-hashing with SHA-256 trade-offs.

**A9. Why the same error for wrong email and wrong password?**
- **Answer:** Prevents user enumeration.
- **Follow-ups:** Registration still reveals "email already registered" — a common trade-off.

**A10. How is logout implemented?**
- **Answer:** The frontend deletes the token; JWTs are stateless so the server cannot revoke it before expiry.
- **Follow-ups:** Token blacklist, short-lived access + refresh tokens (future scope).

**A11. What happens when a token expires?**
- **Answer:** `jwt.decode` raises `ExpiredSignatureError` → 401; the Axios interceptor clears the token and redirects to login.
- **Follow-ups:** Clock skew (`leeway`).

**A12. What is the risk of storing JWTs in localStorage?**
- **Answer:** Readable by any script on the page, so XSS could steal it. HttpOnly cookies avoid that but need CSRF protection.
- **SettleUp:** localStorage for simplicity; React escaping reduces XSS risk.
- **Follow-ups:** SameSite cookies.

**A13. How does SettleUp avoid leaking secrets?**
- **Answer:** Secrets come from environment variables / `.env` (git-ignored); `.env.example` has placeholders; responses never include hashes; errors are generic.
- **Follow-ups:** Secret rotation.

**A14. What happens if the JWT secret leaks?**
- **Answer:** Anyone could forge tokens for any user. Rotate the secret (invalidates all tokens).
- **Follow-ups:** Asymmetric keys (RS256) so APIs only need the public key.

**A15. Why `algorithms=[...]` in `jwt.decode`?**
- **Answer:** Allow-list prevents algorithm-confusion attacks (e.g. `alg: none`).
- **Follow-ups:** HS256 vs RS256.

**A16. How is SQL injection prevented?**
- **Answer:** All queries are parameterised by SQLAlchemy.
- **Follow-ups:** Show a vulnerable f-string query and fix it.

**A17. How is mass assignment prevented?**
- **Answer:** Pydantic schemas whitelist fields; e.g. users cannot set `role` when adding themselves or set `group_id` in an expense body.
- **Follow-ups:** What if `ExpenseUpdate` allowed `group_id`? (Moving expenses across groups — deliberately not allowed.)

**A18. What is CORS and is it a security feature?**
- **Answer:** A browser mechanism that relaxes the same-origin policy for listed origins. It protects users' browsers, not the API — non-browser clients ignore it.
- **Follow-ups:** Why still require auth on every endpoint.

**A19. What is IDOR and how does SettleUp prevent it?**
- **Answer:** Insecure Direct Object Reference — accessing objects by guessing ids. Prevented by checking membership for every id-based access.
- **Follow-ups:** Would UUIDs alone fix it? (No — authorisation is still required.)

**A20. What validation protects against bad financial data?**
- **Answer:** Pydantic (positive integers, limits, sums), router checks (membership, debt limits), DB constraints (CHECK/FK/UNIQUE).
- **Follow-ups:** Defence in depth.

**A21. Why does the 422 handler strip `input`?**
- **Answer:** FastAPI's default echoes the submitted value, which on `/auth/register` would return the password in the response (and potentially into logs).
- **Follow-ups:** Other sensitive echo risks.

**A22. Is SettleUp production-secure?**
- **Answer:** No claim is made. Missing: HTTPS termination, rate limiting, refresh tokens/revocation, audit logs, security headers, dependency scanning, penetration testing.
- **Follow-ups:** Prioritise the list.

**A23. How would you add rate limiting to login?**
- **Answer:** Per-IP and per-account counters (Redis) or a reverse-proxy limit; exponential backoff.
- **Follow-ups:** Lockout DoS risks.

**A24. Who can record a settlement and why?**
- **Answer:** The payer, the receiver or an admin — so a random member cannot mark someone else's debt as paid.
- **Follow-ups:** Should the receiver confirm? (Future scope.)

**A25. How would you implement password reset?**
- **Answer:** Single-use, short-lived random token stored hashed, emailed link, set new password, invalidate sessions.
- **SettleUp:** not implemented (no email service).
- **Follow-ups:** Why hash reset tokens?

## 22.7 Transactions and Consistency (25 questions)

**T1. What happens during a database transaction?**
- **Answer:** Statements execute in an isolated context; changes are invisible to others until COMMIT; on error or ROLLBACK, all are undone; on COMMIT, WAL makes them durable.
- **SettleUp:** creating an expense and its splits.
- **Follow-ups:** Implicit vs explicit transactions.

**T2. What happens if an expense is saved but its splits fail?**
- **Answer:** Both are in one transaction; the failure aborts it and the rollback removes the expense too.
- **Follow-ups:** What if they were in separate transactions? (Orphan expense, broken balances.)

**T3. How would you handle simultaneous expense creation?**
- **Answer:** Independent inserts don't conflict; PostgreSQL handles them concurrently. Each is atomic, and balances are computed from committed rows, so both are reflected.
- **Follow-ups:** What if they must respect a budget? (Then lock or use SERIALIZABLE.)

**T4. Why does settlement creation need a lock?**
- **Answer:** Validation reads balances then inserts; two concurrent requests could both pass validation and over-settle. `SELECT ... FOR UPDATE` on the group row serialises them.
- **Follow-ups:** Alternative: SERIALIZABLE isolation with retry.

**T5. What does Read Committed guarantee?**
- **Answer:** No dirty reads; each statement sees data committed before it began.
- **Follow-ups:** Non-repeatable reads, phantoms.

**T6. What is a lost update?**
- **Answer:** Two transactions read a value, both modify it, and one overwrites the other.
- **SettleUp:** concurrent edits of the same expense are last-writer-wins (documented).
- **Follow-ups:** Optimistic locking with a version column.

**T7. What is optimistic vs pessimistic locking?**
- **Answer:** Optimistic: detect conflicts at write time (version check). Pessimistic: lock before reading (`FOR UPDATE`).
- **SettleUp:** pessimistic for settlements.
- **Follow-ups:** When is each better?

**T8. Why not use SERIALIZABLE everywhere?**
- **Answer:** It makes conflicting transactions fail with serialization errors that the app must retry; more complexity and aborts.
- **Follow-ups:** How would you implement retries?

**T9. What does `db.rollback()` do in SQLAlchemy?**
- **Answer:** Rolls back the DB transaction and expires session state.
- **SettleUp:** after catching `IntegrityError`; in `get_db()` on exceptions.
- **Follow-ups:** Using the session after a failed flush without rollback (error).

**T10. Why flush between deleting and inserting splits?**
- **Answer:** To send DELETEs first so UNIQUE `(expense_id, user_id)` isn't violated by an old and a new row for the same user — still within one transaction.
- **Follow-ups:** Deferrable unique constraints.

**T11. How do you guarantee balances sum to zero?**
- **Answer:** Each expense's shares equal its amount (validated in the same transaction) and each settlement adds and subtracts the same amount.
- **Follow-ups:** How is it tested? (Sum assertions in tests.)

**T12. What consistency rules does the database enforce vs the application?**
- **Answer:** DB: single-row and referential rules. App: multi-row rules (splits sum, settlement limits).
- **Follow-ups:** Could triggers move more into the DB?

**T13. What is a savepoint?**
- **Answer:** A named point inside a transaction you can roll back to without aborting the whole transaction.
- **SettleUp:** not used.
- **Follow-ups:** `session.begin_nested()`.

**T14. What does `FOR UPDATE` lock — the table or rows?**
- **Answer:** Only the selected rows (here one `groups` row).
- **Follow-ups:** `LOCK TABLE` vs row locks; lock modes.

**T15. When is the settlement lock released?**
- **Answer:** At COMMIT or ROLLBACK.
- **Follow-ups:** Why keep the transaction short.

**T16. Can two settlements in different groups block each other?**
- **Answer:** No — they lock different group rows.
- **Follow-ups:** Hot rows in a very busy group.

**T17. What if a request crashes after the lock but before commit?**
- **Answer:** The connection closes, PostgreSQL aborts the transaction and releases the lock.
- **Follow-ups:** `idle_in_transaction_session_timeout`.

**T18. What is atomicity in the member-removal endpoint?**
- **Answer:** Promoting a new admin and deleting the old membership are committed together.
- **Follow-ups:** What if only one happened? (Group without an admin.)

**T19. What is eventual vs strong consistency?**
- **Answer:** Strong: reads see the latest committed write. Eventual: replicas converge later.
- **SettleUp:** single PostgreSQL instance → strong consistency.
- **Follow-ups:** Read replicas would introduce lag.

**T20. Why does the test suite use a real PostgreSQL database?**
- **Answer:** To test real constraints, transactions and SQL functions (`FOR UPDATE`, `to_char`) that SQLite would emulate differently.
- **Follow-ups:** Speed trade-offs; transaction-rollback-per-test strategy.

**T21. How is each test isolated?**
- **Answer:** `TRUNCATE ... RESTART IDENTITY CASCADE` after each test.
- **Follow-ups:** Alternative: wrap each test in a transaction and roll back.

**T22. How would you test the settlement race?**
- **Answer:** Two threads/connections sending settlements simultaneously against a real DB, asserting only one succeeds when both would over-settle.
- **SettleUp:** **not implemented** — stated honestly in Chapter 16.
- **Follow-ups:** Deterministic concurrency tests with barriers.

**T23. What is durability and how could it fail?**
- **Answer:** Committed data survives crashes via WAL fsync; it can fail with disk loss (needs backups/replication) or if fsync is disabled.
- **Follow-ups:** RPO/RTO.

**T24. Is the `amount_paise` vs splits invariant safe against concurrent edits?**
- **Answer:** Each edit rewrites amount and splits atomically, so each committed state is consistent; the last writer wins.
- **Follow-ups:** Detecting concurrent edits for the user (ETags/version).

**T25. Why are suggestions not stored?**
- **Answer:** They are derived from current balances and would become stale with any change.
- **Follow-ups:** Caching with invalidation if computation became expensive.

## 22.8 Project-Specific Questions (20)

**J1. Describe SettleUp in two minutes.**
- **Answer:** React + FastAPI + PostgreSQL app for shared expenses: groups, equal/custom splits in integer paise, computed balances, greedy settlement suggestions, recorded repayments with locked validation, dashboard. 97 backend + 13 frontend automated tests.
- **Follow-ups:** What was hardest? (Correct money handling and concurrency of settlements.)

**J2. How are balances calculated?**
- **Answer:** `paid − share + settlements paid − settlements received`, from four GROUP BY queries per group; never stored.
- **Follow-ups:** Why recompute instead of storing?

**J3. How do you avoid floating-point errors in money calculations?**
- **Answer:** Integer paise everywhere (BIGINT, Python int, JS integers); string-based rupee parsing on the frontend; explicit remainder distribution when dividing.
- **Follow-ups:** What about displaying? (`formatPaise` uses integer division and modulo.)

**J4. How is an equal split of ₹100 among 3 handled?**
- **Answer:** 3334 + 3333 + 3333 paise; the extra paisa goes to the lowest user id — deterministic and exact.
- **Follow-ups:** Is that fair? (Bias is at most 1 paisa per expense; could rotate or randomise.)

**J5. What happens if custom shares don't add up?**
- **Answer:** The frontend shows "₹x left to assign" and blocks submit; the backend's model validator returns 422 regardless.
- **Follow-ups:** Why validate twice?

**J6. Who can edit or delete an expense?**
- **Answer:** The payer or a group admin; others get 403.
- **Follow-ups:** Why not the person who entered it? (Not tracked — see D30.)

**J7. Why can't a member with a balance leave?**
- **Answer:** Their history would still affect others' balances while they could no longer settle in the group.
- **Follow-ups:** What if they want to leave anyway? (Settle first.)

**J8. What happens when the only admin leaves?**
- **Answer:** The earliest-joined remaining member is promoted, in the same transaction.
- **Follow-ups:** Alternatives (require transfer).

**J9. How are settlements validated?**
- **Answer:** Different people; both members; caller is party or admin; payer owes; receiver is owed; amount ≤ min(debt, credit) — computed under a row lock.
- **Follow-ups:** Partial settlements? (Allowed.)

**J10. What does the dashboard show and how is it computed?**
- **Answer:** Totals across my groups, my paid/share/net, per-group balances, 8 recent expenses with my share, category totals, 6-month summary, settlements involving me — one endpoint, several aggregate queries.
- **Follow-ups:** Performance with many groups?

**J11. How is the frontend structured?**
- **Answer:** Routes in `App.jsx`, layouts (`Layout`, `GroupLayout`), pages per screen, one Axios client, an auth context, shared UI components, money utils.
- **Follow-ups:** Why no Redux?

**J12. How does the frontend know a token expired?**
- **Answer:** A 401 triggers the response interceptor, which clears the token and dispatches a logout event.
- **Follow-ups:** Silent refresh (not implemented).

**J13. How did you test the project?**
- **Answer:** Pytest against a real PostgreSQL test DB built by Alembic (unit + API + DB constraint tests), Vitest component tests, and a manual end-to-end walkthrough with screenshots.
- **Follow-ups:** Coverage gaps? (Concurrency, browser E2E automation.)

**J14. What would you improve if the application had thousands of users?**
- **Answer:** Measure first. Then: cache or batch per-group balance computation for the group list/dashboard, keyset pagination, connection pooling (PgBouncer), multiple Uvicorn workers behind a reverse proxy, rate limiting, refresh tokens, background jobs, monitoring.
- **Follow-ups:** Which would you do first and why?

**J15. What would change for millions of expenses in one group?**
- **Answer:** Incremental balance snapshots (periodic checkpoints + recent deltas) or materialised views, partitioning by date, covering indexes.
- **Follow-ups:** Consistency of snapshots.

**J16. How did the team divide work?**
- **Answer:** Sarvesh did the database design and the backend; Sharanagouda built the React frontend; Gollal wrote the frontend tests, the seed data, the Docker database setup and the dashboard API tests. The API contract allowed parallel work.
- **Follow-ups:** How did you keep the contract in sync? (Pydantic schemas + Swagger.)

**J17. Why is there a separate services layer?**
- **Answer:** Splitting, balances and the settlement algorithm are business logic independent of HTTP; isolating them makes them testable and reusable (dashboard reuses balances).
- **Follow-ups:** Why no repository layer? (The Session already is one at this size.)

**J18. What is the role of the seed script?**
- **Answer:** Development-only sample data built through the same models and split functions; refuses to run twice.
- **Follow-ups:** Why not seed in migrations? (Migrations are for schema, not demo data.)

**J19. What are the main limitations?**
- **Answer:** No real payments, no invitations, no token revocation, greedy not globally minimal, not deployed/audited, per-group recomputation cost (Chapter 23).
- **Follow-ups:** Which matters most for real users?

**J20. What bug did you find during development and how did you fix it?**
- **Answer (true example):** Validation errors echoed request bodies, including passwords. Fixed with a custom `RequestValidationError` handler and a test asserting the password is not in the response.
- **Follow-ups:** How did you find it? (Reading actual API responses during the walkthrough.)

## 22.9 Settlement Algorithm Questions (15)

**G1. How does the settlement algorithm work?**
- **Answer:** Separate creditors and debtors, sort by amount, repeatedly match the largest remaining debtor with the largest remaining creditor for `min(debt, credit)`, advance whoever reaches zero.
- **Follow-ups:** Dry-run an example.

**G2. Why does it always terminate?**
- **Answer:** Each step zeros at least one participant and advances a pointer.
- **Follow-ups:** Maximum iterations? (≤ number of non-zero participants.)

**G3. Why does it always settle everyone?**
- **Answer:** Total remaining debt equals total remaining credit at every step; the loop can't stop while either is positive.
- **Follow-ups:** What if balances don't sum to zero? (`ValueError`.)

**G4. How many payments does it produce at most?**
- **Answer:** n − 1 for n non-zero participants.
- **Follow-ups:** Prove it.

**G5. Is it optimal?**
- **Answer:** Not always. Optimal = n − (max number of disjoint zero-sum subsets), an NP-hard problem. Counter-example: −600, −600, −600, +300, +600, +900 → greedy 5, optimal 4.
- **Follow-ups:** How did you find the counter-example? (Brute-force search over small inputs.)

**G6. Time and space complexity?**
- **Answer:** O(n log n) time (sorting) and O(n) space.
- **Follow-ups:** Could you avoid sorting? (Yes, any order works for correctness; sorting improves typical results and determinism.)

**G7. Why sort largest first?**
- **Answer:** Large debts matched with large credits tend to settle people in fewer steps, and it gives a deterministic order.
- **Follow-ups:** Use heaps instead of sorted lists? (Same bound, useful if amounts re-enter.)

**G8. Why are ties broken by user id?**
- **Answer:** Deterministic output: same balances → same suggestions every time.
- **Follow-ups:** Why does determinism matter for the UI?

**G9. Why use net balances instead of individual debts?**
- **Answer:** Netting collapses all pairwise obligations into one number per person, which already removes many unnecessary transfers.
- **Follow-ups:** When would pairwise debts matter? (If people insist on paying the specific person they owe.)

**G10. How would you find the true minimum for small groups?**
- **Answer:** Search for the maximum partition into zero-sum subsets (bitmask DP over subsets, O(2^n · n)), feasible for n ≤ ~15–20.
- **Follow-ups:** Implement the DP.

**G11. How is the algorithm tested?**
- **Answer:** Example from the brief, empty/zero/single-pair/one-to-many cases, odd paise, unbalanced input, determinism, 25 random groups checking all invariants, and comparison with brute force.
- **Follow-ups:** Property-based testing.

**G12. What invariants do the tests check?**
- **Answer:** All amounts > 0; debtors only pay, creditors only receive; applying the plan zeros everyone; total paid equals total debt; ≤ n − 1 payments.
- **Follow-ups:** Any others? (No self-payments.)

**G13. Where do the algorithm's inputs come from?**
- **Answer:** `compute_group_balances` → `{user_id: net_balance_paise}`.
- **Follow-ups:** Why keep the function pure?

**G14. What happens after one suggested payment is recorded?**
- **Answer:** Balances change; the next request recomputes a shorter plan.
- **Follow-ups:** Can users pay a different amount than suggested? (Yes, within the limits.)

**G15. Why integers matter for this algorithm.**
- **Answer:** With floats, residues like 0.0000001 could remain and create tiny bogus payments or infinite loops; with integer paise every comparison to zero is exact.
- **Follow-ups:** How would you handle multi-currency? (Per-currency settlement.)

# Chapter 23 — Limitations and Future Improvements

## 23.1 Genuine limitations of the current implementation

| Limitation | Impact | Possible remedy |
|---|---|---|
| Settlements are records only | No money actually moves; relies on honesty | Payment integration (future scope) |
| Members must already be registered | Cannot invite by email | Invitation workflow (future scope) |
| Stateless JWT, no refresh/revocation; stored in localStorage | Stolen token valid until expiry; logout is client-side only | Short-lived access + refresh tokens, revocation list, httpOnly cookies |
| No rate limiting or account lockout | Login brute-force is only slowed by bcrypt | Rate limiting middleware / proxy |
| Greedy settlement not always minimal | Occasionally one or more extra payments | Exact search for small groups (G10) |
| Balances recomputed per request; group list and dashboard compute per group | Fine for small data; grows with number of groups | Single-query aggregation across groups, caching |
| Concurrent edits of the same expense are last-writer-wins | One user's change can silently replace another's | Version column / ETags |
| Settlement concurrency logic not covered by an automated concurrent test | Behaviour relies on PostgreSQL semantics, verified by reasoning only | Add a multi-connection test |
| A former member's balance can change if an admin later edits an old expense | They might owe money while not a member | Lock old expenses or block edits involving former members |
| No audit trail of who changed what | Disputes cannot be resolved from history | Expense history table |
| No email verification or password reset | Typos lock users out | Email service |
| Not deployed; no HTTPS configuration; not security-audited | Local use only | Deployment with TLS, security review |
| Fixed category list | Users cannot add categories | Categories table |

## 23.2 Future scope (NOT implemented)

These are ideas for later versions. None of them exist in the current code.

* **Recurring expenses** — monthly rent/Wi-Fi created automatically from a template.
* **Notifications** — email or push when someone adds an expense or records a payment.
* **UPI integration** — deep links or a payment gateway to actually pay suggested amounts.
* **Exportable reports** — CSV/PDF export of a group's expenses and balances.
* **Expense receipt uploads** — attach photos of bills (object storage + virus scanning).
* **Better group invitations** — invite unregistered people by email or shareable link.
* Settlement confirmation by the receiver; settlement reversal.
* Percentage and share-based splits; multiple currencies.
* Offline-friendly mobile app.

# Chapter 24 — Complete Codebase Navigation

## 24.1 Folder map

```text
settleup/
├── README.md
├── docker-compose.yml               optional PostgreSQL 16 for local development
├── backend/
│   ├── requirements.txt             pinned Python dependencies
│   ├── .env.example                 configuration template
│   ├── alembic.ini                  Alembic configuration
│   ├── alembic/env.py               connects Alembic to settings + models
│   ├── alembic/versions/0001_create_initial_schema.py   the schema migration
│   ├── app/
│   │   ├── main.py                  app creation, CORS, exception handlers, routers
│   │   ├── config.py                Settings (env vars)
│   │   ├── database.py              engine, SessionLocal, Base, get_db
│   │   ├── models/                  user.py, group.py, expense.py, settlement.py
│   │   ├── schemas/                 user.py, group.py, expense.py, settlement.py, dashboard.py
│   │   ├── routers/                 auth.py, groups.py, expenses.py, settlements.py, dashboard.py
│   │   ├── services/                split_service.py, balance_service.py, settlement_service.py
│   │   ├── dependencies/auth.py     get_current_user, require_group_member/admin
│   │   └── utils/security.py        bcrypt + JWT helpers
│   ├── scripts/seed.py              development seed data
│   ├── scripts/create_test_db.sql   creates settleup_test (used by docker-compose)
│   └── tests/                       conftest.py + 7 test modules
├── frontend/
│   ├── package.json                 pinned JS dependencies and scripts
│   ├── vite.config.js               Vite, Tailwind plugin, Vitest config, chunking
│   ├── .env.example                 VITE_API_BASE_URL
│   └── src/
│       ├── main.jsx, App.jsx        bootstrapping and routes
│       ├── api/client.js, api.js    Axios instance + endpoint functions
│       ├── context/AuthContext.jsx  auth state
│       ├── components/              Layout, GroupLayout, ProtectedRoute, ExpenseForm, ui
│       ├── pages/                   screens
│       ├── utils/money.js, format.js
│       └── test/                    Vitest tests
└── docs/
    ├── SettleUp_Complete_Technical_Guide.md / .pdf
    ├── TEST_REPORT.md, DEVELOPMENT_LOG.md, schema.sql
    ├── screenshots/                 16 PNG screenshots
    ├── test-results/                raw pytest and vitest output
    └── tools/                       screenshot and PDF build scripts (documentation tooling)
```

## 24.2 "Where is…?" table

| Question | Answer |
|---|---|
| Where are routes defined? | Backend: `app/routers/*.py` (mounted in `app/main.py`). Frontend: `src/App.jsx`. |
| Where are database models? | `app/models/*.py`; exported from `app/models/__init__.py`. |
| Where is the schema created? | `alembic/versions/0001_create_initial_schema.py` (never `create_all`). |
| Where does input validation happen? | `app/schemas/*.py` (Pydantic); business-rule checks in routers. |
| Where are permissions checked? | `app/dependencies/auth.py`; plus `_require_can_modify` in `routers/expenses.py` and the party check in `routers/settlements.py`. |
| Where is authentication? | `app/dependencies/auth.py:get_current_user`, `app/utils/security.py`, `routers/auth.py`. |
| Where are splits calculated? | `app/services/split_service.py`. |
| Where are balances calculated? | `app/services/balance_service.py:compute_group_balances`. |
| Where is the settlement algorithm? | `app/services/settlement_service.py:suggest_settlements`. |
| Where is the settlement lock? | `app/routers/settlements.py:record_settlement` (`with_for_update()`). |
| Where are dashboard numbers built? | `app/routers/dashboard.py:get_dashboard`. |
| Where are errors turned into JSON? | `app/main.py` exception handlers. |
| Where are tests? | `backend/tests/` (pytest), `frontend/src/test/` (Vitest). |
| How does the frontend call the backend? | `src/api/api.js` functions → `src/api/client.js` Axios instance (base URL from `VITE_API_BASE_URL`, token interceptor). |
| Where is the token stored? | `localStorage['settleup_token']` via `src/api/client.js`. |
| Where is money converted/formatted? | `src/utils/money.js` (`rupeesToPaise`, `formatPaise`, `previewEqualSplit`). |
| Where is configuration read? | `app/config.py` (backend), `import.meta.env` in `src/api/client.js` (frontend). |

## 24.3 Reading order for a new team member

1. `README.md` → run the app.
2. `backend/app/models/` → understand the data.
3. `backend/app/routers/expenses.py` → one complete feature.
4. `backend/app/services/` → the business logic.
5. `backend/tests/test_balances_settlements.py` → how behaviour is specified.
6. `frontend/src/App.jsx` → `components/GroupLayout.jsx` → `components/ExpenseForm.jsx`.
