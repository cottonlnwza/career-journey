import { z } from "zod";

export const CustomerSchema = z.object({
  id: z.number().int(),
  code: z.string(),
  name: z.string(),
  address_line1: z.string().nullable().optional(),
  address_line2: z.string().nullable().optional(),
  country_id: z.number().int().nullable().optional(),
  credit_limit: z.number().nullable().optional(),
});

export const CreateCustomerBodySchema = z.object({
  code: z.string().optional(),
  name: z.string().min(1),
  address_line1: z.string().optional(),
  address_line2: z.string().optional(),
  country_id: z.coerce.number().int().optional(),
  credit_limit: z.coerce.number().optional(),
});

export const UpdateCustomerBodySchema = z.object({
  code: z.string().optional(),
  name: z.string().optional(),
  address_line1: z.string().optional(),
  address_line2: z.string().optional(),
  country_id: z.coerce.number().int().optional(),
  credit_limit: z.coerce.number().optional(),
});

