\set ON_ERROR_STOP on

-- Receipt module report examples.
-- The receipt tables, constraints, trigger-maintained header total, and invoice_received_view
-- are defined in 001_schema.sql. Sample receipt data is defined in 003_seed.sql.

-- Report 1: Receipt List
-- Edit params as needed.
WITH params AS (
  SELECT null::date as date_from, null::date as date_to, null::text as customer_code
)
SELECT
  rh.receipt_no,
  rh.receipt_date,
  c.code as customer_code,
  c.name as customer_name,
  rh.payment_method,
  rh.total_received
FROM receipt_header rh
JOIN customer c ON c.id = rh.customer_id
JOIN params p ON true
WHERE (p.date_from IS NULL OR rh.receipt_date >= p.date_from)
  AND (p.date_to IS NULL OR rh.receipt_date <= p.date_to)
  AND (p.customer_code IS NULL OR c.code = p.customer_code)
ORDER BY rh.receipt_date DESC, rh.receipt_no DESC;

-- Report 2: Invoice + Receipt
-- Shows invoice balance from invoice_received_view plus each receipt allocation.
WITH params AS (
  SELECT null::date as date_from, null::date as date_to, null::text as customer_code
)
SELECT
  i.invoice_no,
  i.invoice_date,
  irv.amount_due,
  irv.amount_received,
  irv.amount_remain as remaining,
  rh.receipt_no,
  rh.receipt_date,
  rl.amount_received_here as receipt_amount
FROM invoice i
JOIN invoice_received_view irv ON irv.invoice_id = i.id
LEFT JOIN receipt_line rl ON rl.invoice_id = i.id
LEFT JOIN receipt_header rh ON rh.receipt_id = rl.receipt_id
JOIN params p ON true
WHERE (p.date_from IS NULL OR i.invoice_date >= p.date_from)
  AND (p.date_to IS NULL OR i.invoice_date <= p.date_to)
  AND (p.customer_code IS NULL OR i.customer_id = (SELECT id FROM customer WHERE code = p.customer_code))
ORDER BY i.invoice_date DESC, i.invoice_no, rh.receipt_date DESC NULLS LAST;
