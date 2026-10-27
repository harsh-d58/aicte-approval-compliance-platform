import { mockData, mockMeta } from "./mock-data";
import { getReportRows } from "./report-rows";
import type { PortalCollections, ReportCode } from "./types";
export const getMockReportRows = (code:ReportCode,data:PortalCollections=mockData,now:string=mockMeta.now) => getReportRows(code,data,now);
