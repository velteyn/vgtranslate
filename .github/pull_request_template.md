## Summary

<!-- What does this change do, and why? Keep it concise. -->

## Related

<!-- Link the issue or OpenSpec change this addresses, if any. -->

## How it was tested

- [ ] `ruff check .`
- [ ] `python -m py_compile vgtranslate/*.py`
- [ ] Manual smoke: `vgtranslate serve` + a POST to `/service`, or `vgtranslate status`
- [ ] Benchmark run (`vgtranslate bench run benchmark-data`) if this changes engine or prompt behavior

## Checklist

- [ ] Focused commits with clear, imperative messages
- [ ] Provider interfaces unchanged (OCR/MT) unless the change warrants it
- [ ] User docs (`docs/`) updated alongside behavior changes
- [ ] OpenSpec change or issue referenced above, if applicable
