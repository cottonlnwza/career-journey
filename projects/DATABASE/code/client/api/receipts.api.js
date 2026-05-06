import { http } from "./http.js";

function unwrap(res) {
  if (res && res.success === false && res.error) throw new Error(res.error.message);
  return res;
}

export async function listReceipts(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = unwrap(await http(`/api/receipts${query ? `?${query}` : ""}`));
  return { data: res.data, ...(res.meta || {}) };
}

export async function getReceipt(id) {
  const res = unwrap(await http(`/api/receipts/${encodeURIComponent(id)}`));
  return res.data;
}

export async function createReceipt(payload) {
  const res = unwrap(await http("/api/receipts", { method: "POST", body: JSON.stringify(payload) }));
  return res.data;
}

export async function updateReceipt(id, payload) {
  const res = unwrap(await http(`/api/receipts/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(payload) }));
  return res.data;
}

export async function deleteReceipt(id) {
  const res = unwrap(await http(`/api/receipts/${encodeURIComponent(id)}`, { method: "DELETE" }));
  return res.data;
}

export async function getNextReceiptNo(receiptDate) {
  const qs = receiptDate ? `?receipt_date=${encodeURIComponent(receiptDate)}` : "";
  const res = unwrap(await http(`/api/receipts/next-no${qs}`));
  return res.data?.receipt_no ?? null;
}

export async function printReceipt(id) {
  const res = unwrap(await http(`/api/receipts/${encodeURIComponent(id)}/print`));
  return res.data;
}
