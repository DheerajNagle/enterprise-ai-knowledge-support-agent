# Enterprise Virtual Private Network (VPN) Policy & Access Guidelines

**Document ID:** POL-IT-2024-003  
**Version:** 5.0  
**Effective Date:** January 15, 2024  
**Review Cycle:** Semi-Annual  
**Owner:** Information Security & Network Infrastructure  
**Applicability:** All personnel requiring remote access to internal enterprise networks and cloud VPCs  

---

## 1. Objective & Scope

The Virtual Private Network (VPN) provides an encrypted communications tunnel connecting remote devices securely to Enterprise Inc.'s private cloud environments (AWS/GCP), internal microservices, GitLab code repositories, and corporate intranet tools. This policy defines technical standards, access tiers, and operational rules governing VPN connections.

---

## 2. Approved VPN Client Software & Gateways

Remote connections may only be established using company-sanctioned client software pre-installed on managed corporate machines:

- **Primary Client:** Palo Alto GlobalProtect (Version 6.1+)
- **Fallback Client:** Enterprise WireGuard Connector (Version 2.4+)

### Regional Gateways
Users should select the geographically nearest gateway to minimize latency:
- **Americas (East):** `vpn-us-east.enterprise.internal` (Ashburn, VA)
- **Americas (West):** `vpn-us-west.enterprise.internal` (San Jose, CA)
- **Europe (EMEA):** `vpn-eu-central.enterprise.internal` (Frankfurt, DE)
- **Asia Pacific (APAC):** `vpn-ap-southeast.enterprise.internal` (Singapore, SG)

---

## 3. Authentication & Security Posture Requirements

### 3.1 Multi-Factor Authentication (MFA)
- Every VPN login requires primary Single Sign-On (SSO) credentials followed by mandatory **Okta Verify Number Matching** or a hardware **FIDO2 YubiKey**.
- SMS OTP and voice call verification are explicitly deprecated and rejected by network firewalls.

### 3.2 Host Posture Assessment (Device Health Check)
Before granting tunnel connectivity, the VPN client validates device compliance via the endpoint security sensor:
1. **CrowdStrike Falcon:** Sensor must be active and reporting clean telemetry within the last 2 hours.
2. **Disk Encryption:** FileVault (macOS) or BitLocker (Windows) must be 100% active.
3. **OS Patch Level:** The operating system must be within two patch iterations of the latest stable corporate baseline.
4. **Firewall:** Local operating system firewall must be enabled.

*Note: Devices failing posture assessment are assigned to a quarantined VLAN with access limited strictly to the IT Self-Service remediation portal.*

---

## 4. Tunneling Configurations & Routing Rules

### 4.1 Split-Tunneling (Default Profile: `Corp-Standard`)
- Directs only enterprise IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, and `*.enterprise.internal`) through the secure tunnel.
- General internet traffic (such as Zoom, YouTube, public web browsing) egresses through the local internet connection to optimize bandwidth.

### 4.2 Full-Tunneling (Profile: `Corp-Privileged-Full`)
- Mandatory for DevOps, Database Administrators, and SREs when accessing production data bastions, financial ledgers, or customer PII databases.
- 100% of network traffic routes through the enterprise intrusion prevention system (IPS).

---

## 5. Session Timeouts & Connection Limits

- **Maximum Session Lifetime:** Connections automatically disconnect after **12 continuous hours**, requiring re-authentication.
- **Idle Timeout:** Tunnels are severed if no network activity is detected for **60 minutes**.
- **Concurrent Connections:** A single user identity may maintain only **one (1) active VPN session** at any time. Simultaneous logins terminate the prior session and notify the Security Operations Center (SOC).

---

## 6. Prohibited Activities

1. Connecting non-approved personal laptops, tablets, or smartphones (BYOD) to the corporate VPN.
2. Configuring external routers or proxy tunnels to redistribute VPN connectivity to unauthorized local network devices.
3. Engaging in high-bandwidth personal media streaming or peer-to-peer (P2P) file sharing over corporate tunnels.
4. Attempting to bypass device posture inspections or disable security daemons.

---

## 7. Common Troubleshooting Scenarios

| Error / Symptom | Root Cause | Remediation Procedure |
|---|---|---|
| `Gateway Unreachable (Error 502)` | Local ISP DNS failure or captive portal | Ensure public WiFi terms are accepted; flush DNS (`ipconfig /flushdns`); switch to secondary regional gateway. |
| `Posture Check Failed: CS_SENSOR` | CrowdStrike daemon stopped or out-of-date | Open terminal, run `sudo falconctl status`, reboot system; if persistent, contact IT Support. |
| `Authentication Timeout` | Okta push not approved within 30s | Re-attempt login and ensure phone has data connection for Okta Verify push. |
| `Account Locked (403)` | 5 consecutive bad password attempts | Reset password via `https://identity.enterprise.internal/recovery`. |

---

## 8. IT Support & Emergency Contacts

- **IT Service Desk:** `it-helpdesk@enterprise.internal`
- **Security Operations Center (SOC):** `soc-hotline@enterprise.internal` (24/7 Hotline: Ext. 4444)
- **Ticket Category:** `Network/VPN` -> `Remote Access Issues`
