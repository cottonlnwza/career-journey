import * as receiptsService from "../services/receipts.service.js";
import { sendList, sendOne, sendCreated, sendOk, sendError } from "../utils/response.js";
import logger from "../utils/logger.js";

function errorStatus(err) {
  return Number(err?.statusCode || 500);
}

export async function listReceipts(req, res) {
  try {
    const result = await receiptsService.listReceipts(req.query);
    sendList(res, result);
  } catch (err) {
    logger.error("listReceipts failed", { error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), errorStatus(err));
  }
}

export async function getReceipt(req, res) {
  try {
    const id = decodeURIComponent(req.params.id || "");
    const result = await receiptsService.getReceipt(id);
    if (!result) return sendError(res, "Receipt not found", 404);
    sendOne(res, result);
  } catch (err) {
    logger.error("getReceipt failed", { id: req.params.id, error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), errorStatus(err));
  }
}

export async function createReceipt(req, res) {
  try {
    const result = await receiptsService.createReceipt(req.body);
    sendCreated(res, result);
  } catch (err) {
    logger.error("createReceipt failed", { error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), errorStatus(err));
  }
}

export async function updateReceipt(req, res) {
  try {
    const id = decodeURIComponent(req.params.id || "");
    const result = await receiptsService.updateReceipt(id, req.body);
    if (!result) return sendError(res, "Receipt not found", 404);
    sendOk(res, result);
  } catch (err) {
    logger.error("updateReceipt failed", { id: req.params.id, error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), errorStatus(err));
  }
}

export async function deleteReceipt(req, res) {
  try {
    const id = decodeURIComponent(req.params.id || "");
    const result = await receiptsService.deleteReceipt(id);
    if (!result) return sendError(res, "Receipt not found", 404);
    sendOk(res, result);
  } catch (err) {
    logger.error("deleteReceipt failed", { id: req.params.id, error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), errorStatus(err));
  }
}

export async function getNextReceiptNo(req, res) {
  try {
    const receiptDate = req.query.receipt_date || null;
    const receiptNo = await receiptsService.getNextReceiptNo(receiptDate);
    sendOk(res, { receipt_no: receiptNo });
  } catch (err) {
    logger.error("getNextReceiptNo failed", { error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), errorStatus(err));
  }
}

export async function printReceipt(req, res) {
  try {
    const id = decodeURIComponent(req.params.id || "");
    const result = await receiptsService.printReceipt(id);
    if (!result) return sendError(res, "Receipt not found", 404);
    sendOne(res, result);
  } catch (err) {
    logger.error("printReceipt failed", { id: req.params.id, error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), errorStatus(err));
  }
}
