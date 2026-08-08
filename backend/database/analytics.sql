create or replace view v_analytics_overview as
select
    count(*) as total_invoices,
    coalesce(sum(grand_total) filter (where processing_status = 'processed'), 0) as total_spend,
    coalesce(avg(grand_total) filter (where processing_status = 'processed'), 0) as avg_invoice_amount,
    count(distinct vendor) filter (where vendor is not null) as vendor_count,
    coalesce(avg(risk_score), 0) as avg_risk_score,
    count(*) filter (where processing_status = 'processed') as approved_count,
    count(*) filter (where processing_status = 'flagged') as flagged_count,
    count(*) filter (where processing_status = 'rejected') as rejected_count,
    count(*) filter (where processing_status = 'failed') as failed_count,
    count(*) filter (where processing_status = 'rejected') as validation_failure_count,
    count(*) filter (where processing_status = 'flagged') as manual_review_count,
    count(*) filter (where rule_violations ? 'duplicate_invoice') as duplicate_invoice_count,
    coalesce(avg(processing_time_ms) filter (where processing_time_ms is not null), 0) as avg_processing_time_ms,
    case
        when count(*) = 0 then 0
        else round(count(*) filter (where processing_status = 'processed')::numeric / count(*) * 100, 2)
    end as processing_success_rate
from invoices;

create or replace view v_vendor_summary as
select
    vendor,
    count(*) as invoice_count,
    coalesce(sum(grand_total), 0) as total_spend,
    coalesce(avg(grand_total), 0) as avg_invoice_size,
    coalesce(avg(risk_score), 0) as avg_risk_score,
    count(*) filter (where processing_status in ('flagged', 'rejected')) as high_risk_invoices
from invoices
where vendor is not null
group by vendor;

create or replace view v_risk_distribution as
select
    case
        when risk_score is null then 'unknown'
        when risk_score < 40 then 'low'
        when risk_score < 70 then 'medium'
        else 'high'
    end as risk_bucket,
    count(*) as invoice_count
from invoices
group by 1;

create or replace view v_currency_distribution as
select
    coalesce(currency, 'unknown') as currency,
    count(*) as invoice_count,
    coalesce(sum(grand_total), 0) as total_spend
from invoices
group by 1;

create or replace view v_rule_violation_frequency as
select violation, count(*) as occurrences
from invoices, jsonb_array_elements_text(coalesce(rule_violations, '[]'::jsonb)) as violation
group by violation
order by occurrences desc;

create or replace function fn_analytics_trends(p_granularity text)
returns table (
    period date,
    invoice_count bigint,
    total_spend numeric,
    total_tax numeric,
    total_discount numeric
)
language sql
stable
as $$
    select
        date_trunc(
            case p_granularity
                when 'day' then 'day'
                when 'week' then 'week'
                when 'month' then 'month'
                when 'quarter' then 'quarter'
                when 'year' then 'year'
                else 'month'
            end,
            invoice_date
        )::date as period,
        count(*) as invoice_count,
        coalesce(sum(grand_total), 0) as total_spend,
        coalesce(sum(tax), 0) as total_tax,
        coalesce(sum(discount), 0) as total_discount
    from invoices
    where invoice_date is not null
    group by 1
    order by 1;
$$;
