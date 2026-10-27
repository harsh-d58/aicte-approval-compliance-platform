import type { PortalCollections } from "./types";

/** Pages depend on this contract, never on mock-data.ts directly. */
export interface PortalDataSource {
  getSnapshot(): Promise<PortalCollections>;
  getCollection<K extends keyof PortalCollections>(key: K): Promise<PortalCollections[K]>;
}

/** Prototype reads only. A future live adapter must query by authorised scope. */
export const portalDataSource: PortalDataSource = {
  async getSnapshot() {
    const { mockData } = await import("./mock-data");
    return structuredClone(mockData);
  },
  async getCollection<K extends keyof PortalCollections>(key: K): Promise<PortalCollections[K]> {
    const { mockData } = await import("./mock-data");
    if (key === "reportRuns") {
      const { getMockReportRows } = await import("./mock-reports");
      return structuredClone(mockData.reportRuns.map(run => ({
        ...run,
        rowCount: run.status === "COMPLETED" ? getMockReportRows(run.reportCode).length : 0,
      }))) as PortalCollections[K];
    }
    return structuredClone(mockData[key]);
  },
};
