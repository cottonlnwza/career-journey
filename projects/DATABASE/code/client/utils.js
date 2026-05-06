
// Format number as Thai Baht currency
// Example: formatBaht(1234.5) -> "฿1,234.50"
export const formatBaht = (amount) => {
    return new Intl.NumberFormat('th-TH', {
        style: 'currency',
        currency: 'THB',
    }).format(amount);
};

// Format date string to Thai locale
// Example: formatDate("2026-02-01") -> Thai formatted date
export const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
        const d = new Date(dateStr);
        return new Intl.DateTimeFormat('en-US', {
            day: '2-digit',
            month: 'long',
            year: 'numeric',
        }).format(d);
    } catch (e) {
        return dateStr;
    }
};
