const paths = {
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4",
  menu: "M3 6h18M3 12h18M3 18h18",
  logout: "M9 4H4v16h5m5-12 4 4-4 4m-5-4h12",
  clock: "M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  institution: "M3 21h18M5 21V7l7-4 7 4v14M9 21v-4h6v4M8 9h1m6 0h1M8 13h1m6 0h1",
  search: "M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  map: "m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Zm6-3v15m6-12v15",
  document: "M14 2H5v20h14V7l-5-5Zm0 0v5h5M8 12h8m-8 4h8",
  user: "M20 21v-2a7 7 0 0 0-14 0v2M17 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  shield: "m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Zm-4 9 3 3 5-6",
  settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2",
  monitor: "M3 3h18v14H3V3Zm5 19h8m-4-5v5",
  send: "m22 2-7 20-4-9-9-4L22 2ZM11 13 22 2",
  alert: "m12 3 10 18H2L12 3Zm0 6v5m0 3v1",
  calendar: "M4 5h16v16H4V5Zm3-3v6m10-6v6M4 10h16",
  check: "m5 12 4 4L19 6",
} as const;

export type IconName = keyof typeof paths;

export default function Icon({ name, size = 24 }: { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={paths[name]} />
    </svg>
  );
}
