# Security Policy

## Supported scope

This is a reference implementation, not a hardened agent runtime. Security
reports should concern the code and templates in this repository.

## Design boundary

- Ollama is contacted only through a loopback URL by default.
- Environment proxies and HTTP redirects are disabled by the client.
- No tool definitions are sent to the model.
- Log text is treated as untrusted data.
- Model output is never executed.
- The CLI writes no file unless `--output` is supplied.
- Existing output files are not overwritten.
- Real UART/HIL logs, secrets, serial numbers, and machine-specific port maps
  must not be committed.

## Unsafe configurations

The following are outside the supported design:

- `ollama agent --yolo` or `--auto-approve-tools`
- a non-loopback Ollama endpoint without an explicit `--allow-remote` flag
- automatic flash, erase, reset, power, fuse, key, send, publish, or delete
- passing model text to a shell
- committing raw logs before secret and privacy review

## Reporting

Use GitHub private vulnerability reporting for vulnerabilities that could cause command
execution, unexpected writes, secret disclosure, remote endpoint bypass, or
evidence-citation validation bypass. Do not attach real device logs or secrets.
If the private reporting button is unavailable, do not post exploit details or
device data in a public issue; instead open a minimal issue asking the
maintainer to enable a private reporting channel.
