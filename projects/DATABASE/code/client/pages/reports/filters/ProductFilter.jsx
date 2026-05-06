import React from "react";
import ProductPickerModal from "../../../components/ProductPickerModal.jsx";
import { getProduct } from "../../../api/products.api.js";

// Editable input + LoV (like Create Invoice): type code or pick from list; on blur fetch name to show
export default function ProductFilter({ value: productCode, displayLabel, onChange }) {
  const [pickerOpen, setPickerOpen] = React.useState(false);

  const handleSelect = (row) => {
    const label = `${row.code} - ${row.name}`;
    onChange({ productCode: row.code, productLabel: label });
    setPickerOpen(false);
  };

  const handleInputChange = (e) => {
    const v = e.target.value.trim();
    onChange({ productCode: v, productLabel: "" });
  };

  const handleBlur = () => {
    const code = String(productCode || "").trim();
    if (!code) return;
    getProduct(code)
      .then((p) => onChange({ productCode: code, productLabel: `${p.code} - ${p.name}` }))
      .catch(() => { /* keep code, no label */ });
  };

  const display = displayLabel || productCode || "";
  const isEmpty = !String(productCode || "").trim();

  return (
    <div className="filter-group">
      <label className="filter-label">Product</label>
      <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
        <input
          className="form-control"
          type="text"
          value={isEmpty ? "" : display}
          onChange={handleInputChange}
          onBlur={handleBlur}
          placeholder="All Products (type code or use LoV)"
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
            onClick={() => onChange({ productCode: "", productLabel: "" })}
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
      <ProductPickerModal
        isOpen={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={handleSelect}
        initialSearch={productCode || ""}
      />
    </div>
  );
}
