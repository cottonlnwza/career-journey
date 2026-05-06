import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-toastify";
import { listSalesPersons, deleteSalesPerson } from "../../api/salesPersons.api.js";
import { formatDate } from "../../utils.js";
import Loading from "../../components/Loading.jsx";
import { ConfirmModal } from "../../components/Modal.jsx";

export default function SalesPersonList() {
    const [data, setData] = useState([]);
    const [meta, setMeta] = useState(null);
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [err, setErr] = useState("");

    const [deleteModal, setDeleteModal] = useState({ isOpen: false, item: null });

    useEffect(() => {
        setLoading(true);
        listSalesPersons({ search, page, limit: 10 })
            .then((res) => {
                setData(res.data);
                setMeta(res);
                setErr("");
                setLoading(false);
            })
            .catch((e) => {
                setErr(e.message);
                setLoading(false);
            });
    }, [search, page]);

    const handleSearch = (e) => {
        e.preventDefault();
        setPage(1);
        const form = new FormData(e.target);
        setSearch(form.get("q")?.toString() || "");
    };

    const confirmDelete = (item) => setDeleteModal({ isOpen: true, item });
    const doDelete = async () => {
        try {
            await deleteSalesPerson(deleteModal.item.id);
            toast.success("Sales Person deleted.");
            setPage(1);
            setSearch(search + " ");
            setTimeout(() => setSearch(search), 10);
        } catch (e) {
            toast.error(e.message);
        }
        setDeleteModal({ isOpen: false, item: null });
    };

    if (loading && !data.length) return <Loading />;

    return (
        <div className="list-page">
            <div className="page-header">
                <div>
                    <h3 className="page-title">Sales Persons</h3>
                    <div className="text-muted" style={{ fontSize: '0.9rem', marginTop: 4 }}>
                        Manage sales representatives
                    </div>
                </div>
                <Link to="/sales-persons/new" className="btn btn-primary">
                    <svg style={{ marginRight: 6 }} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                    New Sales Person
                </Link>
            </div>

            <div className="list-toolbar">
                <form className="search-form" onSubmit={handleSearch}>
                    <input name="q" defaultValue={search} placeholder="Search code or name..." className="form-control" />
                    <button type="submit" className="btn btn-primary">Search</button>
                    {search && (
                        <button type="button" className="btn btn-outline" onClick={() => { setSearch(""); setPage(1); }}>
                            Clear
                        </button>
                    )}
                </form>
            </div>

            {err && <div className="alert alert-error">{err}</div>}

            <div className="table-container">
                <table className="modern-table">
                    <thead>
                        <tr>
                            <th style={{ width: '15%' }}>Code</th>
                            <th style={{ width: '50%' }}>Name</th>
                            <th style={{ width: '20%' }}>Start Date</th>
                            <th style={{ width: '15%' }} className="text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((item) => (
                            <tr key={item.id}>
                                <td>{item.code}</td>
                                <td className="font-bold">{item.name}</td>
                                <td>{formatDate(item.start_work_date)}</td>
                                <td>
                                    <div className="table-actions">
                                        <Link to={`/sales-persons/${item.id}`} className="btn-icon text-primary" title="View">
                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                                        </Link>
                                        <Link to={`/sales-persons/${item.id}/edit`} className="btn-icon text-primary" title="Edit">
                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                                        </Link>
                                        <button onClick={() => confirmDelete(item)} className="btn-icon text-danger" title="Delete">
                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                        {data.length === 0 && !loading && (
                            <tr><td colSpan="4" className="text-center text-muted" style={{ padding: '2rem' }}>No sales persons found.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>

            <ConfirmModal
                isOpen={deleteModal.isOpen}
                onClose={() => setDeleteModal({ isOpen: false, item: null })}
                onConfirm={doDelete}
                title="Delete Sales Person"
                message={`Are you sure you want to delete ${deleteModal.item?.name}?`}
            />
        </div>
    );
}
