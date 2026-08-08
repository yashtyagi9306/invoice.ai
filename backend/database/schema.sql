create extension if not exists pgcrypto;

create table if not exists invoices (
    id uuid primary key default gen_random_uuid(),
    vendor text,
    invoice_number text,
    invoice_date date,
    due_date date,
    currency text,
    gst_number text,
    purchase_order text,
    subtotal numeric(14, 2),
    tax numeric(14, 2),
    discount numeric(14, 2),
    grand_total numeric(14, 2),
    payment_terms text,
    line_items jsonb,
    risk_score integer,
    risk_reason text,
    suggested_action text,
    attachment_path text,
    file_hash text,
    rule_violations jsonb,
    processing_time_ms integer,
    ai_summary text,
    processing_status text not null default 'pending',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_invoices_vendor on invoices (vendor);
create index if not exists idx_invoices_status on invoices (processing_status);
create index if not exists idx_invoices_created_at on invoices (created_at);
create index if not exists idx_invoices_file_hash on invoices (file_hash);
