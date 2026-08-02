# Contributing

Thank you for helping make PersonaWare more accessible.

## Good contributions

- A screenshot or reproducible path to Japanese text that remains visible in
  normal use.
- A correction that makes translated wording clearer or more accurate.
- Runtime results from real PC 110 hardware or a compatible emulator.
- Improvements to the CP932 audit or image-integrity checks.
- Reproducible installer, recovery, wrong-drive, or power-loss test results.

## Before opening a change

1. Keep executable replacements inside their existing byte slots.
2. Preserve original offsets, relocation data, line endings, and encodings.
3. Run the repository verification:

   ```sh
   ./scripts/verify_release.sh
   ```

   This requires Python 3, NASM, and `mtools`.

4. Describe the screen or workflow affected and include a screenshot when
   possible.

Do not submit ROMs, disk images, source media, credentials, personal records,
or other third-party material unless you have explicit redistribution rights.
Small byte sequences needed to identify a patch location should be kept to the
minimum required for review.

## Translation style

- Prefer short, direct English that fits the original UI.
- Use the terminology already present in the application.
- Preserve keyboard shortcuts and function-key labels.
- Treat warnings, errors, confirmation dialogs, and help pages as user-facing
  text that must be translated.
- Leave conversion tables and program data unchanged unless they are visibly
  rendered or demonstrably affect English operation.
