import * as customersService from "../services/customers.service.js";
// import { CreateCustomerBodySchema, UpdateCustomerBodySchema } from "../models/customer.model.js";
import { sendList, sendData, sendOne, sendCreated, sendOk, sendError } from "../utils/response.js";
import logger from "../utils/logger.js";

export async function listCustomers(req, res) {
  try {
    const result = await customersService.listCustomers(req.query);
    sendList(res, result);
  } catch (err) {
    logger.error("listCustomers failed", { error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), 500);
  }
}

export async function createCustomer(req, res) {
  // const parsed = CreateCustomerBodySchema.safeParse(req.body);
  // if (!parsed.success) return sendError(res, "Validation failed", 400, "VALIDATION_ERROR", parsed.error.flatten());
  try {
    const result = await customersService.createCustomer(req.body);
    sendCreated(res, result);
  } catch (err) {
    logger.error("createCustomer failed", { error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), 400);
  }
}

export async function updateCustomer(req, res) {
  // const parsed = UpdateCustomerBodySchema.safeParse(req.body);
  // if (!parsed.success) return sendError(res, "Validation failed", 400, "VALIDATION_ERROR", parsed.error.flatten());
  try {
    const code = decodeURIComponent(req.params.code || "");
    const existing = await customersService.getCustomerByCode(code);
    if (!existing) return sendError(res, "Customer not found", 404);
    // Merge so partial body does not overwrite other fields with undefined → NULL in DB
    const body = {
      code: req.body.code !== undefined ? req.body.code : existing.code,
      name: req.body.name !== undefined ? req.body.name : existing.name,
      address_line1: req.body.address_line1 !== undefined ? req.body.address_line1 : existing.address_line1,
      address_line2: req.body.address_line2 !== undefined ? req.body.address_line2 : existing.address_line2,
      country_id: req.body.country_id !== undefined ? req.body.country_id : existing.country_id,
      credit_limit: req.body.credit_limit !== undefined ? req.body.credit_limit : existing.credit_limit,
    };
    const result = await customersService.updateCustomerByCode(code, body);
    sendOk(res, result);
  } catch (err) {
    logger.error("updateCustomer failed", { code: req.params.code, error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), 400);
  }
}

export async function deleteCustomer(req, res) {
  try {
    const code = decodeURIComponent(req.params.code || "");
    const force = req.query.force === "true";
    const result = await customersService.deleteCustomerByCode(code, { force });
    if (!result) return sendError(res, "Customer not found", 404);
    sendOk(res, result);
  } catch (err) {
    logger.error("deleteCustomer failed", { code: req.params.code, error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), err?.statusCode ?? 500);
  }
}

export async function listCountries(_req, res) {
  try {
    const result = await customersService.listCountries();
    sendData(res, result.data);
  } catch (err) {
    logger.error("listCountries failed", { error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), 500);
  }
}

export async function getCustomer(req, res) {
  try {
    const code = decodeURIComponent(req.params.code || "");
    const row = await customersService.getCustomerByCode(code);
    if (!row) return sendError(res, "Customer not found", 404);
    sendOne(res, row);
  } catch (err) {
    logger.error("getCustomer failed", { code: req.params.code, error: err?.message ?? String(err) });
    sendError(res, err?.message ?? String(err), 500);
  }
}
