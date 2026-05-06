import React from "react";

export default function DateRangeFilter({ dateFrom, dateTo, onChange }) {
  return (
    <div className="filter-group">
      <label className="filter-label">Date Range</label>
      <div className="filter-row">
        <input
          type="date"
          className="form-control"
          value={dateFrom}
          onChange={(e) => onChange({ dateFrom: e.target.value })}
          placeholder="From"
        />
        <span className="filter-separator">to</span>
        <input
          type="date"
          className="form-control"
          value={dateTo}
          onChange={(e) => onChange({ dateTo: e.target.value })}
          placeholder="To"
        />
      </div>
    </div>
  );
}
