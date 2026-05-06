import React from "react";
import CustomerPickerModal from "../../../components/CustomerPickerModal.jsx";
import { getCustomer } from "../../../api/customers.api.js";

// Editable input + LoV (like Create Invoice): type code or pick from list; on blur fetch name to show
export default function CustomerFilter({ value: customerCode, displayLabel, onChange }) {
  const [pickerOpen, setPickerOpen] = React.useState(false);

  const handleSelect = (code, label) => {
    onChange({ customerCode: code, customerLabel: label });
    setPickerOpen(false);
  };

  const handleInputChange = (e) => {
    const v = e.target.value.trim();
    onChange({ customerCode: v, customerLabel: "" });
  };

  const handleBlur = () => {
    const code = String(customerCode || "").trim();
    if (!code) return;
    getCustomer(code)
      .then((c) => onChange({ customerCode: code, customerLabel: `${c.code} - ${c.name}` }))
      .catch(() => { /* keep code, no label */ });
  };

  const display = displayLabel || customerCode || "";
  const isEmpty = !String(customerCode || "").trim();

  return (
    <div className="filter-group">
      <label className="filter-label">Customer</label>
      <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
        <input
          className="form-control"
          type="text"
          value={isEmpty ? "" : display}
          onChange={handleInputChange}
          onBlur={handleBlur}
          placeholder="All Customers (type code or use LoV)"
          style={{ flex: 1 }}
        />
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setPickerOpen(true)}
          title="List of Values"
        >
          LoV
        </button>
        {!isEmpty && (
          <button
            type="button"
            onClick={() => onChange({ customerCode: "", customerLabel: "" })}
            title="Clear"
            style={{
              padding: "0 12px",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              background: "var(--bg-body)",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "1.2rem",
              lineHeight: 1,
            }}
          >
            ×
          </button>
        )}
      </div>
      <CustomerPickerModal
        isOpen={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={handleSelect}
        initialSearch={customerCode || ""}
      />
    </div>
  );
}
