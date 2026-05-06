import React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";
import { getReceipt, createReceipt, updateReceipt } from "../../api/receipts.api.js";
import ReceiptForm from "../../components/ReceiptForm.jsx";
import ReceiptPrint from "../../components/ReceiptPrint.jsx";
import Loading from "../../components/Loading.jsx";

export default function ReceiptPage({ mode: propMode }) {
  const { id } = useParams();
  const mode = propMode || (id ? "view" : "create");
  const nav = useNavigate();
  const [receiptData, setReceiptData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [submitting, setSubmitting] = React.useState(false);
  const [err, setErr] = React.useState("");

  React.useEffect(() => {
    if (mode === "create") {
      setLoading(false);
      return;
    }
    getReceipt(id)
      .then((data) => {
        setReceiptData(data);
        setLoading(false);
      })
      .catch((e) => {
        setErr(String(e.message || e));
        setLoading(false);
      });
  }, [id, mode]);

  async function onSubmit(payload) {
    setErr("");
    setSubmitting(true);
    try {
      if (mode === "create") {
        const res = await createReceipt(payload);
        toast.success("Receipt created.");
        nav(`/receipts/${encodeURIComponent(res.receipt_no)}`);
      } else {
        await updateReceipt(id, payload);
        toast.success("Receipt updated.");
        nav(`/receipts/${encodeURIComponent(id)}`);
      }
    } catch (e) {
      const msg = String(e.message || e);
      setErr(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <Loading size="large" />;

  if (mode === "view" && receiptData) {
    const h = receiptData.header;
    return (
      <div className="invoice-preview">
        <div className="page-header no-print">
          <h3 className="page-title">Receipt {h.receipt_no}</h3>
          <div className="flex gap-4">
            <Link to="/receipts" className="btn btn-outline">← Back</Link>
            <Link to={`/receipts/${id}/edit`} className="btn btn-outline">Edit</Link>
            <button onClick={() => window.print()} className="btn btn-primary">
              <svg style={{ marginRight: 8 }} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 9V2h12v7"></path>
                <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
                <rect x="6" y="14" width="12" height="8"></rect>
              </svg>
              Print Receipt
            </button>
          </div>
        </div>

        <ReceiptPrint header={h} line_items={receiptData.line_items} />
      </div>
    );
  }

  const title = mode === "create" ? "Create Receipt" : `Edit Receipt ${id}`;
  return (
    <div className="invoice-page">
      <div className="page-header">
        <h3 className="page-title">{title}</h3>
        <Link to="/receipts" className="btn btn-outline">Back</Link>
      </div>
      {err && <div className="alert alert-error">{err}</div>}
      <ReceiptForm onSubmit={onSubmit} submitting={submitting} initialData={mode === "create" ? null : receiptData} />
    </div>
  );
}
