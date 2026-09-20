---
title: Verify a download
summary: Check the SHA-256 of what you downloaded against the one published here.
order: 5
---
Every file on the [download page](/download) lists its SHA-256. Compare it to the file you have:

**PowerShell**
```
Get-FileHash .\VoxTerrae.exe -Algorithm SHA256
```
**macOS / Linux**
```
shasum -a 256 VoxTerrae.exe
```
The 64-character value must match exactly. A mismatch means a corrupted or altered download: delete it.

What a checksum does and does not prove: it proves the bytes you have are the bytes we published on this site. It does not by itself prove *who* published them, because the checksum and the file come from the same server. Two independent checks cover that gap.

## Build provenance (attested releases)
Releases marked *attested* on the [download page](/download) were built by the public GitHub Actions release workflow, and GitHub recorded a SLSA provenance attestation (Sigstore) for the exe at build time. Verify it with the GitHub CLI; it checks the file's digest against that record, so it fails on any altered or substituted binary:
```
gh attestation verify .\VoxTerrae.exe --repo indicaindependent/voxterrae
```
It passes for 0.1.2. It cannot pass for 0.1.1: that build was tagged while the repository was briefly private, no attestation was issued, and one cannot be added afterwards. For 0.1.1 the SHA-256 above is the check. Each release page says which applies.

## Code signing
The exe is not code-signed (no Authenticode signature), which is why Windows SmartScreen shows its notice on first run. An attestation proves where the bytes came from; a code signature would let Windows check that itself. Signing is on the [roadmap](/releases).
