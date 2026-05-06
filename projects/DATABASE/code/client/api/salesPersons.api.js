import { http } from "./http.js";

// copy มาจาก customers.api.js เพื่อ handle error แบบเดียวกัน
function unwrap(res) {
  if (res && res.success === false && res.error) throw new Error(res.error.message);
  return res;
}

// ฟังก์ชันสำหรับเรียก API รายชื่อเซลส์
export async function listSalesPersons(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = unwrap(await http(`/api/sales-persons${query ? `?${query}` : ""}`));
  return { data: res.data, ...(res.meta || {}) };
}

export async function getSalesPerson(id) {
  const res = unwrap(await http(`/api/sales-persons/${id}`));
  return res.data;
}

export async function createSalesPerson(payload) {
  const res = unwrap(await http("/api/sales-persons", { method: "POST", body: payload }));
  return res.data;
}

export async function updateSalesPerson(id, payload) {
  return unwrap(await http(`/api/sales-persons/${id}`, { method: "PUT", body: payload }));
}

export async function deleteSalesPerson(id) {
  return unwrap(await http(`/api/sales-persons/${id}`, { method: "DELETE" }));
}
