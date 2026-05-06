import { pool } from "../db/pool.js";

function toMoney(value) {
  return Math.round(Number(value || 0) * 100) / 100;
}

function badRequest(message) {
  const err = new Error(message);
  err.statusCode = 400;
  return err;
}

async function resolveReceiptId(idOrReceiptNo, client = pool) {
  if (idOrReceiptNo == null || String(idOrReceiptNo).trim() === "") return null;
  if (!Number.isNaN(Number(idOrReceiptNo))) return Number(idOrReceiptNo);

  const res = await client.query("SELECT receipt_id FROM receipt_header WHERE receipt_no = $1", [String(idOrReceiptNo).trim()]);
  return res.rowCount > 0 ? res.rows[0].receipt_id : null;
}

async function resolveCustomerId({ customer_id, customer_code }, client = pool) {
  if (customer_id) return Number(customer_id);
  if (!customer_code || String(customer_code).trim() === "") throw badRequest("Customer must be selected before choosing invoices.");

  const res = await client.query("SELECT id FROM customer WHERE code = $1", [String(customer_code).trim()]);
  if (res.rowCount === 0) throw badRequest(`Customer not found: ${customer_code}`);
  return res.rows[0].id;
}

async function generateReceiptNo(client, receiptDate) {
  const date = receiptDate ? new Date(receiptDate) : new Date();
  const yy = String(date.getUTCFullYear()).slice(-2);
  const prefix = `RCT${yy}-`;
  const res = await client.query(
    `
      SELECT receipt_no
      FROM receipt_header
      WHERE receipt_no LIKE $1
      ORDER BY receipt_no DESC
      LIMIT 1
    `,
    [`${prefix}%`],
  );
  const lastNo = res.rowCount > 0 ? Number(String(res.rows[0].receipt_no).slice(prefix.length)) : 0;
  return `${prefix}${String(lastNo + 1).padStart(5, "0")}`;
}

async function buildReceiptLine(client, { customerId, invoice_id, amount_received_here }, excludeReceiptId = null) {
  const invoiceId = Number(invoice_id);
  if (!invoiceId) throw badRequest("Receipt line missing invoice_id.");

  const inv = await client.query(
    `
      SELECT id, invoice_no, customer_id, coalesce(amount_due, 0)::numeric as amount_due
      FROM invoice
      WHERE id = $1
    `,
    [invoiceId],
  );
  if (inv.rowCount === 0) throw badRequest(`Invoice not found: ${invoiceId}`);
  const invoice = inv.rows[0];
  if (Number(invoice.customer_id) !== Number(customerId)) {
    throw badRequest(`Invoice ${invoice.invoice_no} does not belong to the selected customer.`);
  }

  const received = await client.query(
    `
      SELECT coalesce(sum(amount_received_here), 0)::numeric as amount_received
      FROM receipt_line
      WHERE invoice_id = $1
        AND ($2::bigint IS NULL OR receipt_id <> $2::bigint)
    `,
    [invoiceId, excludeReceiptId],
  );

  const fullAmountDue = toMoney(invoice.amount_due);
  const amountAlreadyReceived = toMoney(received.rows[0].amount_received);
  const amountRemaining = toMoney(fullAmountDue - amountAlreadyReceived);
  const amountReceivedHere = toMoney(amount_received_here);
  const amountStillRemaining = toMoney(amountRemaining - amountReceivedHere);

  if (amountReceivedHere < 0) throw badRequest(`Invoice ${invoice.invoice_no}: amount received must be at least 0.`);
  if (amountReceivedHere > amountRemaining) {
    throw badRequest(`Invoice ${invoice.invoice_no}: amount received cannot exceed remaining balance (${amountRemaining}).`);
  }

  return {
    invoice_id: invoiceId,
    invoice_no: invoice.invoice_no,
    full_amount_due: fullAmountDue,
    amount_already_received: amountAlreadyReceived,
    amount_remaining: amountRemaining,
    amount_received_here: amountReceivedHere,
    amount_still_remaining: amountStillRemaining,
  };
}

async function normalizeReceiptLines(client, customerId, lineItems = [], excludeReceiptId = null) {
  if (!Array.isArray(lineItems) || lineItems.length === 0) throw badRequest("At least one invoice line is required.");

  const seen = new Set();
  const lines = [];
  for (const item of lineItems) {
    const invoiceId = Number(item.invoice_id);
    if (seen.has(invoiceId)) throw badRequest("Each invoice can appear only once per receipt.");
    seen.add(invoiceId);
    lines.push(await buildReceiptLine(client, { customerId, ...item }, excludeReceiptId));
  }
  return lines;
}

function normalizeCreatePayload(body = {}) {
  const receiptDate = body.receipt_date || new Date().toISOString().slice(0, 10);
  const lineItems = Array.isArray(body.line_items)
    ? body.line_items
    : Array.isArray(body.lines)
      ? body.lines.map((line) => ({
          invoice_id: line.invoice_id,
          amount_received_here: line.amount_received_here ?? line.amount,
        }))
      : [];

  return {
    ...body,
    receipt_date: receiptDate,
    line_items: lineItems,
  };
}

export async function listReceipts({
  search = "",
  page = 1,
  limit = 10,
  sortBy = "receipt_date",
  sortDir = "desc",
} = {}) {
  const offset = (Number(page) - 1) * Number(limit);
  const allowedSort = {
    receipt_no: "rh.receipt_no",
    receipt_date: "rh.receipt_date",
    customer_name: "c.name",
    payment_method: "rh.payment_method",
    total_received: "rh.total_received",
  };
  const sortColumn = allowedSort[sortBy] || allowedSort.receipt_date;
  const sortDirection = sortDir === "asc" ? "ASC" : "DESC";
  const searchParam = `%${search}%`;

  const countResult = await pool.query(
    `
      SELECT COUNT(*) as total
      FROM receipt_header rh
      JOIN customer c ON c.id = rh.customer_id
      WHERE rh.receipt_no ILIKE $1 OR c.code ILIKE $1 OR c.name ILIKE $1
    `,
    [searchParam],
  );
  const total = Number(countResult.rows[0].total);

  const { rows } = await pool.query(
    `
      SELECT rh.receipt_id, rh.receipt_no, rh.receipt_date, rh.payment_method, rh.total_received,
             c.code as customer_code, c.name as customer_name
      FROM receipt_header rh
      JOIN customer c ON c.id = rh.customer_id
      WHERE rh.receipt_no ILIKE $1 OR c.code ILIKE $1 OR c.name ILIKE $1
      ORDER BY ${sortColumn} ${sortDirection} NULLS LAST, rh.receipt_id DESC
      LIMIT $2 OFFSET $3
    `,
    [searchParam, Number(limit), offset],
  );

  return {
    data: rows,
    total,
    page: Number(page),
    limit: Number(limit),
    totalPages: Math.ceil(total / Number(limit)),
  };
}

export async function getReceipt(idOrReceiptNo) {
  const receiptId = await resolveReceiptId(idOrReceiptNo);
  if (receiptId == null) return null;

  const header = await pool.query(
    `
      SELECT rh.receipt_id, rh.receipt_no, rh.receipt_date, rh.customer_id, rh.payment_method,
             rh.payment_notes, rh.total_received,
             c.code as customer_code, c.name as customer_name, c.address_line1, c.address_line2
      FROM receipt_header rh
      JOIN customer c ON c.id = rh.customer_id
      WHERE rh.receipt_id = $1
    `,
    [receiptId],
  );
  if (header.rowCount === 0) return null;

  const lines = await pool.query(
    `
      SELECT rl.receipt_line_id, rl.invoice_id, i.invoice_no, i.invoice_date,
             rl.full_amount_due, rl.amount_already_received, rl.amount_remaining,
             rl.amount_received_here, rl.amount_still_remaining
      FROM receipt_line rl
      JOIN invoice i ON i.id = rl.invoice_id
      WHERE rl.receipt_id = $1
      ORDER BY rl.receipt_line_id
    `,
    [receiptId],
  );

  return { header: header.rows[0], line_items: lines.rows };
}

export async function createReceipt(body = {}) {
  const { receipt_no, receipt_date, customer_id, customer_code, payment_method, payment_notes, line_items } = normalizeCreatePayload(body);
  const client = await pool.connect();
  try {
    await client.query("begin");

    const customerId = await resolveCustomerId({ customer_id, customer_code }, client);
    const receiptNo = receipt_no && String(receipt_no).trim() !== ""
      ? String(receipt_no).trim()
      : await generateReceiptNo(client, receipt_date);
    const lines = await normalizeReceiptLines(client, customerId, line_items);

    const rh = await client.query(
      `
        INSERT INTO receipt_header (receipt_no, receipt_date, customer_id, payment_method, payment_notes)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING receipt_id, receipt_no
      `,
      [receiptNo, receipt_date, customerId, payment_method, payment_notes || null],
    );

    for (const line of lines) {
      await client.query(
        `
          INSERT INTO receipt_line (
            receipt_id, invoice_id, full_amount_due, amount_already_received,
            amount_remaining, amount_received_here, amount_still_remaining
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7)
        `,
        [
          rh.rows[0].receipt_id,
          line.invoice_id,
          line.full_amount_due,
          line.amount_already_received,
          line.amount_remaining,
          line.amount_received_here,
          line.amount_still_remaining,
        ],
      );
    }

    await client.query("commit");
    return { receipt_id: rh.rows[0].receipt_id, receipt_no: rh.rows[0].receipt_no };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}

export async function updateReceipt(idOrReceiptNo, { receipt_date, customer_id, customer_code, payment_method, payment_notes, line_items }) {
  const client = await pool.connect();
  try {
    await client.query("begin");

    const receiptId = await resolveReceiptId(idOrReceiptNo, client);
    if (receiptId == null) {
      await client.query("rollback");
      return null;
    }

    const existing = await client.query("SELECT receipt_id FROM receipt_header WHERE receipt_id = $1 FOR UPDATE", [receiptId]);
    if (existing.rowCount === 0) {
      await client.query("rollback");
      return null;
    }

    const customerId = await resolveCustomerId({ customer_id, customer_code }, client);
    const lines = await normalizeReceiptLines(client, customerId, line_items, receiptId);

    await client.query(
      `
        UPDATE receipt_header
        SET receipt_date = $1, customer_id = $2, payment_method = $3, payment_notes = $4
        WHERE receipt_id = $5
      `,
      [receipt_date, customerId, payment_method, payment_notes || null, receiptId],
    );

    await client.query("DELETE FROM receipt_line WHERE receipt_id = $1", [receiptId]);
    for (const line of lines) {
      await client.query(
        `
          INSERT INTO receipt_line (
            receipt_id, invoice_id, full_amount_due, amount_already_received,
            amount_remaining, amount_received_here, amount_still_remaining
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7)
        `,
        [
          receiptId,
          line.invoice_id,
          line.full_amount_due,
          line.amount_already_received,
          line.amount_remaining,
          line.amount_received_here,
          line.amount_still_remaining,
        ],
      );
    }

    await client.query("commit");
    return { ok: true, receipt_id: receiptId };
  } catch (err) {
    await client.query("rollback");
    throw err;
  } finally {
    client.release();
  }
}

export async function deleteReceipt(idOrReceiptNo) {
  const receiptId = await resolveReceiptId(idOrReceiptNo);
  if (receiptId == null) return null;

  const res = await pool.query("DELETE FROM receipt_header WHERE receipt_id = $1 RETURNING receipt_id", [receiptId]);
  return res.rowCount > 0 ? { ok: true } : null;
}

export async function getNextReceiptNo(receiptDate) {
  const client = await pool.connect();
  try {
    return await generateReceiptNo(client, receiptDate);
  } finally {
    client.release();
  }
}

export async function printReceipt(idOrReceiptNo) {
  return getReceipt(idOrReceiptNo);
}
