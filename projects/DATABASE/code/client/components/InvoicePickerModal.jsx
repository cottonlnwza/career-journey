import React from "react";
import { createPortal } from "react-dom";
import { listUnpaidInvoices } from "../api/invoices.api.js";
import { formatBaht, formatDate } from "../utils.js";
import { TableLoading } from "./Loading.jsx";

export default function InvoicePickerModal({ isOpen, onClose, onSelect, customerCode, excludeReceiptId }) {
  const [data, setData] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const [searchInput, setSearchInput] = React.useState("");

  React.useEffect(() => {
    if (!isOpen) return;
    setSearch("");
    setSearchInput("");
  }, [isOpen]);

  React.useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 250);
    return () => clearTimeout(t);
  }, [searchInput]);

  React.useEffect(() => {
    if (!isOpen || !customerCode) {
      setData([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    listUnpaidInvoices({ customer_code: customerCode, exclude_receipt_id: excludeReceiptId || undefined })
      .then((rows) => {
        if (!cancelled) setData(rows || []);
      })
      .catch(() => { if (!cancelled) setData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [isOpen, customerCode, excludeReceiptId]);

  const filtered = search
    ? data.filter((inv) => inv.invoice_no.toLowerCase().includes(search.toLowerCase()))
    : data;

  const handleSelect = (inv) => {
    onSelect(inv);
    onClose();
  };

  if (!isOpen) return null;

  return createPortal(
    <div
      className="modal-overlay"
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 10000, padding: 24,
      }}
    >
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "white", borderRadius: "var(--radius)",
          boxShadow: "var(--shadow-lg)", maxWidth: 760, width: "100%",
          maxHeight: "80vh", overflow: "hidden", display: "flex", flexDirection: "column",
        }}
      >
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 600 }}>Select Invoice</h3>
          <div style={{ position: "relative", width: 220 }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search invoice no..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              style={{ paddingLeft: 34 }}
              autoFocus
            />
            <svg style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
          </div>
        </div>

        <div style={{ overflow: "auto", flex: 1, minHeight: 0 }}>
          <table className="modern-table">
            <thead>
              <tr>
                <th>Invoice No</th>
                <th>Date</th>
                <th className="text-right">Amount Due</th>
                <th className="text-right">Remaining</th>
                <th style={{ width: 90 }} className="text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <TableLoading colSpan={5} />
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", padding: 32, color: "var(--text-muted)" }}>
                    {!customerCode ? "Select a customer first." : search ? "No matching invoices." : "No unpaid invoices for this customer."}
                  </td>
                </tr>
              ) : (
                filtered.map((inv) => (
                  <tr key={inv.invoice_id}>
                    <td className="font-bold">{inv.invoice_no}</td>
                    <td>{formatDate(inv.invoice_date)}</td>
                    <td className="text-right">{formatBaht(inv.amount_due)}</td>
                    <td className="text-right" style={{ color: "var(--primary)", fontWeight: 600 }}>{formatBaht(inv.amount_remain)}</td>
                    <td className="text-center">
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{ padding: "5px 12px", fontSize: "0.85rem" }}
                        onClick={() => handleSelect(inv)}
                      >
                        Select
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>,
    document.body
  );
}
