import React from "react";
import { formatBaht, formatDate } from "../utils.js";

const PAYMENT_LABELS = {
  cash: "Cash",
  bank_transfer: "Bank Transfer",
  check: "Check",
};

export default function ReceiptPrint({ header: h, line_items: lines = [] }) {
  return (
    <div className="card">
      <div className="flex justify-between mb-4">
        <div>
          <div className="brand mb-4">InvoiceDoc v2</div>
          <div className="font-bold">Received From</div>
          <div>{h.customer_name}</div>
          {h.address_line1 && <div className="text-muted">{h.address_line1}</div>}
          {h.address_line2 && <div className="text-muted">{h.address_line2}</div>}
        </div>
        <div className="text-right">
          <h2 className="mb-4">RECEIPT</h2>
          <div><span className="font-bold">Date:</span> {formatDate(h.receipt_date)}</div>
          <div><span className="font-bold">Receipt No:</span> {h.receipt_no}</div>
          <div><span className="font-bold">Payment:</span> {PAYMENT_LABELS[h.payment_method] || h.payment_method}</div>
        </div>
      </div>

      <div className="table-container">
        <table className="modern-table">
          <thead>
            <tr>
              <th>Invoice No</th>
              <th>Invoice Date</th>
              <th className="text-right">Amount Due</th>
              <th className="text-right">Already Received</th>
              <th className="text-right">Remaining Before</th>
              <th className="text-right">Received Here</th>
              <th className="text-right">Still Remaining</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.receipt_line_id}>
                <td className="font-bold">{line.invoice_no}</td>
                <td>{formatDate(line.invoice_date)}</td>
                <td className="text-right">{formatBaht(line.full_amount_due)}</td>
                <td className="text-right">{formatBaht(line.amount_already_received)}</td>
                <td className="text-right">{formatBaht(line.amount_remaining)}</td>
                <td className="text-right font-bold" style={{ color: "var(--primary)" }}>{formatBaht(line.amount_received_here)}</td>
                <td className="text-right">{formatBaht(line.amount_still_remaining)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex justify-between">
        <div className="text-muted" style={{ maxWidth: 360 }}>{h.payment_notes || ""}</div>
        <div style={{ minWidth: 240 }}>
          <div className="flex justify-between mt-4 p-2 bg-body font-bold" style={{ fontSize: "1.1rem" }}>
            <span>Total Received:</span>
            <span style={{ color: "var(--primary)" }}>{formatBaht(h.total_received)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
