// Loading spinner and message; TableLoading for inline table loading state.
import React from "react";

export default function Loading({ message = "Loading...", size = "medium" }) {
  const sizeMap = {
    small: 24,
    medium: 40,
    large: 64
  };
  
  const spinnerSize = sizeMap[size] || sizeMap.medium;

  return (
    <div className="loading-container">
      <div className="loading-spinner" style={{ width: spinnerSize, height: spinnerSize }}>
        <svg
          width={spinnerSize}
          height={spinnerSize}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" opacity="0.25" />
          <path
            d="M12 2a10 10 0 0 1 10 10"
            opacity="0.75"
          />
        </svg>
      </div>
      {message && <div className="loading-message">{message}</div>}
    </div>
  );
}

// Inline loading spinner for tables
export function TableLoading({ colSpan = 1 }) {
  return (
    <tr>
      <td colSpan={colSpan} className="text-center p-4">
        <div className="loading-container" style={{ padding: "20px" }}>
          <div className="loading-spinner" style={{ width: 32, height: 32, margin: "0 auto" }}>
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" opacity="0.25" />
              <path
                d="M12 2a10 10 0 0 1 10 10"
                opacity="0.75"
              />
            </svg>
          </div>
        </div>
      </td>
    </tr>
  );
}
