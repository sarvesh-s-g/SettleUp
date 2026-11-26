BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 1eafb6ed5e01

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
    CONSTRAINT ck_expenses_category CHECK (category IN ('food', 'groceries', 'rent', 'utilities', 'transport', 'entertainment', 'shopping', 'other')), 
    CONSTRAINT ck_expenses_split_type CHECK (split_type IN ('equal', 'custom')), 
    CONSTRAINT ck_expenses_amount_positive CHECK (amount_paise > 0), 
    FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE, 
    FOREIGN KEY(paid_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_expenses_group_id_expense_date ON expenses (group_id, expense_date);

CREATE INDEX ix_expenses_paid_by ON expenses (paid_by);

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

INSERT INTO alembic_version (version_num) VALUES ('1eafb6ed5e01') RETURNING alembic_version.version_num;

COMMIT;

