# Security Policy

Desktop automation is powerful. Security is a product feature for Arbora, not paperwork.

## Supported versions

This repository is in early prototype stage. Treat all releases before 1.0 as experimental.

## Reporting a vulnerability

If you discover a vulnerability in design docs or code:

1. **Do not** open a public issue with exploit details.
2. Contact the maintainers privately (contact method will be published with the first packaged release; until then use GitHub private security advisories on [Victor-Jnr/Arbora](https://github.com/Victor-Jnr/Arbora) if available).
3. Allow reasonable time for assessment before public discussion.

Please do not request or contribute exploit payloads, malware, or instructions intended to attack systems.

## Expected practices (product)

- Least-privilege tool scopes through the permission broker
- No plaintext long-term storage of secrets in memory or logs
- Clear separation between read-only diagnostics and mutating repairs
- Auditability of privileged operations
- Careful handling of prompt-injection from web/page/file content

## Hard confirmation classes

Even inside trusted routines, Arbora must require a fresh explicit confirmation before:

- Financial or purchase-related actions
- Credential / private-data handling
- Destructive or irreversible system/file actions
