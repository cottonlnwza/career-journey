import { pool } from "../db/pool.js";

// สร้าง service สำหรับดึงข้อมูลเซลส์จาก database ตามคำค้นหา (search)
export async function listSalesPersons({ search, page, limit }) {
  const offset = (Number(page) - 1) * Number(limit);
  const searchParam = `%${search}%`;

  // query 1: นับ total (จำนวนทั้งหมดที่มี)
  const countResult = await pool.query(
    `SELECT COUNT(*) as total FROM sales_person
     WHERE code ILIKE $1 OR name ILIKE $1`,
    [searchParam],
  );

  // query 2: ดึง rows ตามหน้า (Pagination)
  const { rows } = await pool.query(
    `SELECT id, code, name, start_work_date
     FROM sales_person
     WHERE code ILIKE $1 OR name ILIKE $1
     ORDER BY code ASC
     LIMIT $2 OFFSET $3`,
    [searchParam, Number(limit), offset],
  );

  return { data: rows, total: Number(countResult.rows[0].total), page: Number(page), limit: Number(limit), 
    totalPages: Math.ceil(Number(countResult.rows[0].total) / Number(limit)) };
}

export async function getSalesPerson(id) {
  const r = await pool.query("SELECT id, code, name, start_work_date FROM sales_person WHERE id = $1", [id]);
  return r.rowCount > 0 ? r.rows[0] : null;
}

export async function createSalesPerson({ code, name, start_work_date }) {
  const r = await pool.query(
    "INSERT INTO sales_person (code, name, start_work_date, created_at) VALUES ($1, $2, $3, now()) RETURNING id, code, name, start_work_date",
    [code, name, start_work_date]
  );
  return r.rows[0];
}

export async function updateSalesPerson(id, { code, name, start_work_date }) {
  const r = await pool.query(
    "UPDATE sales_person SET code=$1, name=$2, start_work_date=$3 WHERE id=$4 RETURNING id",
    [code, name, start_work_date, id]
  );
  if (r.rowCount === 0) throw new Error("Sales Person not found");
  return { ok: true };
}

export async function deleteSalesPerson(id) {
  await pool.query("DELETE FROM sales_person WHERE id=$1", [id]);
  return { ok: true };
}
