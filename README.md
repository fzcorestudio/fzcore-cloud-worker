# FZCORE Studio - 24/7 Autonomous Cloud Outbound & Harvester Engine

Production cloud worker executing continuously on GitHub Actions (24/7/365).

### Architecture & Capabilities
1. **Inbox Monitor & Reply Forwarder:**
   - Scans 50 fleet mailboxes via IMAP SSL.
   - Detects delivery failures and auto-quarantines dead emails/domains.
   - Filters out bot auto-responders.
   - Forwards genuine client replies directly to `nmstationer@gmail.com` with `Reply-To` set to the client.

2. **Safe Multi-Mailbox SMTP Dispatcher:**
   - Subdomain round-robin load distribution.
   - Humanized anti-spam pacing (50 to 75 seconds).
   - Unified persistent sent ledger on Hostinger Private Vault.
   - Follow-Up #1 bumps sent exclusively to verified Direct Named Owners.

3. **Headless Playwright Maps Harvester:**
   - Crawls Rank #20 to #100 contractors across high-margin niches (Remodeling, Roofing, MedSpa, Detailing, etc.).
   - 20-point DOM audit + RFC DNS MX handshake verification.
   - Continuously replenishes active vault queue.

### Security
All credentials and mailbox passwords are encrypted in GitHub Actions Secrets (`secrets.*`). Zero credentials in code.
