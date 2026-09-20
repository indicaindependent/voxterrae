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

What a checksum does and does not prove: it proves the bytes you have are the bytes we published on this site. It does not by itself prove *who* published them, because the checksum and the file come from the same server. Signed releases (Sigstore bundle and Windows code signature) are on the [roadmap](/releases) and will be listed next to each file when they exist.
