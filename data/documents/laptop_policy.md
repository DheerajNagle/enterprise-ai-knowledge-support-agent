# Enterprise Corporate Laptop & Hardware Asset Policy

**Document ID:** POL-IT-2024-004  
**Version:** 4.3  
**Effective Date:** March 1, 2024  
**Review Cycle:** Annual  
**Owner:** Global IT Asset Management & End-User Computing  
**Applicability:** All full-time, contract, and temporary personnel provisioned corporate computing equipment  

---

## 1. Policy Purpose

This policy governs the provisioning, maintenance, security baseline, replacement lifecycle, and decommissioning of enterprise-owned laptops, mobile devices, and associated accessories. All corporate equipment remains the exclusive property of Enterprise Inc. at all times.

---

## 2. Standard Provisioning Profiles

Employees receive standardized hardware configurations aligned with their departmental requirements:

### 2.1 Engineering & Data Science Tier
- **macOS Option:** Apple MacBook Pro 16-inch (Apple Silicon M-Series, 36GB Unified Memory, 1TB NVMe SSD).
- **Linux/Windows Option:** Dell Precision 5570 or Lenovo ThinkPad P1 (64GB DDR5 RAM, 1TB NVMe SSD, NVIDIA RTX GPU, Ubuntu LTS or Windows 11 Enterprise).

### 2.2 Corporate & Business Operations Tier
- **macOS Option:** Apple MacBook Air 15-inch (Apple Silicon M-Series, 16GB Unified Memory, 512GB SSD).
- **Windows Option:** Lenovo ThinkPad T14s Gen 4 (Intel Core i7, 16GB RAM, 512GB SSD, Windows 11 Enterprise).

*Note: Custom hardware configurations exceeding standard tiers require Director-level budget approval and an IT architectural review.*

---

## 3. Hardware Refresh Lifecycle

- **Standard Lifecycle:** All primary laptops follow a strict **36-month (3-year) refresh cycle** calculated from the initial deployment date.
- **Automated Notification:** The IT Asset Management system automatically sends an email invitation 45 days prior to the 36-month milestone prompting the employee to select their replacement machine.
- **Legacy Machine Buyout:** Upon successful delivery of the new laptop, employees in good standing may purchase their depreciated laptop for personal use at fair market scrap value ($100 USD) following a certified IT cryptographic disk sanitization.

---

## 4. Mobile Device Management (MDM) & Mandatory Software

All corporate laptops are enrolled in enterprise MDM systems prior to dispatch:
- **macOS Fleet:** Managed via **Jamf Pro**.
- **Windows Fleet:** Managed via **Microsoft Intune**.

### Non-Removable Baseline Agents
1. **CrowdStrike Falcon Sensor:** Real-time threat detection and behavioral analysis.
2. **Netskope Client:** Cloud access security broker and data loss prevention (DLP).
3. **Automated OS Patching:** Security patches are deployed automatically on Tuesdays. Employees are given a 72-hour deferral grace period before an automated reboot occurs.

*Removal, evasion, or modification of MDM configuration profiles constitutes a serious security violation subject to disciplinary action.*

---

## 5. Loss, Theft, and Emergency Incident Protocol

If a corporate laptop is misplaced, lost, or stolen, immediate action is mandatory:

1. **2-Hour Reporting Window:** You must report the incident within **two (2) hours** of discovery:
   - Call the 24/7 Emergency SOC Hotline: `+1-800-555-0199` or email `soc-hotline@enterprise.internal`.
   - Submit an urgent ticket: Category `Hardware` -> `Lost/Stolen Device`.
2. **Remote Wipe:** The SOC initiates a remote cryptographic wipe and device lock command via MDM.
3. **Police Report:** For stolen assets, file a report with local law enforcement within **48 hours** and upload the police report incident number to the IT ticket.
4. **Loaner Replacement:** IT Logistics ships an expedited loaner laptop within **24 business hours**.

---

## 6. Repair & Accidental Damage Coverage

- All machines include comprehensive OEM warranty coverage (AppleCare+ for Enterprise or Dell ProSupport Plus).
- **Spills and Drops:** Accidental damage is covered up to two incidents per hardware lifecycle. Report damage via the IT portal to receive a return shipping box.
- **Unauthorized Third-Party Repair:** Employees must never take corporate laptops to unauthorized third-party repair shops (e.g., local mall kiosks). All repairs must flow through corporate IT channels.

---

## 7. Offboarding & Asset Return

- Upon resignation or separation, all corporate assets (laptop, power adapters, monitors, hardware tokens) must be returned within **five (5) business days**.
- IT Logistics provides a prepaid, insured shipping box with custom foam packaging sent directly to the employee's residential address.
- Failure to return company equipment may result in legal recovery proceedings and withholding of final unearned stipends where permitted by applicable law.

---

## 8. Support & Service Desk Contacts

- **IT Asset Management Team:** `it-hardware@enterprise.internal`
- **Global Help Desk:** `helpdesk@enterprise.internal`
- **Internal Ticket Category:** `Hardware` -> `Laptop Provisioning & Refresh`
- **Depot Hours:** Monday – Friday, 08:00 – 18:00 Local Time
