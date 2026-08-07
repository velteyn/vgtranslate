# Security Policy

## Supported Versions

Security fixes are released for the current 2.x line. Older releases —
including the pre-rewrite 1.x / Python 2 codebase — are not supported and
receive no security updates.

| Version | Supported |
| ------- | --------- |
| 2.0.x   | :white_check_mark: |
| 1.x     | :x: |
| < 1.0   | :x: |

## Reporting a Vulnerability

Please do **not** open a public issue for a security problem. Report it
privately through GitHub's **Security Advisories**: on the repository's
*Security* tab, choose *Report a vulnerability*. This lets us fix the issue
before it is disclosed.

What to include:

- The affected version(s) and how you reproduced it (request, frame, config).
- Any crash logs or unexpected server behavior.
- Whether the issue is reachable only locally or also remotely.

What happens next:

- You'll receive an acknowledgment within a few days.
- We'll investigate, confirm scope, and prepare a fix and release.
- If the report is declined or out of scope, you'll get a short explanation.

## Scope

VGTranslate is a **local-first** server: it binds to `localhost`, is driven by a
trusted emulator on the same machine, and talks to local LLM services. The
reports that matter most:

- Requests that crash, hang, or exhaust the server (malformed frames, very
  large uploads).
- Content-type/parser edge cases that bypass the validated request handling.
- Path traversal or config tampering reachable from the HTTP endpoint.
- Anything that would let a malicious page or game abuse the localhost service.
