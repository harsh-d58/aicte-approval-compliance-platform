# Access policy decision sheet — prototype

Use with [identity_access_plan.md](../../identity_access_plan.md) and [PRD v1.0](<../../Product Requirements Document (PRD)- SIH Round 2 FInalsss- PS4.md>) §§3, 5.2, 13.1 and 21. This is a **review template**, not an approved role matrix or permission grant. Do not load it into the database until the named owner signs off a version.

| Approval field | Decision |
| --- | --- |
| Policy owner and approving authority | **To be supplied** |
| Security reviewer | **To be supplied** |
| Version and effective date | **To be supplied** |
| Approved prototype identity provider | Supabase Auth selected by project owner; formal organisation approval **to be confirmed** |
| Scope hierarchy and grant authority | **To be supplied** |
| Stronger authentication for privileged actions | **To be supplied** |
| Review and revocation timing | **To be supplied** |

## 1. Confirm roles and actions

The PRD names the following personas and typical responsibilities. For each proposed role, the policy owner must select exact actions from **Read, Create, Update, Assign, Transition, Return, Verify, Approve, Configure, Export, Administer**. Typical responsibility is not permission to perform it.

| PRD persona | PRD responsibility to review | Approved role code | Approved actions/resources | Allowed scope | Incompatible roles / approval notes |
| --- | --- | --- | --- | --- | --- |
| Institutional representative | Applications, deficiency responses, evidence, document renewal | TBD | TBD | TBD | TBD |
| Scrutiny officer | Case/document review, observations, deficiency returns | TBD | TBD | TBD | TBD |
| Regional officer | Regional oversight, assignments, EVC expert selection/schedule | TBD | TBD | TBD | TBD |
| EVC coordinator | Availability, slot recommendations, invitations and visit completion | TBD | TBD | TBD | TBD |
| EVC expert | Assigned visit material, availability, observations and drafts | TBD | TBD | TBD | TBD |
| Compliance officer | Conditions, evidence review and verification | TBD | TBD | TBD | TBD |
| Central administrator | Cross-region aggregate monitoring and authorised configuration | TBD | TBD | TBD | TBD |
| Policy/configuration administrator | Versioned rules and publication | TBD | TBD | TBD | TBD |
| Auditor | Authorised history, integrity checks and exports | TBD | TBD | TBD | Must not gain workflow mutation by default |
| System administrator | Technical operation, identity integration, backups and monitoring | TBD | TBD | TBD | Must not gain statutory approval by default |
| Integration service | Approved import/sync under field ownership rules | TBD | TBD | TBD | Service identity policy TBD |

Decide the action/resource pair, not just a broad role name. In particular, choose separate permissions for record read, file download, report export, evidence verification, EVC committee selection, workflow transition, final approval and configuration publication.

## 2. Scope and relationship decisions

The existing `public.user_role_assignments` check constraint permits lowercase `global`, `institution`, `region`, `application` and `campus`; `global` requires a null `scope_id`, while all other listed types require a UUID. There is **no `evc` scope type**. Current institution/application reads implement direct region matching only. EVC access may be derived from exact visit membership, but the policy owner must approve that relationship before it is used.

| Decision | Required answer |
| --- | --- |
| Which roles may receive each of the five existing scope types? | TBD |
| Who can grant `global`, and for which resources? | TBD |
| Does `region` include descendants or only direct `institutions.region_id`? | TBD; current reads use direct match |
| Does an assigned scrutiny case grant application-only access, and which linked documents? | TBD |
| How does EVC committee membership grant visit, observation, source and report access? | TBD |
| Can campus scope see institution-wide records? | TBD; current read routes do not accept campus scope |
| How are institution representatives verified before an institution assignment is granted? | TBD; entering a code is insufficient |
| Which scopes permit auditor/history/report access, and can exports contain personal data? | TBD |
| How are service identities scoped and separated from human authority? | TBD |

## 3. Grant lifecycle and control decisions

- [ ] Identify authorised grant, change, revoke and emergency-access actors, including any second approval.
- [ ] Define active window semantics, timezone, expiry, revocation status and maximum allowed duration. Current reads require `valid_from <= now` and `valid_until > now` when an end exists.
- [ ] Define whether duplicate/overlapping active assignments are rejected, merged or explicitly versioned. The database has no unique assignment index beyond its primary key.
- [ ] Define reason and evidence for every grant/change/revoke, plus audit visibility, retention and periodic access review.
- [ ] Define simultaneous roles and conflicts of duty. Technical administration, auditing, expert review and statutory approval require explicit separation.
- [ ] Define user suspension/disable rules and how quickly active sessions lose access. Backend must recheck on every request.
- [ ] Confirm how a first policy administrator is provisioned without leaving a permanent unreviewed superuser.

## 4. First controlled validation record

After approval, record a fictional test case without credentials in this document:

| Field | Value |
| --- | --- |
| Approved policy version | TBD |
| Auth user subject reference (store in approved location; no token/password here) | TBD |
| `public.users` mapping checked | [ ] |
| Role/permission/scope assignment checked | [ ] |
| In-scope institution/application read | [ ] |
| Out-of-scope institution/application denied | [ ] |
| Disabled/revoked/expired access denied | [ ] |
| Audit event and reviewer evidence | [ ] |

**Sign-off gate:** once the tables above are filled and approved, update [access_policy.md](access_policy.md) with the effective policy version, then implement the PRD-listed grant/revoke APIs and test the real browser journey. Until then, the empty application policy tables are intentionally fail-closed.
