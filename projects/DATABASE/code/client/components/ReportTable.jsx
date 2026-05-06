// Table for report data: columns, sortable headers, loading state, empty message. Used by Reports.jsx.
import React from "react";
import { TableLoading } from "./Loading.jsx";

export default function ReportTable({ columns, data, emptyMessage = "No data found.", filters, sortKey, sortDir, onSort, loading = false }) {
  const SortIcon = ({ columnKey, sortable }) => {
    if (sortable === false) return null;
    const isActive = sortKey === columnKey;
    return (
      <span style={{ marginLeft: 4, opacity: isActive ? 1 : 0.3 }}>
        {isActive && sortDir === "desc" ? "▼" : "▲"}
      </span>
    );
  };

  const handleSort = (key, sortable) => {
    if (sortable === false || !onSort) return;
    if (sortKey === key) {
      onSort(key, sortDir === "asc" ? "desc" : "asc");
    } else {
      onSort(key, "asc");
    }
  };

  return (
    <table className="modern-table">
      <thead>
        <tr>
          {columns.map(col => (
            <th 
              key={col.key} 
              className={col.align === "right" ? "text-right" : ""}
              onClick={() => handleSort(col.key, col.sortable)}
              style={{ 
                cursor: col.sortable !== false ? 'pointer' : 'default',
                userSelect: 'none'
              }}
            >
              {col.label}
              <SortIcon columnKey={col.key} sortable={col.sortable} />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <TableLoading colSpan={columns.length} />
        ) : (
          <>
            {data.map((row, idx) => (
              <tr key={idx}>
                {columns.map(col => (
                  <td key={col.key} className={col.align === "right" ? "text-right" : ""} style={col.style}>
                    {col.render ? col.render(row[col.key], row, filters) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="text-center p-4" style={{ color: "var(--text-muted)" }}>
                  {emptyMessage}
                </td>
              </tr>
            )}
          </>
        )}
      </tbody>
    </table>
  );
}
