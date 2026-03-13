# Lessons Learned

- 2026-03-13: Adding a new UI dependency is not fully verified by service-level UAT.
  Detection signal: `GUI smoke check` failed with `ModuleNotFoundError: No module named 'PIL'` even though UAT passed.
  Prevention rule: after changing desktop UI imports or build assets, run a real GUI smoke check and ensure the venv has been updated from `requirements.txt` before building the `.exe`.
