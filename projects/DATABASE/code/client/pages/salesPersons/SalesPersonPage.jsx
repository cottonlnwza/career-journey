import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { toast } from "react-toastify";
import { getSalesPerson, createSalesPerson, updateSalesPerson } from "../../api/salesPersons.api.js";
import Loading from "../../components/Loading.jsx";

export default function SalesPersonPage({ mode }) {
    const { id } = useParams();
    const nav = useNavigate();
    const isView = mode === "view";
    const isCreate = mode === "create";

    const [form, setForm] = useState({ code: "", name: "", start_work_date: new Date().toISOString().slice(0, 10) });
    const [loading, setLoading] = useState(!isCreate);
    const [submitting, setSubmitting] = useState(false);
    const [err, setErr] = useState("");

    useEffect(() => {
        if (!isCreate) {
            getSalesPerson(id)
                .then(data => {
                    setForm({ 
                        code: data.code || "", 
                        name: data.name || "", 
                        start_work_date: data.start_work_date ? new Date(data.start_work_date).toISOString().slice(0, 10) : "" 
                    });
                    setLoading(false);
                })
                .catch(e => {
                    setErr(e.message);
                    setLoading(false);
                });
        }
    }, [id, isCreate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setErr("");
        try {
            if (isCreate) {
                const res = await createSalesPerson(form);
                toast.success("Sales Person created");
                nav(`/sales-persons/${res.id}`);
            } else {
                await updateSalesPerson(id, form);
                toast.success("Sales Person updated");
                nav(`/sales-persons/${id}`);
            }
        } catch (e) {
            setErr(e.message);
            toast.error(e.message);
            setSubmitting(false);
        }
    };

    if (loading) return <Loading />;

    const title = isCreate ? "New Sales Person" : isView ? "Sales Person Details" : "Edit Sales Person";

    return (
        <div className="form-page">
            <div className="page-header">
                <h3 className="page-title">{title}</h3>
                <div className="flex gap-2">
                    <Link to="/sales-persons" className="btn btn-outline">Back</Link>
                    {isView && <Link to={`/sales-persons/${id}/edit`} className="btn btn-primary">Edit</Link>}
                </div>
            </div>

            {err && <div className="alert alert-error">{err}</div>}

            <div className="card" style={{ maxWidth: 600 }}>
                <form onSubmit={handleSubmit} className="standard-form">
                    <div className="form-group">
                        <label className="form-label">Code <span className="required-marker">*</span></label>
                        <input
                            required
                            disabled={isView || (!isCreate)}
                            className="form-control"
                            value={form.code}
                            onChange={e => setForm({ ...form, code: e.target.value })}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Name <span className="required-marker">*</span></label>
                        <input
                            required
                            disabled={isView}
                            className="form-control"
                            value={form.name}
                            onChange={e => setForm({ ...form, name: e.target.value })}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Start Work Date <span className="required-marker">*</span></label>
                        <input
                            type="date"
                            required
                            disabled={isView}
                            className="form-control"
                            value={form.start_work_date}
                            onChange={e => setForm({ ...form, start_work_date: e.target.value })}
                        />
                    </div>
                    {!isView && (
                        <div className="form-actions" style={{ marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
                            <button type="submit" disabled={submitting} className="btn btn-primary">
                                {submitting ? "Saving..." : "Save"}
                            </button>
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
}
