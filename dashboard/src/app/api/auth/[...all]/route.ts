import { toNextJsHandler } from "better-auth/nextjs"
import { auth } from "@/lib/auth"

const handler = toNextJsHandler(auth)

export const { POST, GET } = handler