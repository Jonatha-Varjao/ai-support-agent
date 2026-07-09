import { z } from "zod";

const emailSchema = z.string().email("Email inválido");
export const loginSchema = z.object({ email: emailSchema });

