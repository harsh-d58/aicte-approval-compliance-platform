/** Hosted prototype defaults to local business data. Live is an explicit opt-in. */
export const isDemoMode = process.env.NEXT_PUBLIC_PORTAL_MODE !== "live";
