# Dashboard upgrade plan

## Post-build PRD recheck

The shared glass/3D/interaction foundation is implemented across ten roles. This does **not** close the complete M2 metric contract: explicit time remaining, processing/verification/lead-time definitions, delivery-rate denominators, committee aggregation and integration-delay metrics still need implementation/reconciliation (F10). Reporting date semantics and export auditability also remain open (F09/F11). P04 is therefore partial in the tracker. Historical comparisons remain unavailable until complete coverage exists. See the refreshed `missing_frontend.md`; 28 tests currently pass.


Status: core demonstration upgrade implemented and checked on 27 October 2026. Original design plan prepared 26 October 2026.

## Implementation record

Completed: all ten role datasets and dashboards; white glass navigation/cards with verified standard backdrop blur; CSS/SVG dimensional accents; readable type; desktop collapse/mobile focus-managed drawer; scoped filters and chips; multi-select status categories; coordinated filter versus highlight modes; hierarchical region/institution/stage exploration; focused charts, accessible data tables and record inspection; validated return context; browser-local saved views with rename/delete; same-view CSV export; snapshot/freshness labels and low-effects/reduced-motion styling.

Charts use lightweight native controls, CSS and SVG. No Power BI embedding, fabricated telemetry or WebGL dependency is required. Role-specific datasets use applications, visits, conditions, workflow versions, audit events or jobs rather than reusing application counters for every persona.

Historical trend and equal-period comparison controls explain unavailable coverage instead of inventing history. Live refresh/server queries, complete history, durable preferences and broad formal accessibility/performance certification remain dependencies. All ten dashboards were checked on desktop and a 390px phone viewport without page-level horizontal overflow; filter/highlight, data/focus dialogs, saved views, scope changes and low-effects fallback were exercised. Automated validation now has 28 checks.

Use [frontend_tracker.md](frontend_tracker.md) for current completion checkboxes. The sections below preserve the full design contract, including production and later optional enhancements.

Upgrade **all ten role dashboards** into a coherent glassmorphism interface with dimensional elements and Power BI-style exploration. The result should feel polished at the level of spacing, translucency, hover, focus, typography, chart transitions and record navigation—not simply add transparent cards to the existing screen.

This supplements [plan.md](plan.md) and [missing_frontend.md](missing_frontend.md). It preserves the complete P01–P54 product scope and the approved Home direction. It does not mark missing business workflows as implemented. The original planning text below describes the intended complete contract; the implementation record above distinguishes shipped demonstration behaviour from remaining service/validation work.

## 1. Scope and outcome

The primary delivery is P04 `/portal`, with distinct views for institutional representatives, scrutiny officers, regional officers, EVC coordinators, EVC experts, compliance officers, central administrators, policy administrators, auditors and system administrators. Role and scope come from the authorised session, not a URL role parameter.

Apply the same surfaces and interaction components to future module summaries, report viewers and operational consoles: applications, documents/renewals, EVC, compliance, notification delivery, escalation, reporting, audit and administration. Detail forms keep their own task-focused layouts while inheriting typography, controls, focus treatment and glass framing.

Expected experience:

1. Identify the active role, institution/region/visit and data snapshot immediately.
2. Read relevant KPIs and see the highest-priority work without scrolling past a large decorative banner.
3. Select a stage, region, owner or time window and understand how other visuals respond.
4. Drill from an aggregate into the exact authorised records that produced it.
5. Save a useful view, return from a record with its context intact, and export the same filtered results.
6. Enjoy depth, light and movement while still reading accurate values and using the interface by keyboard or touch.

## 2. Starting point and dependencies

Existing foundations: `DemoProvider`, scoped fixtures, `PortalShell`, shared UI components, `dashboardMetrics`, application read views, task/inbox/account pages and eight automated tests. Current dashboards have summary cards, limited drill-through and stage bars; they lack coordinated filters, historical analytics, saved views and most domain destinations.

Carry forward these fixes: nested route children stay mounted during session bootstrap; URL destinations are validated; scope filtering precedes record display; the GIF logo mask remains intact. Correct the audited navbar blur compatibility issue before treating glass rendering as verified.

Separate two work tracks:

| Track | Deliverable | Dependency |
| --- | --- | --- |
| Dashboard platform | Glass design system, responsive layout, metrics, filters, charts, detail drawers, saved views and accessible alternatives | Can start against fictional data now |
| Business destinations | Application forms/review, documents/OCR, EVC, evidence verification, reports and audit actions | Implement the relevant pages from `plan.md`; expose links when their targets work |
| Live service integration | Scoped queries, approved identity, real histories, provider outcomes and durable preferences | Approved APIs, server permissions and policy decisions |

During the prototype, unresolved actions open a meaningful labelled preview or show a clear availability explanation. A card must never navigate to an unbuilt route or display a fake successful action.

## 3. Visual direction

### Palette and materials

Use a light analytical workspace with warm peach illumination, subtle lavender depth and navy typography. Connect it to Home’s orange-to-white gradient and frosted navigation. Keep saturated colour for selection, status and important actions.

| Token | Initial proposal | Intended use |
| --- | --- | --- |
| Canvas | `#f5f5fa`, with very soft peach/lavender background gradients | Dashboard background; gradients stay static |
| Primary text | `#20224f` | Headings, metric values, active navigation |
| Secondary text | `#626b80` | Supporting text; verify actual contrast after blending |
| Accent | `#a94f25` | Primary actions and selected slicers |
| Glass surface | White at 72–84% opacity | Dashboard cards and panel frames |
| Strong glass | White at 88–94% opacity | Sticky navigation, drawers and dense content frames |
| Plot/table interior | White at 96–100% opacity | Axes, labels, tabular data and fine marks |
| Glass edge | White highlight plus a subtle navy outer border | Surface definition on both light and warm backgrounds |
| Positive | Muted green, initially `#287457` | Verified/completed outcomes |
| Warning | Dark amber, initially `#94651b` | Due soon, pending clarification or attention |
| Negative | Muted red, initially `#b13e46` | Overdue, failed and explicitly negative outcomes |
| Informational | Blue, initially `#426caa` | Assigned/upcoming/information states |

These are starting tokens, not a contrast certification. Validate every final foreground/background pair, including hovered and dimmed chart states. Replace the current regex-based badge tones with explicit status definitions.

### Glass surface specification

- Use three consistent surface levels: navigation, analytical card and floating overlay. Define them once and reuse them across all roles.
- Navigation: approximately 20–24px blur; analytical card frames: 12–16px blur; overlays: 20–24px blur. Use opacity to preserve readability rather than stacking more blur layers.
- Radius: 12–16px for panels, 10–12px for KPI cards and 8px for controls. Keep one consistent panel radius within a dashboard.
- Give glass cards a faint top-edge highlight, soft ambient shadow and a restrained darker outer edge. Selected cards gain an accent edge and visible selection marker.
- Use a translucent outer card with a nearly opaque plot/table interior so content remains clear over gradients.
- Write the WebKit backdrop declaration before the standard declaration, then inspect the generated CSS and computed browser style. Test actual blur, not just a tint that resembles glass in a screenshot.
- Provide a solid high-contrast surface when backdrop blur is unavailable, reduced transparency is requested or the low-effects mode is enabled.

Illustrative starting rule, to be tuned in the shared component:

```css
.glassPanel {
  background: rgb(255 255 255 / 78%);
  border: 1px solid rgb(255 255 255 / 75%);
  border-radius: 14px;
  box-shadow:
    0 10px 30px rgb(32 34 79 / 6%),
    0 0 0 1px rgb(32 34 79 / 5%),
    inset 0 1px 0 rgb(255 255 255 / 90%);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
}
```

### Typography and spacing

- Retain Noto Sans. Use approximately 28–32px page titles, 16–18px panel titles, 32–40px KPI values and 13–14px essential labels/body text. Essential chart/table labels should generally be at least 12px.
- Replace the current frequent 8–10px labels and faint grey text where they carry information.
- Use a 4px spacing system: 8px within related controls, 12–16px within small groups, 20–24px panel padding and 24px grid gaps on desktop. Reduce panel padding to 16px on phones.
- Use tabular numerals and consistent decimal precision. Reserve the KPI value width so filtering does not shift card layout.
- Avoid forced zero padding such as `01` for ordinary counts; display `1`, `0`, `128`, and an explicitly defined compact format for large values.
- Specify exact states for default, hover, keyboard focus, pressed, selected, disabled, loading, updating, empty, error and stale. A raised appearance alone does not make a panel clickable.

## 4. 3D elements and motion

### Depth system

| Level | Element | Treatment |
| --- | --- | --- |
| Background | Ambient light pools | Static CSS gradients; low contrast; no pointer tracking |
| Surface | KPI and analytical panels | Layered glass, edge highlight, shadow and a 2–4px elevation change |
| Accent | Role emblem or a primary KPI icon | CSS/SVG isometric layers with visible side faces and soft shadow |
| Context | Selected workflow or committee model | Optional shallow isometric diagram, with a labelled flat equivalent |
| Overlay | Filter drawer, tooltip, detail panel | Clear elevation and focus handling; text remains flat and stable |

Use dimensional styling for cards, icons and workflow context. Quantitative plots retain consistent axes and directly comparable mark lengths/areas. Place charts in raised glass frames rather than changing the apparent sizes of their values through perspective.

### Role accents

Institution: layered campus/building emblem. Scrutiny: stacked review sheets. Regional: raised regional tiles. Coordinator: layered calendar with committee markers. Expert: committee/visit emblem. Compliance: shield and evidence stack. Central: layered regional overview. Policy: versioned workflow nodes. Auditor: linked event blocks. System: service/queue nodes.

Build these as reusable CSS/SVG compositions based on the current icon system. They must convey role/context without obscuring data. Keep the default header accent small; allow at most one larger contextual 3D illustration per dashboard section.

### Motion contract

- Button/card feedback: 120–180ms; chart filter transitions: 200–350ms; drawers: 180–240ms. Treat these as tuning ranges.
- Fine-pointer KPI tilt: optional, maximum roughly 1.5–2 degrees, 800–1000px perspective and a 2–4px lift. Tilt the decorative layer while keeping labels and numbers easy to read.
- Provide equivalent focus and selection states without tilt. Disable pointer tilt on touch/coarse-pointer devices and under reduced motion.
- Use one animation frame loop only while an effect is active; avoid React state updates for every pointer movement. Clean up observers, chart events and animation frames on unmount.
- Animate valid value changes once. Keep previous values visible during refresh and show an updating state. There is no decorative random counter or fabricated live pulse.
- Reduced motion uses immediate value updates and simple fades where appropriate. Low-effects mode uses opaque surfaces, no tilt and no ambient animation.
- Begin with CSS/SVG depth. A separately loaded WebGL scene is a later optional enhancement only if a real use case and device measurements justify its cost; the complete dashboard must work without it.

## 5. Shared dashboard layout

Desktop layout uses a 12-column canvas, a compact collapsible glass sidebar, a 64–72px topbar and a content width around 1440–1600px where space permits.

```text
Sidebar | Role / active scope / breadcrumb          Freshness / help / account
        | Title + compact role context              Saved view / Refresh / Export
        | Date window + authorised slicers + applied-filter chips + Reset
        | KPI 1         KPI 2         KPI 3         KPI 4
        | Primary interactive chart (8 columns) | Priority/action panel (4)
        | Secondary comparison (6)              | Domain chart (6)
        | Filtered record table + pagination + selected-record detail drawer
```

- Reduce the existing large welcome panel to a compact context strip. At a representative desktop viewport, the initial screen should reveal KPIs and meaningful analytical content.
- Make the active role and exact institution/region/visit visible in the persistent shell. Locked access scope and user-chosen analytical filters must look different.
- Keep the filter summary accessible while scrolling. On small screens, use a compact summary and a Filters button rather than a wide fixed toolbar.
- Show three or four well-chosen KPIs initially. Extra measures belong in a secondary row or domain tab, with the same semantic definitions.
- Page sections can be Overview, Workload/Timeline, and Records where useful; section changes retain compatible filters.
- Each chart panel gets a title, metric definition/info action, current context, selection indication and menu. Use meaningful domain titles rather than Chart 1/Graph 2.

## 6. Power BI-style exploration contract

The inspiration is the interaction model: slicers, coordinated selections, focused detail pages and saved views. Microsoft documents filtering/highlighting and drillthrough as different operations; implement those differences explicitly. [Filters and highlighting](https://learn.microsoft.com/power-bi/create-reports/power-bi-reports-filters-and-highlighting), [drillthrough](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-drill-through-buttons).

| Interaction | Required dashboard behaviour |
| --- | --- |
| Slicers | Date/as-of window, academic year, authorised region/institution, stage, status, owner, visit or document category where relevant. Hide irrelevant dimensions and show locked scope clearly. |
| Cross-filter | Selecting a chart category narrows compatible visuals, KPIs and the record table. Add a removable filter chip naming the selection. |
| Cross-highlight | Dim unrelated marks while retaining the visible comparison population. Keep totals unchanged and label the highlighted subset. |
| Multi-select | OR within the same dimension, AND across different dimensions. Provide a visible multi-select control and a keyboard/touch equivalent to modifier-click. |
| Drill-down/up | Navigate a permitted hierarchy within a chart, retain breadcrumbs and expose a clear Drill up control. |
| Drill-through | Open a record list, report or case with the selected entity/filter context. Back restores filters, hierarchy, sort and relevant scroll position. |
| Tooltip | Show exact value, denominator, date/snapshot, definition and relevant context on hover or focus. Offer tap-to-inspect and a persistent detail option. |
| Time brush | Select a date interval in an event-based trend, preview it, then Apply. Show which measures use an event window versus an as-of snapshot. |
| Compare | Explicit current-versus-prior period with equal duration and visible bounds. Display unavailable comparison data honestly. |
| Focus mode | Expand one visual into an accessible panel without losing selection/filter context. Return restores the page position. |
| Show data | Open an accessible table of the exact visible values and contributing records where permitted. |
| Reset | Separate Clear chart selection, Reset filters and Restore default view. Never clear the user’s authorised role/scope. |
| Saved views | Save/rename/delete a local view containing permitted filters, sections, visual configuration and layout. Clearly identify browser-local persistence. |
| Copy view link | Copy a validated analytical URL; the recipient still needs their own session and scope. A shared URL grants no access. |
| Refresh | Refresh from the selected adapter, retain context, update freshness, and announce failures. Demo refresh restores the defined synthetic snapshot. |
| Export | Export the same filtered authorised data with reporting period, timestamp and filter summary. Open a genuine export flow when implemented. |

### Selection rules

Use one dashboard interaction controller. Each visual declares its dataset, entity grain, dimensions, compatible interactions and drill targets. Chart events dispatch typed selection actions to that controller; they do not mutate neighbouring charts independently.

Prevent confusing self-filtering: keep the source visual’s comparison categories visible when applying its own selection. Other compatible visuals respond through the shared controller. Each visual declares Filter, Highlight or Ignore for every supported selection type. A region click must not silently reinterpret a document-expiry bucket.

For a highlight interaction, preserve the base total and show “selected subset / displayed total”. For a filter interaction, recompute the filtered totals and expose the applied chip. Clear selections by clicking the selected category again, using its chip, or an explicit Clear selection control. Background clicks must not accidentally clear other controls.

Changing scope cancels pending queries, clears incompatible filters/highlights and removes stale records before rendering the new context. Preserve only preferences that remain valid for the new assignment.

## 7. Filters, views and navigation state

Create a typed, versioned `DashboardQuery` with:

- `section`, `asOf`, `dateFrom`, `dateTo`, `academicYear`;
- permitted dimension selections: `regionIds`, `institutionIds`, `stageCodes`, `statuses`, `ownerIds`, `visitIds`, `documentTypes`;
- compatible chart selection, hierarchy path, sort, pagination and comparison mode;
- a schema version so stored views/URLs can be migrated or reset safely.

Authentication and effective permissions remain outside this query. Validate IDs, enums, date bounds and pagination against the active scope. Explain invalid/incompatible saved selections and offer to remove them.

Use URL state for applied filters and navigation context. Use replacement updates for transient search/slider previews; create history entries for meaningful applied views so browser Back is useful. Store saved views under a versioned user/role/scope key. Store view definitions rather than copies of case data. Revalidate each saved view when opened.

A record drill-through carries an approved, same-origin return context. Expand the existing route allowlist only when the target page is implemented. When reopening the dashboard, restore the source view and keep the filter summary visible.

Example: a regional officer selects an overdue scrutiny bar → a Stage: Scrutiny chip and Overdue: Yes chip appear → the permitted case table changes → Open records shows those exact cases → opening one case and returning restores that selection.

## 8. Semantic metrics and honest data

Every KPI/chart needs a definition registry: identifier, business definition, source collection(s), grain, date semantics, allowed dimensions, denominator, units, precision, good/bad direction, permissions, drill target and empty/unavailable handling.

| Measure | Proposed semantic rule to validate |
| --- | --- |
| Active applications | Retain the existing sample predicate initially, label it, and obtain approval on whether an approved-but-not-closed case remains active. |
| Action required | Count actual role-owned actionable items, not every open condition. Deduplicate items shown through more than one source. |
| Application/stage age | Use submission/stage-entry timestamps; drafts and missing timestamps show Not applicable/Unavailable rather than a fabricated zero. |
| Overdue count/duration | Evaluate applicable outstanding records against the shared clock; retain the underlying review state separately. Closed records do not keep accruing active overdue time. |
| Upcoming visits | Define which proposed/confirmed visits count and label the states separately; a proposed slot is not a confirmed booking. |
| Compliance completion | Separate submitted evidence, verified outcomes and authorised closure. Show numerator and denominator. |
| Document expiry | Use the configured document types and authoritative applicable version. Exclude non-expiring categories from expiry rates. |
| Notification delivery | Use provider-confirmed outcomes; display the denominator and distinguish accepted/sent from delivered. |
| Processing/verification duration | Use completed start/end pairs; state whether the statistic is median, percentile or average and disclose excluded incomplete records. |

Pipeline: authorised scope → validated query → domain selectors → shared semantic measures → charts/KPIs/tables → exports. Use that same pipeline for all eight report categories.

Do not apply one application submission-date filter indiscriminately to all domains. Distinguish inventory/backlog measures **as of** a timestamp from events **during** a period. Use start-inclusive/end-exclusive timestamps internally and display understandable date bounds in IST. Each visual exposes the relevant date field in its info/details panel.

### Fixture expansion

The current small snapshot cannot support credible daily trends or performance percentiles. Extend it with explicitly fictional, coherent histories: submissions, stage entry/exit, assignment, EVC readiness/confirmation/completion, evidence/verification, notification attempts and closure events. Preserve relationships and deterministic timestamps.

- Keep the fixed demo clock visible. Generate aggregates from the events, not hand-entered chart points.
- Provide enough records to exercise region/owner/stage/date filters, without implying they represent operational capacity.
- Cover normal, zero, missing, stale, overdue, completed, conflicted and failed states. Zero means no matching records; unavailable means insufficient data.
- Show “Trend unavailable for this snapshot” until the required histories exist. A comparison tile with no prior sample must not display an invented percentage change.
- Keep sample APH deadlines/targets labelled. Defer SLA target lines until the configured target is known.

## 9. Role-by-role dashboard specifications

Each role uses the shared glass shell and interaction system, with its own record scope, priorities, charts and actions. The listed metrics are the intended design; final statutory definitions and permissions require the PRD’s policy decisions.

### 9.1 Institutional representative

- **KPIs:** active applications, responses due, upcoming confirmed/proposed visits separated, documents due for renewal.
- **Visuals:** application stage distribution; obligation/deadline timeline; document validity by applicable type. Add historical submission/completion trends only after event fixtures exist.
- **Records/actions:** application register, drafts to resume, deficiency responses, evidence requests, upcoming visits and renewals. Link to P10/P13/P20/P25/P31 when available.
- **Slicers:** authorised institution/campus, academic year, application, stage/status and due window. Institutional scope remains locked.
- **3D accent:** small layered campus emblem and elevated next-action tile.
- **Acceptance example:** selecting Returned for deficiency filters both the count and case list; opening a notice preserves the selected application context; evidence submission never appears as verified closure.

### 9.2 Scrutiny officer

- **KPIs:** assigned active cases, overdue stages, returned/resubmitted cases, reviews awaiting action.
- **Visuals:** stage-age bands; assigned workload by stage/status; return/resubmission history; source-linked review findings by category when available.
- **Records/actions:** urgency-ordered review queue, document/check workspace, deficiency issue/resolve and guarded next-stage recommendation. Link P05/P12/P13/P18.
- **Slicers:** assigned cases, stage, age band, type, year and review state; no unrestricted region-wide case browsing.
- **3D accent:** review-sheet stack with a restrained selected-layer effect.
- **Acceptance example:** choosing an overdue age band opens exactly the assigned review cases; a blocked transition exposes the guard/reason rather than changing state.

### 9.3 Regional officer

- **KPIs:** regional active pendency, overdue stages, EVC deadline risks and open escalations.
- **Visuals:** institution-by-stage matrix; officer workload/age bands; EVC readiness versus deadline; regional completion trend if histories support it.
- **Records/actions:** assign/reassign case, open scrutiny, select committee, inspect scheduling risk, resolve permitted escalations. Link P09/P12/P23/P25/P34.
- **Slicers:** assigned region/subregion where permitted, institution/type, application type/year, owner, stage and overdue window.
- **3D accent:** raised regional tile cluster; use an ordered matrix before introducing a geographical map requiring authoritative boundaries.
- **Acceptance example:** selecting one officer highlights their load, filters the record list and leaves the visible comparison population explicitly identified.

### 9.4 EVC coordinator

- **KPIs:** visits awaiting availability, proposed/unconfirmed visits, deadline risks and outstanding committee records.
- **Visuals:** scheduling pipeline by state; participant-confirmation matrix; visit calendar/time distribution; report completion queue.
- **Records/actions:** request availability, inspect exact selected membership, recommend/confirm slots, monitor invitations, postpone/reschedule, record completion and open draft records. Link P21–P29 within permissions.
- **Slicers:** assigned coordinator, visit/application, institution, deadline window and scheduling/report state.
- **3D accent:** layered calendar tile and officer-selected committee markers; selection authority is shown separately from coordination controls.
- **Acceptance example:** a proposed visit shows missing/stale availability and precise blockers; confirmation rechecks every selected expert and the institution and can return a conflict.

### 9.5 EVC expert

- **KPIs:** assigned upcoming visits, availability confirmations due, observations due and records awaiting that expert’s review.
- **Visuals:** personal assigned-visit timeline; availability status; observation/review progress with clearly defined totals.
- **Records/actions:** submit availability, open authorised case material, record observations, inspect draft sources and submit a permitted review. Link P24/P27/P29.
- **Slicers:** assigned visit, date window and personal action state. Display the exact active visit in the shell and enforce assigned-material access.
- **3D accent:** compact committee/visit emblem; no institution-wide analytical population outside the assignment.
- **Acceptance example:** changing from EVC 001 to EVC 002 removes previous-visit records and changes KPIs, observations and review tasks consistently.

### 9.6 Compliance officer

- **KPIs:** evidence awaiting review, overdue conditions, clarification required and verified/closed conditions separately.
- **Visuals:** condition state by deadline band; evidence turnaround distribution; document-expiry/renewal queue; review workload by authorised institution.
- **Records/actions:** inspect original condition/decision and immutable evidence versions, verify/request clarification, close/reopen with reason and review renewal. Link P19/P20/P30/P31.
- **Slicers:** institution/region within assignment, condition/document type, reviewer, due window and verification state.
- **3D accent:** shield and evidence-card layers with a stable status marker.
- **Acceptance example:** an overdue clarification remains Clarification required with a separate overdue flag; uploading a file does not improve a verified-compliance KPI.

### 9.7 Central administrator

- **KPIs:** cross-region active cases, overdue stage rate, completed EVCs, verified compliance and case closure measures with denominators.
- **Visuals:** region-by-stage matrix; received versus closed event trend; stage bottlenecks/age distribution; EVC/compliance comparison by region.
- **Records/actions:** drill region → institution → application; open permitted consolidated reports and supporting records. Configuration actions follow separately granted permissions.
- **Slicers:** authorised regions, institution/application type, year, stage and explicit event/as-of period.
- **3D accent:** layered regional overview with light depth; focus the content on comparisons.
- **Acceptance example:** selecting a region updates the same records used for the regional view and report export; global context never implies unrestricted privileged actions.

### 9.8 Policy/configuration administrator

- **KPIs:** published workflow versions, drafts awaiting validation, planned effective changes and configurations awaiting approved publication.
- **Visuals:** version/effective-date timeline; draft/published/retired distribution; impacted-case counts by pinned workflow; validation findings by category.
- **Records/actions:** inspect/clone/edit/validate/version-review/publish within authority. Link P42–P46. No statutory case-transition controls are added merely because this role edits configuration.
- **Slicers:** application type, APH reference, workflow/version, configuration category, effective-date window and publication state.
- **3D accent:** versioned workflow-card stack; an accessible stage list remains the editing/inspection path.
- **Acceptance example:** previewing a new rule shows affected categories; publishing creates a new version and does not silently rewrite existing cases.

### 9.9 Auditor

- **KPIs:** visible audit events, designated actions with/without expected audit evidence, verification mismatches where genuinely evaluated, and permitted export activity.
- **Visuals:** event timeline; actor/action/entity matrix; verification/anchor state distribution with optional ledger availability; closure authority/history summaries.
- **Records/actions:** read event details, inspect source versions, verify permitted fingerprints and export redacted history. Link P37/P38/P39. Views are read-only.
- **Slicers:** authorised scope, case/entity, action, actor, period, verification state and correlation reference.
- **3D accent:** linked event blocks, labelled as illustrative when sample hashes are used.
- **Acceptance example:** a mismatch is an integrity finding with a source/version and time, not an assertion that a document is forged; disabled ledger status does not block audit browsing.

### 9.10 System administrator

- **KPIs:** failed jobs, queued/retrying jobs, stale/failed connectors and delivery/processing measures backed by known outcomes.
- **Visuals:** job state by queue; retry/failure timeline; connector freshness matrix; measured processing durations and throughput when source telemetry exists.
- **Records/actions:** inspect job/error/attempt history, perform authorised retries, inspect integration status and manual fallback. Link P33/P47/P48. Secrets remain outside frontend models.
- **Slicers:** queue/type, connector, status, time window, retryability and correlation ID.
- **3D accent:** lightweight service/queue node diagram with explicit unknown/stale indicators.
- **Acceptance example:** a retry remains queued/processing until the adapter reports an outcome; demo telemetry is labelled and never presented as measured production uptime.

## 10. Shared report and domain analytics

Extend the component system to all eight report variants. The report data, dashboard cards and record tables must share filter/metric definitions.

| Report variant | Default analytical visual | Primary drill target |
| --- | --- | --- |
| Region performance | Region/stage matrix plus processing-duration comparison | Regional scoped records |
| Application pendency | Stage/age-band bars and deadline distribution | Application register/workspace |
| EVC status | Visit-state timeline and readiness/deadline matrix | Visit/committee/scheduling workspace |
| Undertaking compliance | Verification-state/deadline distribution | Condition/evidence workspace |
| Document validity | Applicable expiry-window/type distribution | Document/version/renewal workspace |
| Overdue actions | Owner/action-type age bands | Source action and escalation |
| Notification delivery | Channel/outcome/attempt distribution | Notification attempt history |
| Case closure | Closure event trend and authority/outcome table | Historical decision/closure record |

Each offers a visible data table, source timestamp and metric definition. A complex chart is optional when a small table communicates the data better. PDF/print mode flattens glass and shadows, expands labels and includes filters, reporting period, snapshot and generation time. CSV/XLSX contain real rows, not screenshots or renamed text files.

## 11. Controls and content specification

| Control | Required states and meaning |
| --- | --- |
| Date selector | Presets/custom window, validation, explicit time basis, Apply/Cancel and visible bounds |
| Scope selector | Authorised assignments only; exact scope name; confirmation of changed context |
| Filter chip | Dimension/value, clear action and accessible label; locked access chips cannot be cleared |
| Metric card | Value/unit, context, definition, freshness, optional genuine comparison and a meaningful destination |
| Chart menu | Focus, Show data, metric details and authorised export; clear availability explanations |
| Detail drawer | Source records and count reconciliation; close/Escape/focus restoration; contextual record links |
| Saved view menu | Save as, rename, restore, delete local definition and default view; explain incompatible filters |
| Refresh | Idle/updating/updated/failed/stale; retain working context and show the actual snapshot time |
| Export | Available/queued/processing/completed/failed/expired according to a real or explicitly simulated job |
| View actions | Label the actual destination: Review deficiency, Open visit, View evidence; avoid a generic Review button that only opens unrelated context |

Copy rules: pluralise counts; show date plus time and IST for deadlines; qualify sample policy and synthetic histories; define every percentage; show the comparison period; explain zero versus unavailable; keep status labels consistent with the case model; distinguish proposed, submitted, verified and approved. A rule-based insight sentence must link to the records behind it. Natural-language AI analysis is a later independent feature, not an implied capability of the redesign.

## 12. Component and code architecture

Recommended chart foundation: **Apache ECharts with modular imports**, behind a small typed React adapter. Start with SVG for the bounded dashboard datasets; benchmark a Canvas renderer only for a measured dense-visual need. ECharts documents modular loading, renderer choices and an event/action API suitable for the planned controller. [Modular imports](https://echarts.apache.org/handbook/en/basics/import/), [renderer guidance](https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/), [events/actions](https://echarts.apache.org/handbook/en/concepts/event/).

Before adopting the dependency, run a compatibility/bundle/accessibility spike in this actual Next.js 16.4/React 19.3 project. Pin the tested version in the lockfile. Use the existing React/CSS Modules stack; add no additional state or animation library until the spike identifies a concrete need.

Proposed structure, all relative to `frontend/`:

```text
app/portal-ui/dashboard/
  DashboardShell.tsx          DashboardHeader.tsx
  DashboardToolbar.tsx        FilterDrawer.tsx
  GlassPanel.tsx              DepthIcon.tsx
  KpiCard.tsx                 ChartPanel.tsx
  ChartAdapter.tsx            ChartDataTable.tsx
  SelectionChips.tsx          InsightPanel.tsx
  DetailDrawer.tsx            SavedViewMenu.tsx
  DashboardBoundary.tsx       dashboard.module.css
  glass.module.css           charts.module.css
lib/portal/dashboard/
  definitions.ts             metrics.ts
  selectors.ts               filters.ts
  interactions.ts            route-context.ts
  saved-views.ts              chart-theme.ts
  roles/institution.ts       roles/scrutiny.ts
  roles/regional.ts          roles/coordinator.ts
  roles/expert.ts            roles/compliance.ts
  roles/central.ts           roles/policy.ts
  roles/auditor.ts           roles/system.ts
```

- Keep a common `DashboardDefinition` describing permitted KPIs, visuals, grain, slicers, interactions, priorities and drill destinations for each role. Avoid ten copied pages with slightly different headings.
- Keep business selectors independent of chart options so they can be unit tested and reused by reports.
- Split the current large `portal.module.css` gradually; preserve existing task/application/account styling while migrating dashboard surfaces.
- Adapt the current `dashboard-metrics.ts` into the shared metric registry without changing definitions silently.
- Initialise chart instances in client components, resize through `ResizeObserver`, update options deliberately, and dispose cleanly. Do not reinitialise charts on every filter change.
- Preserve Suspense boundaries and the pending-route rendering fix. Read the installed Next.js guidance before adding dynamic chart imports or changing route structure.
- Keep adapter mode, snapshot clock and data provenance explicit. Mock pages continue to avoid importing seed files directly.

## 13. Responsive and accessible behaviour

| Width/context | Layout and effects |
| --- | --- |
| Large desktop | 12-column grid; four KPIs; 8/4 and 6/6 chart layouts; optional persistent filter rail |
| Small desktop/tablet | Reduced sidebar or drawer; two-column KPI grid; charts wrap by usable plot width |
| Phone | Two KPI columns when readable, otherwise one; single-column analytical panels; filter drawer with Apply/Reset; tap-friendly detail sheets |
| Zoom/reflow | Preserve reading order and labels; table scroll stays inside its region; no whole-page horizontal overflow |
| Reduced motion/transparency | Static depth, immediate updates and stronger opaque surfaces; all controls remain available |
| Print/export | Flat backgrounds, expanded labels, coherent pagination and visible data/filter metadata |

Keyboard: operate filters, chart selection, drill actions, visual menus, focus mode and data tables without requiring a pointer or right-click. Provide an accessible record/table alternative to every interactive plot. Use roving focus only where the chosen widget pattern requires it; preserve visible focus rings outside rounded/clipped card edges.

Tooltips work on focus and touch; critical information is also available persistently. Announce applied-filter/result-count and refresh changes politely without reading every chart mark. Status uses text plus shape/icon, not colour alone. Aim for WCAG 2.1 AA: check 4.5:1 ordinary text and 3:1 large text/meaningful UI graphics where applicable, over the actual composited glass backgrounds. Verify 200%/400% zoom and a 320px reflow case. Use approximately 44px touch targets for primary controls.

## 14. Performance and operational states

Set measurable budgets during the spike; the following are proposed engineering targets, not current achievements or production capacity claims:

- On a representative development device with 1,000 coherent demo cases, aim for filter-to-visible-update within 200ms for local selectors and ordinary chart updates. Record the device, dataset, measurement method and p95 result.
- Target responsive pointer/focus interactions and avoid long main-thread tasks above 50ms during ordinary filter changes; profile rather than assuming blur is free.
- Lazy-load chart types by dashboard need, measure the route’s compressed JS increase, and record an agreed bundle budget before rolling the engine into all roles.
- Limit simultaneous backdrop layers; virtualise or paginate large record sets and defer offscreen charts. Aggregate/downsample with an explicit policy and retain exact tabular values.
- Avoid continuous expensive 3D animation, polling or chart resize loops. Pause nonessential work when hidden; clean up on navigation.
- Use a single cancellation-aware refresh cycle and request identity; late results from a previous scope cannot overwrite the current view.

Each panel must cover: initial skeleton, updating with previous data retained, no records, no matches, insufficient history, stale snapshot, missing permission, source failure/retry and unavailable comparison. Page-level failures must not silently blank every panel. A connector with unknown freshness stays Unknown, not Healthy.

## 15. Delivery phases and implementation gates

| Phase | Work | Gate before proceeding |
| --- | --- | --- |
| D0 — Contract and baseline | Inventory role metrics/permissions, fix existing query/copy/glass issues, capture current desktop/mobile references, define data semantics | Role/scope and metric registry reviewed; missing destinations recorded |
| D1 — Design foundation | Glass tokens, panel levels, 3D icon/depth primitives, typography/control states, opaque fallback | Computed blur verified; contrast/focus/reduced-effects pass on a sample dashboard |
| D2 — Semantic/query foundation | Deterministic event fixtures, domain selectors, date semantics, typed URL filters, shared selection controller | Counts reconcile; invalid/out-of-scope inputs fail safely; no invented historical trend |
| D3 — Chart spike and reference dashboard | Modular chart adapter; institution dashboard with KPI, stage chart, deadline view, record table and drawer | Keyboard/touch interaction, source rows, bundle and performance measurements pass |
| D4 — Work/review roles | Scrutiny, regional and compliance dashboards, actionable priorities and module drill destinations | Role-specific filters, age/deadline logic and access boundaries verified |
| D5 — EVC roles | Coordinator and expert dashboards, availability/readiness/report-state visuals and visit scope handling | Exact committee scope, stale/conflict/no-slot states and source navigation verified |
| D6 — Oversight/operations | Central, policy, auditor and system dashboards with their dedicated visual definitions | All ten role views complete; no generic institutional copy or irrelevant controls remain |
| D7 — Exploration and reporting | Saved views, focus mode, show-data, comparison, eight report views and matching exports | Bookmark/Back restoration, filter/highlight semantics and export reconciliation pass |
| D8 — Finish and rollout | Depth/motion polish, responsive/a11y/performance tests, documentation and final walkthrough | Role matrix and state matrix pass; remaining external dependencies explicitly labelled |

Basic coordinated filtering and drill-through ship with D3, not only as late polish. Saved-view/export enhancements can progress in D7 after the shared data/selection contract is stable. Business forms and domain destinations are implemented alongside the corresponding phases from the main plan. A dashboard can be visually complete while a destination remains explicitly unavailable; functional completion requires that destination and action to work.

Roll out the reference dashboard first, review it against the detailed state checklist, then apply its primitives across the remaining roles. Avoid a one-shot rewrite of the whole portal. Preserve the existing Home and functional read views throughout migration.

## 16. Test and acceptance matrix

| Area | Required evidence |
| --- | --- |
| All ten roles | Correct metrics, priorities, filters, active scope and destinations for every authorised assignment |
| Metric integrity | Same scoped/filtered records produce KPI, chart, table and export totals; documented definitions and time bases |
| Selection | Filter versus highlight verified; OR/AND rules; source-visual context; clear/reset; incompatible interaction handling |
| Navigation | Chart → list → record → Back preserves valid context; invalid/deep/shared URLs cannot grant access |
| Saved views | Save/restore/rename/delete, schema migration and role/scope incompatibility handling |
| Histories | Genuine zero versus unavailable; missing prior period; drafts; terminal cases; deadline boundaries; sample timezone |
| EVC/compliance | Proposed versus confirmed, exact committee participants, stale/conflict handling, evidence versus verification distinctions |
| Async data | Loading, cancellation, failed refresh, stale data, partial failure and late response from a previous assignment |
| Visual fidelity | Glass blur in generated CSS/browser, edge/shadow consistency, no text tilt/clipping, restrained 3D and every control state |
| Accessibility | Keyboard-only and screen-reader spot checks; chart data alternatives; contrast; zoom/reflow; touch; reduced motion/effects |
| Performance | Recorded baseline versus upgraded route bundle, interaction latency, paint/scroll behaviour and cleanup |
| Exports | Actual supported file content, correct permitted rows, metadata, snapshot and failure/expiry behaviour |

Extend the eight existing tests rather than treating them as dashboard coverage. Add pure selector/query/interaction tests, component tests for control states and browser journeys for all roles. Maintain deterministic fixtures for screenshot comparisons; inspect at least 1440px desktop, 1024px tablet and 390px phone layouts, plus the narrow reflow case. Re-run lint, tests and production build at each integrated phase.

Final walkthrough must demonstrate: a regional workload selection changes dependent views; an institution opens the precise response/evidence context; an expert scope switch removes previous-visit material; a saved view restores its filters; a report export reconciles with the dashboard; an error/stale state is explained; and reduced-effects mode retains all functionality.

## 17. Completion checklist

- [ ] Shared glass/3D system is implemented and verified in the actual compiled browser output.
- [ ] All ten roles have distinct useful analytical views, not just different labels.
- [ ] Filters, cross-filter/highlight, drill navigation and visible selection state work by pointer, touch and keyboard.
- [ ] Active role/scope, dates, definitions, denominators and freshness are always understandable.
- [ ] Every actionable KPI/insight leads to permitted contributing records or an explicit unavailable-state preview.
- [ ] Saved views and Back navigation restore context without retaining incompatible scope data.
- [ ] Charts/KPIs/tables and all eight report outputs use the same semantic source and reconcile.
- [ ] 3D effects enhance hierarchy while plot values, labels and input targets remain stable and readable.
- [ ] Missing history, zero results, stale data, partial errors, conflicts and asynchronous refresh states are tested.
- [ ] Mobile, zoom, accessibility, reduced-effects and performance gates pass with recorded evidence.
- [ ] Existing Home, session/scoping behaviour and pending-route regression remain intact.
- [ ] `plan.md`, `missing_frontend.md` and `frontend/docs/PROGRESS.md` are updated with actual delivered scope and outstanding dependencies.

## 18. Reference basis

Product requirements remain the main-folder PRD, particularly §§3.2,7.1–7.5,8,11–14,16–17 and the §20 demonstration. `missing_frontend.md` identifies current gaps; this document defines the dashboard upgrade rather than replacing those missing workflows.

The proposed saved-view and coordinated-report experience takes its interaction vocabulary from Microsoft’s [report overview](https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-reports-overview). The implementation is a native Next.js portal design. Embedding a Power BI service/report, licensing an external analytics product or transmitting case data to it is outside this plan unless separately requested.
