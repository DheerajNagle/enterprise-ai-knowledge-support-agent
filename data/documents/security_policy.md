# Enterprise Information Security & Data Governance Policy

**Document ID:** POL-SEC-2024-005  
**Version:** 6.2  
**Effective Date:** January 10, 2024  
**Review Cycle:** Annual  
**Owner:** Chief Information Security Officer (CISO) & Corporate Risk  
**Applicability:** All employees, contractors, interns, and third-party vendors  

---

## 1. Information Classification Framework

Enterprise Inc. classifies all information and data assets into four discrete tiers. Handling procedures correspond strictly to the classification tier:

| Classification | Definition | Examples | Permitted Storage |
|---|---|---|---|
| **Public** | Information approved for unrestricted public consumption. | Marketing press releases, published API docs, job listings. | Public website, company blog. |
| **Internal** | Data intended for internal use; unauthorized disclosure causes minor disruption. | Intranet wikis, organization charts, team sprint backlogs. | Google Workspace, Notion, Slack. |
| **Confidential** | Proprietary commercial data; disclosure causes commercial or reputational harm. | Financial projections, source code, pricing models, vendor contracts. | Private GitLab repos, encrypted corporate drives. |
| **Restricted** | Highly sensitive data governed by strict regulatory, legal, or privacy obligations. | Customer PII, PCI payment data, HIPAA health records, encryption keys. | Isolated production databases, HashiCorp Vault. |

---

## 2. Artificial Intelligence (AI) & LLM Usage Standards

To prevent proprietary intellectual property leaks and compliance breaches:

1. **Approved Enterprise AI Tools:** Employees must utilize the company-hosted **Enterprise AI Knowledge & Support Agent** and sanctioned enterprise API tenants (where zero-data-retention agreements are active).
2. **Prohibited Consumer AI:** Entering proprietary source code, customer data, internal roadmaps, or personnel records into consumer AI services (such as free consumer versions of ChatGPT, Claude, or public prompt-engineering sites) is strictly prohibited.
3. **Training Opt-Out:** In all developer-approved tooling, telemetry and model-training switches must remain disabled.

---

## 3. Removable Media & Endpoint Data Loss Prevention (DLP)

- **USB Mass Storage Restrictions:** All USB flash drives and external hard drives are **blocked by default** via endpoint security software. Connecting unapproved external storage generates an automated security alert.
- **Exceptions:** Hardware engineers requiring firmware flashing may request a temporary 14-day USB write exemption through a CISO-approved security waiver.
- **Cloud Storage:** Syncing corporate files to personal Dropbox, Google Drive, or iCloud accounts is intercepted and blocked by Netskope DLP agents.

---

## 4. Phishing, Social Engineering & Credential Protection

- **Reporting Suspicious Communications:** Employees must report suspicious emails, SMS lures (smishing), or Slack messages using the internal **PhishAlarm** button in Outlook/Gmail or by forwarding the raw headers to `phishing@enterprise.internal`.
- **Training Simulations:** The InfoSec team conducts randomized monthly simulated phishing tests. Employees who fail two consecutive simulations must complete mandatory remedial security refresher training within 14 days.
- **Never Disclose Credentials:** IT Support personnel, system administrators, and executives will **never** ask for your password, Okta push token, or MFA seed under any circumstances.

---

## 5. Clean Desk & Clear Screen Standards

- **Locking Workstations:** Computers must be locked immediately upon leaving your desk (`Ctrl+Cmd+Q` on macOS, `Windows+L` on Windows). Screen savers are configured to lock automatically after **5 minutes of inactivity**.
- **Physical Documents:** Printed materials containing Confidential or Restricted information must be stored in locked pedestals or immediately destroyed using cross-cut shredder bins located in copy rooms.
- **Whiteboards:** Meeting room whiteboards containing architectural diagrams, API keys, or customer details must be wiped clean at the conclusion of each session.

---

## 6. Security Incident Triage & SLA Matrix

Any suspected unauthorized access, data compromise, or security anomaly must be reported immediately:

| Severity Level | Criteria | Initial Response SLA |
|---|---|---|
| **Critical (P1)** | Active ransomware, confirmed customer data breach, compromised root keys. | **< 15 minutes** (24/7) |
| **High (P2)** | Compromised employee credentials, lost corporate laptop, unauthorized privilege escalation. | **< 1 hour** (24/7) |
| **Medium (P3)** | Target of spear-phishing attack, suspicious unauthorized port scanning, malware quarantined. | **< 4 hours** (Business hours) |
| **Low (P4)** | Security policy question, routine compliance exception request. | **< 24 hours** (Business hours) |

---

## 7. InfoSec Contacts & Reporting

- **CISO Office:** `ciso@enterprise.internal`
- **Security Operations Center (SOC Hotline):** `+1-800-555-0199` / `soc@enterprise.internal`
- **Phishing Triage:** `phishing@enterprise.internal`
- **Incident Portal Ticket:** `Access/Identity` -> `Security Incident Report`
