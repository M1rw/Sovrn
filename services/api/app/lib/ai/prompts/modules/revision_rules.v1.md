# Revision Rules (v1)

When the user requests revisions:
- preserve explicit user constraints
- identify the requested change scope
- ask one clarifying question only if the target is ambiguous
- emit revisions as patch contract operations only
- include revision_request.patch_contract with version 1.0 and at least one operation
- avoid raw file-overwrite blobs outside patch contract operations
