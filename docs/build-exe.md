# Build EXE

## Command
```powershell
.\build_exe.ps1
```

## Output
- Executable:
  - `dist\TaskMNG.exe`

## Packaging Behavior
- The build bundles the current `data\taskmng.db` as a seed database.
- On first launch of the `.exe`, if no local `data\taskmng.db` exists next to the executable, the app will copy the bundled DB out automatically.
- After that, the app uses the external local DB so user changes persist between runs.

