# Enterprise Password, Credential & MFA Standards Policy

**Document ID:** POL-SEC-2024-008  
**Version:** 5.0  
**Effective Date:** February 1, 2024  
**Review Cycle:** Annual  
**Owner:** Identity & Access Management (IAM) & Cybersecurity  
**Applicability:** All workforce members, service accounts, and API integrations  

---

## 1. Scope & Framework Alignment

This policy establishes strict standards for user authentication, password construction, multi-factor authentication (MFA), and credential lifecycles. Enterprise Inc. adheres strictly to the **NIST SP 800-63B Digital Identity Guidelines**, prioritizing memorability, password length, and phishing-resistant multi-factor authentication over arbitrary character rotation.

---

## 2. Password Length & Complexity Requirements

All primary corporate credentials (SSO/Okta, Active Directory, local admin accounts) must satisfy the following minimum specifications:

- **Minimum Length:** **Sixteen (16) characters** minimum.
- **Composition:** Must contain characters from at least three (3) of the following categories:
  - Uppercase letters (`A` through `Z`)
  - Lowercase letters (`a` through `z`)
  - Numeric digits (`0` through `9`)
  - Non-alphanumeric special characters (`! @ # $ % ^ & * ( ) _ + - = [ ] { } | ; : , . < > ?`)
- **Passphrase Strategy (Recommended):** Users are encouraged to utilize 4 to 5 random, unrelated words separated by spaces or hyphens (e.g., `purple-orbit-battery-vintage-drift`).
- **Prohibited Patterns:**
  - Common dictionary sequences (`Password123!`, `Welcome2024!`).
  - Company names, department names, or system acronyms (`Enterprise2024#`).
  - Personal identifiable information (employee birth year, spouse/child names, pet names).
- **Breach Screening:** All new password submissions are checked automatically in real time against the **HaveIBeenPwned** database of compromised credentials. Any password appearing in prior public breaches is immediately rejected.

---

## 3. Rotation, Expiration & Credential Lifecycles

- **No Arbitrary Expiration:** In alignment with modern NIST guidance, user passwords **do not expire on a routine 60 or 90-day cycle**. Forced periodic expiration encourages predictable substitutions and degrades organizational security.
- **Mandatory Triggered Rotation:** A password reset is enforced immediately under the following conditions:
  - An anomalous login event is flagged by Okta ThreatInsight (e.g., impossible travel, malicious IP egress).
  - Suspected phishing compromise or device theft.
  - Notice from external cybersecurity intelligence indicating credential exposure.

---

## 4. Multi-Factor Authentication (MFA) Standards

MFA is non-optional and enforced across 100% of corporate services:
- **Approved Methods:**
  - **FIDO2 / WebAuthn Hardware Security Keys:** Yubikey 5 Series (Available free from IT Support).
  - **Okta Verify:** Mobile application with biometric number matching challenge.
- **Disallowed Methods:** SMS text OTP and automated phone calls are strictly blocked due to vulnerability to SIM-swapping and SS7 interception attacks.

---

## 5. Enterprise Password Manager Adoption

- **Sanctioned Solution:** All employees are provisioned an **Enterprise 1Password Account** (`https://1password.enterprise.internal`).
- **Zero-Knowledge Vaults:** Employees must generate and store unique, high-entropy passwords for all secondary internal and external software services within 1Password.
- **Browser Auto-Fill Restrictions:** Storing corporate credentials in unmanaged consumer browser password sync tools (such as personal Google Chrome or Apple Keychain accounts) is prohibited.

---

## 6. Account Lockouts & Self-Service Unlocking

- **Lockout Threshold:** Five (5) consecutive failed authentication attempts within a 15-minute window will lock the account.
- **Self-Service Remediation:**
  1. Visit the recovery portal: `https://identity.enterprise.internal/recovery`.
  2. Complete the biometric Okta Verify push challenge on your registered mobile device.
  3. Reset your password and unlock your account.
- **Help Desk Escalation:** If you cannot access your mobile device, contact the IT Service Desk. An IT technician will verify your identity via video call before issuing a temporary 1-hour bypass code.

---

## 7. Machine & Service Account Credentials

- Service accounts, API tokens, and database secrets must be at least **32 characters** in length with cryptographic entropy.
- Machine credentials must be stored and retrieved programmatically via **HashiCorp Vault** or **AWS Secrets Manager**.
- Storing plain-text secrets, API keys, or private tokens in git repositories, environment files committed to source control, or Jira tickets is a critical security incident.

---

## 8. IAM Contacts & Support

- **Identity & Access Management:** `iam-team@enterprise.internal`
- **IT Service Desk:** `helpdesk@enterprise.internal` (Phone: Ext. 4357 / `HELP`)
- **Internal Ticket Category:** `Access/Identity` -> `Password & MFA Reset`
