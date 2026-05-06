import React from "react";
import CustomerPickerModal from "./CustomerPickerModal.jsx";
import InvoicePickerModal from "./InvoicePickerModal.jsx";
import { AlertModal } from "./Modal.jsx";
import { getCustomer } from "../api/customers.api.js";
import { getNextReceiptNo } from "../api/receipts.api.js";
import { formatBaht, formatDate } from "../utils.js";

const PAYMENT_METHODS = [
  { value: "cash", label: "Cash" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "check", label: "Check" },
];

const emptyLine = () => ({
  invoice_id: "",
  invoice_no: "",
  invoice_date: "",
  full_amount_due: 0,
  amount_already_received: 0,
  amount_remaining: 0,
  amount_received_here: 0,
});

function toMoney(value) {
  return Math.round(Number(value || 0) * 100) / 100;
}

export default function ReceiptForm({ onSubmit, submitting, initialData }) {
  const [receiptNo, setReceiptNo] = React.useState("");
  const [autoCode, setAutoCode] = React.useState(true);
  const [nextReceiptNo, setNextReceiptNo] = React.useState("");
  const [receiptDate, setReceiptDate] = React.useState(new Date().toISOString().slice(0, 10));
  const [customerCode, setCustomerCode] = React.useState("");
  const [customerDetails, setCustomerDetails] = React.useState(null);
  const [customerLoadError, setCustomerLoadError] = React.useState("");
  const [customerModalOpen, setCustomerModalOpen] = React.useState(false);
  const [paymentMethod, setPaymentMethod] = React.useState("cash");
  const [paymentNotes, setPaymentNotes] = React.useState("");
  const [lines, setLines] = React.useState([emptyLine()]);
  const [invoiceModalOpen, setInvoiceModalOpen] = React.useState(false);
  const [activeLineIndex, setActiveLineIndex] = React.useState(null);
  const [alertModal, setAlertModal] = React.useState({ isOpen: false, title: "Validation Error", message: "" });

  const editingReceiptId = initialData?.header?.receipt_id || null;

  React.useEffect(() => {
    if (!initialData) return;
    const header = initialData.header;
    setReceiptNo(header.receipt_no || "");
    setAutoCode(false);
    setReceiptDate(header.receipt_date ? new Date(header.receipt_date).toISOString().slice(0, 10) : "");
    setCustomerCode(header.customer_code || "");
    setPaymentMethod(header.payment_method || "cash");
    setPaymentNotes(header.payment_notes || "");
    setLines((initialData.line_items || []).map((line) => ({
      invoice_id: line.invoice_id,
      invoice_no: line.invoice_no,
      invoice_date: line.invoice_date,
      full_amount_due: Number(line.full_amount_due || 0),
      amount_already_received: Number(line.amount_already_received || 0),
      amount_remaining: Number(line.amount_remaining || 0),
      amount_received_here: Number(line.amount_received_here || 0),
    })));
  }, [initialData]);

  // Fetch customer details when customerCode changes
  React.useEffect(() => {
    const code = String(customerCode || "").trim();
    if (!code) {
      setCustomerDetails(null);
      setCustomerLoadError("");
      return;
    }
    let cancelled = false;
    setCustomerLoadError("");
    getCustomer(code)
      .then((data) => { if (!cancelled) setCustomerDetails(data); })
      .catch(() => {
        if (!cancelled) {
          setCustomerDetails(null);
          setCustomerLoadError("Customer not found");
        }
      });
    return () => { cancelled = true; };
  }, [customerCode]);

  // Preview next receipt number when in auto mode (create only)
  React.useEffect(() => {
    if (initialData || !autoCode) return;
    let cancelled = false;
    getNextReceiptNo(receiptDate)
      .then((no) => { if (!cancelled && no) setNextReceiptNo(no); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [autoCode, receiptDate, initialData]);

  const totalReceived = toMoney(lines.reduce((sum, line) => sum + Number(line.amount_received_here || 0), 0));

  function updateLine(index, patch) {
    setLines((current) => current.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  function openInvoicePicker(index) {
    setActiveLineIndex(index);
    setInvoiceModalOpen(true);
  }

  function handleInvoiceSelect(inv) {
    if (activeLineIndex == null) return;
    updateLine(activeLineIndex, {
      invoice_id: inv.invoice_id,
      invoice_no: inv.invoice_no,
      invoice_date: inv.invoice_date,
      full_amount_due: Number(inv.amount_due || 0),
      amount_already_received: Number(inv.amount_received || 0),
      amount_remaining: Number(inv.amount_remain || 0),
      amount_received_here: Number(inv.amount_remain || 0),
    });
    setActiveLineIndex(null);
  }

  function validate() {
    const errors = [];
    if (!receiptDate) errors.push("Receipt date is required.");
    if (!String(customerCode || "").trim() || !customerDetails) errors.push("Customer must be selected.");
    if (!initialData && !autoCode && !String(receiptNo || "").trim()) errors.push("Receipt no is required when Auto is off.");
    if (!paymentMethod) errors.push("Payment method is required.");
    if (lines.length === 0) errors.push("At least one invoice line is required.");

    const seen = new Set();
    lines.forEach((line, index) => {
      const row = index + 1;
      if (!line.invoice_id) errors.push(`Row ${row}: invoice is required.`);
      if (seen.has(String(line.invoice_id))) errors.push(`Row ${row}: invoice is duplicated.`);
      seen.add(String(line.invoice_id));
      const received = Number(line.amount_received_here);
      const remaining = Number(line.amount_remaining || 0);
      if (Number.isNaN(received) || received < 0) errors.push(`Row ${row}: amount received must be at least 0.`);
      if (received > remaining) errors.push(`Row ${row}: amount received cannot exceed remaining balance.`);
    });
    return errors;
  }

  function handleSubmit(e) {
    e.preventDefault();
    const errors = validate();
    if (errors.length > 0) {
      setAlertModal({
        isOpen: true,
        title: "Save Failed.",
        message: (
          <ul style={{ margin: 0, paddingLeft: 20, color: "var(--text-main)" }}>
            {errors.map((msg, i) => <li key={i}>{msg}</li>)}
          </ul>
        ),
      });
      return;
    }
    onSubmit({
      receipt_no: initialData ? receiptNo : (autoCode ? "" : receiptNo.trim()),
      receipt_date: receiptDate,
      customer_code: customerCode.trim(),
      payment_method: paymentMethod,
      payment_notes: paymentNotes,
      line_items: lines.map((line) => ({
        invoice_id: Number(line.invoice_id),
        amount_received_here: Number(line.amount_received_here || 0),
      })),
    });
  }

  const customerAddressDisplay = customerDetails
    ? [customerDetails.address_line1, customerDetails.address_line2, customerDetails.country_name].filter(Boolean).join(", ")
    : "";

  return (
    <>
      <AlertModal
        isOpen={alertModal.isOpen}
        onClose={() => setAlertModal((prev) => ({ ...prev, isOpen: false }))}
        title={alertModal.title}
        message={alertModal.message}
      />

      <InvoicePickerModal
        isOpen={invoiceModalOpen}
        onClose={() => { setInvoiceModalOpen(false); setActiveLineIndex(null); }}
        onSelect={handleInvoiceSelect}
        customerCode={customerCode}
        excludeReceiptId={editingReceiptId}
      />

      <form onSubmit={handleSubmit}>
        <div className="invoice-form-grid" style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 16, marginBottom: 16 }}>
          <div className="card">
            <h4>Receipt Details</h4>
            <div style={{ display: "grid", gap: 12 }}>

              {/* Receipt No */}
              <div className="form-group">
                <label className="form-label">
                  {(!initialData && autoCode) ? "Receipt No" : <>Receipt No <span className="required-marker">*</span></>}
                </label>
                <div className="flex gap-2">
                  <input
                    className="form-control"
                    disabled={autoCode || !!initialData}
                    value={receiptNo}
                    onChange={(e) => setReceiptNo(e.target.value)}
                    placeholder={autoCode ? (nextReceiptNo ? `Auto (next: ${nextReceiptNo})` : "Auto-generated") : "e.g. RCT26-00001"}
                  />
                  {!initialData && (
                    <div className="form-inline-option">
                      <input type="checkbox" checked={autoCode} onChange={(e) => setAutoCode(e.target.checked)} id="receipt_auto" />
                      <label htmlFor="receipt_auto">Auto</label>
                    </div>
                  )}
                </div>
              </div>

              {/* Customer */}
              <div className="form-group">
                <label className="form-label">Customer Code <span className="required-marker">*</span></label>
                <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
                  <input
                    className="form-control"
                    value={customerCode}
                    onChange={(e) => { setCustomerCode(e.target.value); setLines([emptyLine()]); }}
                    placeholder="e.g. C100"
                  />
                  <button type="button" className="btn btn-primary" onClick={() => setCustomerModalOpen(true)}>LoV</button>
                  {customerCode && (
                    <button type="button" className="btn btn-outline" onClick={() => { setCustomerCode(""); setLines([emptyLine()]); }}>Clear</button>
                  )}
                </div>
                {customerLoadError && <span style={{ fontSize: "0.8rem", color: "#ef4444", marginTop: 4, display: "block" }}>{customerLoadError}</span>}
              </div>

              <div className="form-group">
                <label className="form-label">Customer Name</label>
                <input className="form-control" disabled value={customerDetails?.name ?? ""} readOnly placeholder="-" />
              </div>

              <div className="form-group">
                <label className="form-label">Customer Address</label>
                <input className="form-control" disabled value={customerAddressDisplay} readOnly placeholder="-" />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Receipt Date <span className="required-marker">*</span></label>
                  <input type="date" className="form-control" value={receiptDate} onChange={(e) => setReceiptDate(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Payment Method <span className="required-marker">*</span></label>
                  <select className="form-control" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
                    {PAYMENT_METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Payment Notes</label>
                <textarea className="form-control" rows={3} value={paymentNotes} onChange={(e) => setPaymentNotes(e.target.value)} />
              </div>
            </div>
          </div>

          {/* Summary sidebar */}
          <div className="card invoice-summary-card" style={{ height: "fit-content" }}>
            <h4>Summary</h4>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, display: "flex", justifyContent: "space-between", fontSize: "1.1rem", fontWeight: 700, color: "var(--primary)" }}>
              <span>Total Received</span>
              <span>{submitting ? "..." : formatBaht(totalReceived)}</span>
            </div>
            <div style={{ marginTop: 16 }}>
              <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={submitting || !customerDetails}>
                {submitting ? "Saving..." : (initialData ? "Save Changes" : "Create Receipt")}
              </button>
              {!customerDetails && (
                <div style={{ marginTop: 6, fontSize: "0.75rem", color: "#ef4444", textAlign: "center" }}>
                  Please select a customer first
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Invoice allocation table */}
        <div className="card">
          <div className="flex justify-between mb-4">
            <h4 style={{ margin: 0 }}>Invoice Allocation</h4>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => setLines((current) => [...current, emptyLine()])}
              disabled={!customerDetails}
            >
              Add Invoice
            </button>
          </div>

          <div className="table-container">
            <table className="modern-table">
              <thead>
                <tr>
                  <th style={{ minWidth: 180 }}>Invoice No</th>
                  <th>Date</th>
                  <th className="text-right">Amount Due</th>
                  <th className="text-right">Already Received</th>
                  <th className="text-right">Remaining</th>
                  <th className="text-right">Received Here</th>
                  <th className="text-right">Still Remaining</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line, index) => {
                  const stillRemaining = toMoney(Number(line.amount_remaining || 0) - Number(line.amount_received_here || 0));
                  return (
                    <tr key={index}>
                      <td>
                        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          <input
                            className="form-control"
                            readOnly
                            value={line.invoice_no || ""}
                            placeholder={customerDetails ? "Select invoice..." : "Select customer first"}
                            style={{ flex: 1, cursor: "default", background: "var(--bg-body)" }}
                          />
                          <button
                            type="button"
                            className="btn btn-primary"
                            style={{ whiteSpace: "nowrap", padding: "6px 10px", fontSize: "0.8rem" }}
                            disabled={!customerDetails}
                            onClick={() => openInvoicePicker(index)}
                          >
                            LoV
                          </button>
                        </div>
                      </td>
                      <td>{line.invoice_date ? formatDate(line.invoice_date) : "-"}</td>
                      <td className="text-right">{formatBaht(line.full_amount_due)}</td>
                      <td className="text-right">{formatBaht(line.amount_already_received)}</td>
                      <td className="text-right font-bold">{formatBaht(line.amount_remaining)}</td>
                      <td className="text-right">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          className="form-control"
                          style={{ width: 120, marginLeft: "auto", textAlign: "right" }}
                          value={line.amount_received_here}
                          onChange={(e) => updateLine(index, { amount_received_here: e.target.value })}
                          disabled={!line.invoice_id}
                        />
                      </td>
                      <td className="text-right">{formatBaht(stillRemaining)}</td>
                      <td className="text-right">
                        <button
                          type="button"
                          className="btn btn-outline"
                          onClick={() => setLines((current) => current.filter((_, i) => i !== index))}
                          disabled={lines.length === 1}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </form>

      <CustomerPickerModal
        isOpen={customerModalOpen}
        onClose={() => setCustomerModalOpen(false)}
        initialSearch={customerCode}
        onSelect={(code) => {
          setCustomerCode(String(code));
          setLines([emptyLine()]);
          setCustomerModalOpen(false);
        }}
      />
    </>
  );
}
